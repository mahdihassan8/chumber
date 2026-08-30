from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from tests.conftest import auth_headers, make_product


def test_add_to_cart(client: TestClient, db: Session, customer: User) -> None:
    product = make_product(db, stock=5)
    headers = auth_headers(client, customer.username, "password123")
    response = client.post("/api/cart/items", json={"product_id": str(product.id), "quantity": 2}, headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 2
    assert body["total"] == 5.0


def test_cannot_exceed_stock(client: TestClient, db: Session, customer: User) -> None:
    product = make_product(db, stock=5)
    headers = auth_headers(client, customer.username, "password123")
    response = client.post("/api/cart/items", json={"product_id": str(product.id), "quantity": 6}, headers=headers)
    assert response.status_code == 400


def test_adding_twice_accumulates_and_still_respects_stock(client: TestClient, db: Session, customer: User) -> None:
    product = make_product(db, stock=5)
    headers = auth_headers(client, customer.username, "password123")
    client.post("/api/cart/items", json={"product_id": str(product.id), "quantity": 3}, headers=headers)
    response = client.post("/api/cart/items", json={"product_id": str(product.id), "quantity": 3}, headers=headers)
    assert response.status_code == 400


def test_update_quantity_clamped_to_stock(client: TestClient, db: Session, customer: User) -> None:
    product = make_product(db, stock=5)
    headers = auth_headers(client, customer.username, "password123")
    add_resp = client.post("/api/cart/items", json={"product_id": str(product.id), "quantity": 1}, headers=headers)
    item_id = add_resp.json()["items"][0]["id"]

    ok_resp = client.patch(f"/api/cart/items/{item_id}", json={"quantity": 5}, headers=headers)
    assert ok_resp.status_code == 200

    over_resp = client.patch(f"/api/cart/items/{item_id}", json={"quantity": 6}, headers=headers)
    assert over_resp.status_code == 400


def test_remove_item(client: TestClient, db: Session, customer: User) -> None:
    product = make_product(db, stock=5)
    headers = auth_headers(client, customer.username, "password123")
    add_resp = client.post("/api/cart/items", json={"product_id": str(product.id), "quantity": 1}, headers=headers)
    item_id = add_resp.json()["items"][0]["id"]

    response = client.delete(f"/api/cart/items/{item_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_quantity_below_one_rejected(client: TestClient, db: Session, customer: User) -> None:
    product = make_product(db, stock=5)
    headers = auth_headers(client, customer.username, "password123")
    response = client.post("/api/cart/items", json={"product_id": str(product.id), "quantity": 0}, headers=headers)
    assert response.status_code == 422
