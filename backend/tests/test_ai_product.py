import io
import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from sqlalchemy.orm import Session

from app.models.ai import AIRequestStatus
from app.models.ai_product_draft import AIProductDraft
from app.models.product import Product
from app.models.user import User
from app.services import ai_product_service, product_image_service
from app.services.image_fetch_service import detect_extension, fetch_image
from tests.conftest import auth_headers, make_user


def _png_bytes(*, transparent: bool) -> bytes:
    colour = (255, 0, 0, 0) if transparent else (255, 0, 0, 255)
    buffer = io.BytesIO()
    Image.new("RGBA", (8, 8), colour).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def staged_uploads_in_tmp(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:  # noqa: ANN001
    """Redirects image staging to a throwaway directory.

    save_image() writes to the real uploads dir, which in production is a
    mounted volume — without this every test run would leave orphaned PNGs
    sitting next to genuine product images.
    """
    monkeypatch.setattr(product_image_service, "UPLOAD_DIR", tmp_path / "products")


@pytest.fixture()
def fake_ai(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stubs both network legs (research + image model) so the tests exercise
    the draft/confirm orchestration rather than Gemini."""
    monkeypatch.setattr(ai_product_service.settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(
        ai_product_service,
        "_research",
        lambda name: (
            ai_product_service._ProductResearch(
                product_name="Snickers Bar",
                description="A chocolate bar with nougat and peanuts.",
                image_url="https://example.com/snickers.png",
                source_title="Example Store",
                suggested_price_iqd=1500,
                image_prompt="GTA cover art style Snickers bar, bold outlines",
            ),
            None,
        ),
    )
    monkeypatch.setattr(
        ai_product_service, "search_product_images", lambda name, description="": ["https://example.com/real.jpg"]
    )
    monkeypatch.setattr(ai_product_service, "fetch_image", lambda url: (_png_bytes(transparent=False), ".png"))
    monkeypatch.setattr(ai_product_service, "apply_gta_style", lambda data: data)
    monkeypatch.setattr(
        ai_product_service, "_to_transparent_png", lambda data: (_png_bytes(transparent=True), True, None)
    )


# ---------------------------------------------------------------------------
# Nothing is created before the admin confirms
# ---------------------------------------------------------------------------


def test_draft_does_not_create_a_product(client: TestClient, db: Session, admin: User, fake_ai: None) -> None:
    before = db.query(Product).count()

    response = client.post(
        "/api/ai/products/draft", json={"name": "Snickers"}, headers=auth_headers(client, admin.username, "password123")
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["extracted_name"] == "Snickers Bar"
    assert body["image_prompt"]
    assert body["has_transparency"] is True
    assert body["created_product_id"] is None
    assert db.query(Product).count() == before, "a draft must not create a product"


def test_confirm_creates_the_product_with_admin_stock(client: TestClient, db: Session, admin: User, fake_ai: None) -> None:
    headers = auth_headers(client, admin.username, "password123")
    draft = client.post("/api/ai/products/draft", json={"name": "Snickers"}, headers=headers).json()

    response = client.post(f"/api/ai/products/{draft['id']}/confirm", json={"stock_quantity": 7}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "confirmed"

    product = db.get(Product, uuid.UUID(body["created_product_id"]))
    assert product is not None
    assert product.name == "Snickers Bar"
    assert product.stock_quantity == 7
    assert float(product.price) == 1500
    # The staged image becomes the product's image, not a second copy.
    assert product.image_url == draft["staged_image_url"]


def test_admin_can_override_name_price_and_description(client: TestClient, db: Session, admin: User, fake_ai: None) -> None:
    headers = auth_headers(client, admin.username, "password123")
    draft = client.post("/api/ai/products/draft", json={"name": "Snickers"}, headers=headers).json()

    response = client.post(
        f"/api/ai/products/{draft['id']}/confirm",
        json={"stock_quantity": 3, "name": "Snickers Mini", "price": 900, "description": "Smaller one."},
        headers=headers,
    )
    assert response.status_code == 200

    product = db.get(Product, uuid.UUID(response.json()["created_product_id"]))
    assert product.name == "Snickers Mini"
    assert float(product.price) == 900
    assert product.description == "Smaller one."


def test_confirming_twice_is_rejected(client: TestClient, db: Session, admin: User, fake_ai: None) -> None:
    headers = auth_headers(client, admin.username, "password123")
    draft = client.post("/api/ai/products/draft", json={"name": "Snickers"}, headers=headers).json()
    client.post(f"/api/ai/products/{draft['id']}/confirm", json={"stock_quantity": 1}, headers=headers)

    again = client.post(f"/api/ai/products/{draft['id']}/confirm", json={"stock_quantity": 1}, headers=headers)
    assert again.status_code == 400


def test_rejected_draft_creates_nothing(client: TestClient, db: Session, admin: User, fake_ai: None) -> None:
    headers = auth_headers(client, admin.username, "password123")
    draft = client.post("/api/ai/products/draft", json={"name": "Snickers"}, headers=headers).json()
    before = db.query(Product).count()

    response = client.post(f"/api/ai/products/{draft['id']}/reject", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert db.query(Product).count() == before

    # A rejected draft can no longer be confirmed.
    assert client.post(f"/api/ai/products/{draft['id']}/confirm", json={"stock_quantity": 1}, headers=headers).status_code == 400


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


def test_customer_cannot_draft_products(client: TestClient, customer: User) -> None:
    response = client.post(
        "/api/ai/products/draft", json={"name": "Snickers"}, headers=auth_headers(client, customer.username, "password123")
    )
    assert response.status_code == 403


def test_unauthenticated_cannot_draft_products(client: TestClient) -> None:
    assert client.post("/api/ai/products/draft", json={"name": "Snickers"}).status_code == 401


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------


def test_missing_api_key_yields_failed_draft_not_an_error(
    client: TestClient, db: Session, admin: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ai_product_service.settings, "gemini_api_key", "")
    response = client.post(
        "/api/ai/products/draft", json={"name": "Snickers"}, headers=auth_headers(client, admin.username, "password123")
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert "not configured" in body["error_message"]
    assert db.query(Product).count() == 0


def test_successful_image_pipeline_records_source_and_stores_image(
    client: TestClient, db: Session, admin: User, fake_ai: None
) -> None:
    response = client.post(
        "/api/ai/products/draft", json={"name": "Snickers"}, headers=auth_headers(client, admin.username, "password123")
    )
    body = response.json()
    assert body["image_status"] == "ok"
    assert body["staged_image_url"] is not None
    assert body["source_url"] == "https://example.com/real.jpg"
    assert body["has_transparency"] is True


def test_correct_image_url_is_stored_on_the_created_product(
    client: TestClient, db: Session, admin: User, fake_ai: None
) -> None:
    headers = auth_headers(client, admin.username, "password123")
    draft = client.post("/api/ai/products/draft", json={"name": "Snickers"}, headers=headers).json()
    confirmed = client.post(f"/api/ai/products/{draft['id']}/confirm", json={"stock_quantity": 5}, headers=headers).json()

    product = db.get(Product, uuid.UUID(confirmed["created_product_id"]))
    assert product.image_url == draft["staged_image_url"]
    assert product.image_url.startswith("/uploads/products/")


def test_image_search_not_configured_still_yields_a_reviewable_draft(
    client: TestClient, db: Session, admin: User, monkeypatch: pytest.MonkeyPatch, fake_ai: None
) -> None:
    def _unavailable(name, description=""):  # noqa: ANN001, ANN202
        raise ai_product_service.ImageSearchUnavailable("Image search is not configured")

    monkeypatch.setattr(ai_product_service, "search_product_images", _unavailable)
    monkeypatch.setattr(ai_product_service.settings, "google_cse_api_key", "")
    monkeypatch.setattr(ai_product_service.settings, "google_cse_id", "")

    body = client.post(
        "/api/ai/products/draft", json={"name": "Snickers"}, headers=auth_headers(client, admin.username, "password123")
    ).json()

    assert body["status"] == "pending"
    assert body["image_status"] == "not_configured"
    assert body["staged_image_url"] is None
    assert body["extracted_name"] == "Snickers Bar", "product details must survive an image failure"


def test_image_search_returning_nothing_is_reported_not_faked(
    client: TestClient, db: Session, admin: User, monkeypatch: pytest.MonkeyPatch, fake_ai: None
) -> None:
    monkeypatch.setattr(ai_product_service, "search_product_images", lambda name, description="": [])
    body = client.post(
        "/api/ai/products/draft", json={"name": "Snickers"}, headers=auth_headers(client, admin.username, "password123")
    ).json()

    assert body["image_status"] == "no_results"
    assert body["staged_image_url"] is None
    assert body["source_url"] is None, "a failed search must never leave a URL behind"


def test_every_candidate_failing_to_download_is_reported(
    client: TestClient, db: Session, admin: User, monkeypatch: pytest.MonkeyPatch, fake_ai: None
) -> None:
    """A dead or hostile image URL must not discard the product details, and
    must not be saved as the product's image."""
    monkeypatch.setattr(
        ai_product_service, "search_product_images", lambda name, description="": ["https://a.test/1.jpg", "https://b.test/2.jpg"]
    )

    def _reject(url: str):  # noqa: ANN202
        raise HTTPException(status_code=400, detail="Image host resolves to a non-public address")

    monkeypatch.setattr(ai_product_service, "fetch_image", _reject)
    body = client.post(
        "/api/ai/products/draft", json={"name": "Snickers"}, headers=auth_headers(client, admin.username, "password123")
    ).json()

    assert body["status"] == "pending"
    assert body["image_status"] == "fetch_failed"
    assert body["staged_image_url"] is None
    assert body["extracted_name"] == "Snickers Bar"
    assert db.query(Product).count() == 0


def test_second_candidate_is_used_when_the_first_fails(
    client: TestClient, db: Session, admin: User, monkeypatch: pytest.MonkeyPatch, fake_ai: None
) -> None:
    monkeypatch.setattr(
        ai_product_service, "search_product_images", lambda name, description="": ["https://bad.test/1.jpg", "https://good.test/2.jpg"]
    )

    def _fetch(url: str):  # noqa: ANN202
        if "bad" in url:
            raise HTTPException(status_code=400, detail="nope")
        return _png_bytes(transparent=False), ".png"

    monkeypatch.setattr(ai_product_service, "fetch_image", _fetch)
    body = client.post(
        "/api/ai/products/draft", json={"name": "Snickers"}, headers=auth_headers(client, admin.username, "password123")
    ).json()

    assert body["image_status"] == "ok"
    assert body["source_url"] == "https://good.test/2.jpg"


def test_style_step_failing_is_reported_and_stores_no_image(
    client: TestClient, db: Session, admin: User, monkeypatch: pytest.MonkeyPatch, fake_ai: None
) -> None:
    def _boom(data: bytes):  # noqa: ANN202
        raise ValueError("style kernel blew up")

    monkeypatch.setattr(ai_product_service, "apply_gta_style", _boom)
    body = client.post(
        "/api/ai/products/draft", json={"name": "Snickers"}, headers=auth_headers(client, admin.username, "password123")
    ).json()

    assert body["status"] == "pending"
    assert body["image_status"] == "processing_failed"
    assert body["staged_image_url"] is None


def test_background_removal_failure_keeps_the_image_and_says_so(
    client: TestClient, db: Session, admin: User, monkeypatch: pytest.MonkeyPatch, fake_ai: None
) -> None:
    """rembg being unavailable or busy must not lose the styled image — it is
    stored opaque, and the admin is told."""
    monkeypatch.setattr(
        ai_product_service,
        "_to_transparent_png",
        lambda data: (_png_bytes(transparent=False), False, "Background removal is busy"),
    )
    body = client.post(
        "/api/ai/products/draft", json={"name": "Snickers"}, headers=auth_headers(client, admin.username, "password123")
    ).json()

    assert body["image_status"] == "ok"
    assert body["staged_image_url"] is not None
    assert body["has_transparency"] is False
    assert "busy" in body["image_error"]


def test_admin_can_retry_the_image_without_losing_reviewed_details(
    client: TestClient, db: Session, admin: User, monkeypatch: pytest.MonkeyPatch, fake_ai: None
) -> None:
    monkeypatch.setattr(ai_product_service, "search_product_images", lambda name, description="": [])
    headers = auth_headers(client, admin.username, "password123")
    draft = client.post("/api/ai/products/draft", json={"name": "Snickers"}, headers=headers).json()
    assert draft["image_status"] == "no_results"

    # Search starts working; only the image is re-run.
    monkeypatch.setattr(
        ai_product_service, "search_product_images", lambda name, description="": ["https://example.com/real.jpg"]
    )
    retried = client.post(f"/api/ai/products/{draft['id']}/retry-image", headers=headers).json()

    assert retried["image_status"] == "ok"
    assert retried["staged_image_url"] is not None
    assert retried["extracted_name"] == draft["extracted_name"]
    assert retried["suggested_price"] == draft["suggested_price"]


def test_customer_cannot_retry_images(client: TestClient, customer: User) -> None:
    response = client.post(f"/api/ai/products/{uuid.uuid4()}/retry-image", headers=auth_headers(client, customer.username, "password123"))
    assert response.status_code == 403


def test_draft_without_any_image_is_still_confirmable(
    client: TestClient, db: Session, admin: User, monkeypatch: pytest.MonkeyPatch, fake_ai: None
) -> None:
    """The image is never mandatory: when no product photo can be found the
    admin must still be able to create the product and attach one later
    through the existing upload."""
    monkeypatch.setattr(ai_product_service, "search_product_images", lambda name, description="": [])
    headers = auth_headers(client, admin.username, "password123")
    draft = client.post("/api/ai/products/draft", json={"name": "Snickers"}, headers=headers).json()
    assert draft["status"] == "pending"
    assert draft["staged_image_url"] is None

    confirmed = client.post(f"/api/ai/products/{draft['id']}/confirm", json={"stock_quantity": 4}, headers=headers)
    assert confirmed.status_code == 200
    product = db.get(Product, uuid.UUID(confirmed.json()["created_product_id"]))
    assert product.image_url is None
    assert product.stock_quantity == 4


# ---------------------------------------------------------------------------
# Free tier only: quota exhaustion is a dead end, never a paid fallback
# ---------------------------------------------------------------------------


def test_exhausted_free_tier_quota_fails_with_a_clear_message(
    client: TestClient, db: Session, admin: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ai_product_service.settings, "gemini_api_key", "test-key")

    calls: list[str] = []

    class _Quota(Exception):
        def __str__(self) -> str:
            return "429 RESOURCE_EXHAUSTED"

    class _FakeModels:
        def generate_content(self, *, model, contents, config):  # noqa: ANN001, ANN202
            calls.append(model)
            raise _Quota()

    class _FakeClient:
        models = _FakeModels()

    monkeypatch.setattr(ai_product_service, "_client", lambda: _FakeClient())

    response = client.post(
        "/api/ai/products/draft", json={"name": "Snickers"}, headers=auth_headers(client, admin.username, "password123")
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert "free-tier quota is exhausted" in body["error_message"]
    assert "No paid model was used" in body["error_message"]
    # Only the declared free-tier models were ever attempted.
    assert calls == list(ai_product_service.TEXT_MODELS)
    assert db.query(Product).count() == 0


# ---------------------------------------------------------------------------
# SSRF hardening on the image fetcher (no mocking — these must really refuse)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/x.png",
        "http://localhost/x.png",
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata
        "http://10.0.0.5/x.png",
        "http://192.168.1.10/x.png",
        "http://[::1]/x.png",
        "http://db:5432/x.png",  # the compose-network Postgres host
    ],
)
def test_fetch_image_refuses_non_public_addresses(url: str) -> None:
    with pytest.raises(HTTPException) as exc:
        fetch_image(url)
    assert exc.value.status_code == 400


@pytest.mark.parametrize("url", ["file:///etc/passwd", "gopher://example.com/x", "redis://example.com:6379"])
def test_fetch_image_refuses_non_http_schemes(url: str) -> None:
    with pytest.raises(HTTPException) as exc:
        fetch_image(url)
    assert "http or https" in exc.value.detail


# ---------------------------------------------------------------------------
# Real local image processing (no mocks) and resource protection
# ---------------------------------------------------------------------------


def test_gta_filter_preserves_the_real_product() -> None:
    """The style must be a filter over the real photo, not a redraw: same
    dimensions, alpha carried through, and the product's own colour still
    recognisably itself."""
    from app.services.product_image_style_service import apply_gta_style

    source = Image.new("RGBA", (120, 180), (255, 255, 255, 255))
    ImageDraw.Draw(source).rectangle((30, 20, 90, 160), fill=(20, 70, 190, 255))
    buffer = io.BytesIO()
    source.save(buffer, format="PNG")

    styled = Image.open(io.BytesIO(apply_gta_style(buffer.getvalue())))

    assert styled.size == source.size, "the product must not be cropped or resized"
    assert styled.mode == "RGBA"
    r, g, b = styled.convert("RGB").getpixel((60, 90))
    assert b > r and b > g, "the product's brand colour must survive styling"


def test_gta_filter_rejects_a_non_image() -> None:
    from app.services.product_image_style_service import apply_gta_style

    with pytest.raises(Exception):
        apply_gta_style(b"<!DOCTYPE html><html>not an image</html>")


def test_concurrent_background_removal_is_serialised(monkeypatch: pytest.MonkeyPatch) -> None:
    """Only one rembg inference may run at a time — two at ~900MB peak would
    threaten a 4GB host. When the guard is already held, the call degrades to
    keeping the image rather than queuing forever or OOMing."""
    monkeypatch.setattr(ai_product_service, "REMBG_WAIT_SECONDS", 0)

    acquired = ai_product_service._rembg_lock.acquire(timeout=5)
    assert acquired, "lock should be free at test start"
    try:
        png, has_alpha, error = ai_product_service._to_transparent_png(_png_bytes(transparent=False))
    finally:
        ai_product_service._rembg_lock.release()

    assert error is not None and "busy" in error.lower()
    assert has_alpha is False
    assert png, "the styled image must still be returned, not discarded"


def test_detect_extension_reads_magic_bytes_not_the_claimed_type() -> None:
    assert detect_extension(_png_bytes(transparent=True)) == ".png"
    assert detect_extension(b"\xff\xd8\xff\xe0somejpegdata") == ".jpg"
    assert detect_extension(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == ".webp"
    # An HTML error page served with image/png must not pass as an image.
    assert detect_extension(b"<!DOCTYPE html><html>nope</html>") is None
