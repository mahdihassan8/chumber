from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from tests.conftest import auth_headers, make_product


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
