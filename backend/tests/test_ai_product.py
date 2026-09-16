import io
import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image
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
            {
                "product_name": "Snickers Bar",
                "description": "A chocolate bar with nougat and peanuts.",
                "image_url": "https://example.com/snickers.png",
                "source_title": "Example Store",
                "suggested_price_iqd": 1500,
                "image_prompt": "GTA cover art style Snickers bar, bold outlines",
            },
            None,
        ),
    )
    monkeypatch.setattr(ai_product_service, "fetch_image", lambda url: (_png_bytes(transparent=False), ".png"))
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


def test_unusable_image_url_fails_the_draft_cleanly(
    client: TestClient, db: Session, admin: User, monkeypatch: pytest.MonkeyPatch, fake_ai: None
) -> None:
    def _reject(url: str):  # noqa: ANN202
        raise HTTPException(status_code=400, detail="Image host resolves to a non-public address")

    monkeypatch.setattr(ai_product_service, "fetch_image", _reject)
    response = client.post(
        "/api/ai/products/draft", json={"name": "Snickers"}, headers=auth_headers(client, admin.username, "password123")
    )

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert db.query(AIProductDraft).filter(AIProductDraft.status == AIRequestStatus.FAILED).count() == 1
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


def test_detect_extension_reads_magic_bytes_not_the_claimed_type() -> None:
    assert detect_extension(_png_bytes(transparent=True)) == ".png"
    assert detect_extension(b"\xff\xd8\xff\xe0somejpegdata") == ".jpg"
    assert detect_extension(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == ".webp"
    # An HTML error page served with image/png must not pass as an image.
    assert detect_extension(b"<!DOCTYPE html><html>nope</html>") is None
