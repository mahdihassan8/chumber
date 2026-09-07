from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import Region, User, UserRole
from tests.conftest import auth_headers, make_product, make_user


class _FakeModels:
    def __init__(self, tool_input: dict) -> None:
        self._tool_input = tool_input

    def generate_content(self, **kwargs):  # noqa: ANN003, ANN201
        from app.services.ai_service import _RestockAction

        return SimpleNamespace(parsed=_RestockAction(**self._tool_input))


class _FakeGenaiClient:
    def __init__(self, tool_input: dict) -> None:
        self.models = _FakeModels(tool_input)


def _patch_gemini(monkeypatch: pytest.MonkeyPatch, tool_input: dict) -> None:
    import app.services.ai_service as ai_service

    monkeypatch.setattr(ai_service.settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(ai_service.genai, "Client", lambda api_key, http_options=None: _FakeGenaiClient(tool_input))


def test_customer_cannot_access_ai_parse(client: TestClient, customer: User) -> None:
    headers = auth_headers(client, customer.username, "password123")
    response = client.post("/api/ai/restock/parse", json={"message": "Add 20 Coca Cola"}, headers=headers)
    assert response.status_code == 403


def test_customer_cannot_access_ai_history(client: TestClient, customer: User) -> None:
    headers = auth_headers(client, customer.username, "password123")
    response = client.get("/api/ai/restock/history", headers=headers)
    assert response.status_code == 403


def test_ai_not_configured_returns_failed_status(client: TestClient, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.post("/api/ai/restock/parse", json={"message": "Add 20 Coca Cola"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "failed"


def test_ai_parse_resolves_matching_product(
    client: TestClient, db: Session, admin: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    product = make_product(db, name="Coca Cola", stock=5)
    _patch_gemini(monkeypatch, {"action": "restock", "product_name": "Coca Cola", "quantity": 20})

    headers = auth_headers(client, admin.username, "password123")
    response = client.post("/api/ai/restock/parse", json={"message": "Add 20 Coca Cola"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["resolved_product_id"] == str(product.id)
    assert body["parsed_quantity"] == 20


def test_ai_confirm_applies_stock_and_requires_admin(
    client: TestClient, db: Session, admin: User, customer: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    product = make_product(db, name="Coca Cola", stock=5)
    _patch_gemini(monkeypatch, {"action": "restock", "product_name": "Coca Cola", "quantity": 20})

    admin_headers = auth_headers(client, admin.username, "password123")
    parse_resp = client.post("/api/ai/restock/parse", json={"message": "Add 20 Coca Cola"}, headers=admin_headers)
    request_id = parse_resp.json()["id"]

    customer_headers = auth_headers(client, customer.username, "password123")
    forbidden_resp = client.post(f"/api/ai/restock/{request_id}/confirm", headers=customer_headers)
    assert forbidden_resp.status_code == 403

    confirm_resp = client.post(f"/api/ai/restock/{request_id}/confirm", headers=admin_headers)
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "confirmed"

    db.refresh(product)
    assert product.stock_quantity == 25


def test_ai_confirm_rejects_when_no_product_matched(
    client: TestClient, admin: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_gemini(monkeypatch, {"action": "restock", "product_name": "Nonexistent Product Xyz", "quantity": 10})
    headers = auth_headers(client, admin.username, "password123")
    parse_resp = client.post("/api/ai/restock/parse", json={"message": "Add 10 Nonexistent Product Xyz"}, headers=headers)
    request_id = parse_resp.json()["id"]
    assert parse_resp.json()["resolved_product_id"] is None

    confirm_resp = client.post(f"/api/ai/restock/{request_id}/confirm", headers=headers)
    assert confirm_resp.status_code == 400


def test_ai_reject_does_not_change_stock(
    client: TestClient, db: Session, admin: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    product = make_product(db, name="Coca Cola", stock=5)
    _patch_gemini(monkeypatch, {"action": "restock", "product_name": "Coca Cola", "quantity": 20})
    headers = auth_headers(client, admin.username, "password123")
    parse_resp = client.post("/api/ai/restock/parse", json={"message": "Add 20 Coca Cola"}, headers=headers)
    request_id = parse_resp.json()["id"]

    reject_resp = client.post(f"/api/ai/restock/{request_id}/reject", headers=headers)
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "rejected"

    db.refresh(product)
    assert product.stock_quantity == 5


def test_voice_input_type_recorded(client: TestClient, db: Session, admin: User, monkeypatch: pytest.MonkeyPatch) -> None:
    make_product(db, name="Coca Cola", stock=5)
    _patch_gemini(monkeypatch, {"action": "restock", "product_name": "Coca Cola", "quantity": 15})
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(
        "/api/ai/restock/parse", json={"message": "Add fifteen bottles of Coca Cola", "input_type": "voice"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["input_type"] == "voice"


# ---------------------------------------------------------------------------
# Region isolation: the AI assistant must never discover or restock a
# product outside the admin's current region.
# ---------------------------------------------------------------------------

NAJAF = {"X-Region": "najaf"}
BAGHDAD = {"X-Region": "baghdad"}


def test_najaf_admin_ai_restock_of_najaf_product_succeeds(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    naj_admin = make_user(db, username="ai_naj_admin1", password="password123", role=UserRole.ADMIN, region=Region.NAJAF)
    product = make_product(db, name="Najaf Cola", stock=5, region=Region.NAJAF)
    _patch_gemini(monkeypatch, {"action": "restock", "product_name": "Najaf Cola", "quantity": 10})

    headers = {**auth_headers(client, naj_admin.username, "password123"), **NAJAF}
    parse_resp = client.post("/api/ai/restock/parse", json={"message": "Add 10 Najaf Cola"}, headers=headers)
    assert parse_resp.json()["resolved_product_id"] == str(product.id)

    confirm_resp = client.post(f"/api/ai/restock/{parse_resp.json()['id']}/confirm", headers=headers)
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "confirmed"

    db.refresh(product)
    assert product.stock_quantity == 15


def test_najaf_admin_cannot_discover_baghdad_product(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    naj_admin = make_user(db, username="ai_naj_admin2", password="password123", role=UserRole.ADMIN, region=Region.NAJAF)
    baghdad_product = make_product(db, name="Baghdad Pepsi AI", stock=5, region=Region.BAGHDAD)
    _patch_gemini(monkeypatch, {"action": "restock", "product_name": "Baghdad Pepsi AI", "quantity": 10})

    headers = {**auth_headers(client, naj_admin.username, "password123"), **NAJAF}
    parse_resp = client.post("/api/ai/restock/parse", json={"message": "Add 10 Baghdad Pepsi AI"}, headers=headers)
    assert parse_resp.json()["resolved_product_id"] is None

    db.refresh(baghdad_product)
    assert baghdad_product.stock_quantity == 5


def test_baghdad_admin_ai_restock_of_baghdad_product_succeeds(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    bag_admin = make_user(db, username="ai_bag_admin1", password="password123", role=UserRole.ADMIN, region=Region.BAGHDAD)
    product = make_product(db, name="Baghdad Sprite", stock=5, region=Region.BAGHDAD)
    _patch_gemini(monkeypatch, {"action": "restock", "product_name": "Baghdad Sprite", "quantity": 8})

    headers = {**auth_headers(client, bag_admin.username, "password123"), **BAGHDAD}
    parse_resp = client.post("/api/ai/restock/parse", json={"message": "Add 8 Baghdad Sprite"}, headers=headers)
    assert parse_resp.json()["resolved_product_id"] == str(product.id)

    confirm_resp = client.post(f"/api/ai/restock/{parse_resp.json()['id']}/confirm", headers=headers)
    assert confirm_resp.status_code == 200

    db.refresh(product)
    assert product.stock_quantity == 13


def test_baghdad_admin_cannot_discover_najaf_product(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    bag_admin = make_user(db, username="ai_bag_admin2", password="password123", role=UserRole.ADMIN, region=Region.BAGHDAD)
    najaf_product = make_product(db, name="Najaf Fanta AI", stock=5, region=Region.NAJAF)
    _patch_gemini(monkeypatch, {"action": "restock", "product_name": "Najaf Fanta AI", "quantity": 10})

    headers = {**auth_headers(client, bag_admin.username, "password123"), **BAGHDAD}
    parse_resp = client.post("/api/ai/restock/parse", json={"message": "Add 10 Najaf Fanta AI"}, headers=headers)
    assert parse_resp.json()["resolved_product_id"] is None

    db.refresh(najaf_product)
    assert najaf_product.stock_quantity == 5


def test_confirm_rejects_product_no_longer_in_current_region(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Defense in depth for confirm itself, not just parse: even if a request
    somehow carries a resolved_product_id outside the caller's current region,
    confirm must 404 via the same region-aware lookup every other by-id
    product path uses, rather than restocking it."""
    boss = make_user(db, username="ai_boss1", password="password123", role=UserRole.SUPER_ADMIN, region=Region.NAJAF)
    baghdad_product = make_product(db, name="Baghdad Fanta AI", stock=5, region=Region.BAGHDAD)
    _patch_gemini(monkeypatch, {"action": "restock", "product_name": "Baghdad Fanta AI", "quantity": 10})

    # A Super Admin can act in Baghdad, so parsing there resolves the product...
    parse_headers = {**auth_headers(client, boss.username, "password123"), **BAGHDAD}
    parse_resp = client.post("/api/ai/restock/parse", json={"message": "Add 10 Baghdad Fanta AI"}, headers=parse_headers)
    assert parse_resp.json()["resolved_product_id"] == str(baghdad_product.id)

    # ...but a regular Najaf-only admin confirming that same request id must
    # not be able to restock the Baghdad product just because it was already
    # resolved.
    naj_admin = make_user(db, username="ai_naj_admin3", password="password123", role=UserRole.ADMIN, region=Region.NAJAF)
    confirm_headers = {**auth_headers(client, naj_admin.username, "password123"), **NAJAF}
    confirm_resp = client.post(f"/api/ai/restock/{parse_resp.json()['id']}/confirm", headers=confirm_headers)
    assert confirm_resp.status_code == 404

    db.refresh(baghdad_product)
    assert baghdad_product.stock_quantity == 5


def test_forged_region_header_rejected_on_ai_parse(client: TestClient, db: Session) -> None:
    naj_admin = make_user(db, username="ai_naj_admin4", password="password123", role=UserRole.ADMIN, region=Region.NAJAF)
    headers = {**auth_headers(client, naj_admin.username, "password123"), **BAGHDAD}
    response = client.post("/api/ai/restock/parse", json={"message": "Add 10 Something"}, headers=headers)
    assert response.status_code == 403


def test_forged_region_header_rejected_on_ai_confirm(client: TestClient, db: Session) -> None:
    naj_admin = make_user(db, username="ai_naj_admin5", password="password123", role=UserRole.ADMIN, region=Region.NAJAF)
    headers = {**auth_headers(client, naj_admin.username, "password123"), **BAGHDAD}
    response = client.post("/api/ai/restock/00000000-0000-0000-0000-000000000000/confirm", headers=headers)
    assert response.status_code == 403
