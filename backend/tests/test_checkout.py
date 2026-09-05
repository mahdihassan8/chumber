from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from tests.conftest import auth_headers, make_product, make_user


def test_checkout_success_deducts_balance_and_stock(client: TestClient, db: Session, customer: User) -> None:
    product = make_product(db, price=10_000, stock=5)
    headers = auth_headers(client, customer.username, "password123")
    client.post("/api/cart/items", json={"product_id": str(product.id), "quantity": 3}, headers=headers)

    response = client.post("/api/orders/checkout", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["new_balance"] == 70_000.0  # 100,000 - 30,000
    assert body["order"]["total_amount"] == 30_000.0
    assert body["order"]["items"][0]["quantity"] == 3

    db.refresh(product)
    assert product.stock_quantity == 2

    cart_response = client.get("/api/cart", headers=headers)
    assert cart_response.json()["items"] == []


def test_checkout_insufficient_balance_fails_and_does_not_change_balance(client: TestClient, db: Session, customer: User) -> None:
    product = make_product(db, price=50_000, stock=5)
    headers = auth_headers(client, customer.username, "password123")
    client.post("/api/cart/items", json={"product_id": str(product.id), "quantity": 3}, headers=headers)  # total 150,000 > balance 100,000

    response = client.post("/api/orders/checkout", headers=headers)
    assert response.status_code == 400
    assert "Insufficient balance" in response.json()["detail"]

    db.refresh(customer)
    assert float(customer.balance) == 100_000.0

    db.refresh(product)
    assert product.stock_quantity == 5


def test_checkout_empty_cart_fails(client: TestClient, customer: User) -> None:
    headers = auth_headers(client, customer.username, "password123")
    response = client.post("/api/orders/checkout", headers=headers)
    assert response.status_code == 400


def test_checkout_rejects_stock_that_changed_after_adding_to_cart(client: TestClient, db: Session, customer: User) -> None:
    product = make_product(db, price=10_000, stock=5)
    headers = auth_headers(client, customer.username, "password123")
    client.post("/api/cart/items", json={"product_id": str(product.id), "quantity": 5}, headers=headers)

    # Simulate stock being sold/restocked down by an admin action between add-to-cart and checkout.
    product.stock_quantity = 2
    db.commit()

    response = client.post("/api/orders/checkout", headers=headers)
    assert response.status_code == 400
    assert "in stock" in response.json()["detail"]

    db.refresh(customer)
    assert float(customer.balance) == 100_000.0


def test_checkout_creates_purchase_transaction(client: TestClient, db: Session, customer: User) -> None:
    product = make_product(db, price=10_000, stock=5)
    headers = auth_headers(client, customer.username, "password123")
    client.post("/api/cart/items", json={"product_id": str(product.id), "quantity": 2}, headers=headers)
    client.post("/api/orders/checkout", headers=headers)

    response = client.get("/api/balance", headers=headers)
    transactions = response.json()["transactions"]
    assert any(t["transaction_type"] == "purchase" and t["amount"] == -20_000.0 for t in transactions)


def test_checkout_free_product_charges_nothing(client: TestClient, db: Session, customer: User) -> None:
    product = make_product(db, name="Free Sample", price=0, stock=5)
    headers = auth_headers(client, customer.username, "password123")
    client.post("/api/cart/items", json={"product_id": str(product.id), "quantity": 2}, headers=headers)

    response = client.post("/api/orders/checkout", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["new_balance"] == 100_000.0  # unchanged — customer fixture starts at 100,000 IQD
    assert body["order"]["total_amount"] == 0.0

    db.refresh(product)
    assert product.stock_quantity == 3


def test_customer_with_zero_balance_can_claim_free_product(client: TestClient, db: Session) -> None:
    poor_customer = make_user(db, username="poor_customer", password="password123", role=UserRole.CUSTOMER, balance=0)
    product = make_product(db, name="Free Sample", price=0, stock=5)
    headers = auth_headers(client, poor_customer.username, "password123")
    client.post("/api/cart/items", json={"product_id": str(product.id), "quantity": 1}, headers=headers)

    response = client.post("/api/orders/checkout", headers=headers)
    assert response.status_code == 200
    assert response.json()["new_balance"] == 0.0
