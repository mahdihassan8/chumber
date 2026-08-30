from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from tests.conftest import auth_headers, make_product, make_user


def _buy(client: TestClient, headers: dict, product_id: str, quantity: int) -> None:
    resp = client.post("/api/cart/items", json={"product_id": product_id, "quantity": quantity}, headers=headers)
    assert resp.status_code == 201, resp.text
    resp = client.post("/api/orders/checkout", headers=headers)
    assert resp.status_code == 200, resp.text


def test_customer_cannot_create_product(client: TestClient, customer: User) -> None:
    headers = auth_headers(client, customer.username, "password123")
    response = client.post(
        "/api/products", json={"name": "Sprite", "price": 2, "stock_quantity": 5}, headers=headers
    )
    assert response.status_code == 403


def test_admin_can_create_product(client: TestClient, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(
        "/api/products", json={"name": "Sprite", "price": 2, "stock_quantity": 5, "description": "Lemon soda"}, headers=headers
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Sprite"
    assert body["is_available"] is True


def test_out_of_stock_product_hidden_from_customer(client: TestClient, db: Session, customer: User) -> None:
    make_product(db, name="Out Of Stock Soda", stock=0)
    headers = auth_headers(client, customer.username, "password123")
    response = client.get("/api/products", headers=headers)
    assert response.status_code == 200
    names = [p["name"] for p in response.json()]
    assert "Out Of Stock Soda" not in names


def test_out_of_stock_product_visible_to_admin(client: TestClient, db: Session, admin: User) -> None:
    make_product(db, name="Out Of Stock Soda", stock=0)
    headers = auth_headers(client, admin.username, "password123")
    response = client.get("/api/products", headers=headers)
    assert response.status_code == 200
    names = [p["name"] for p in response.json()]
    assert "Out Of Stock Soda" in names


def test_customer_cannot_restock(client: TestClient, db: Session, customer: User) -> None:
    product = make_product(db)
    headers = auth_headers(client, customer.username, "password123")
    response = client.post(f"/api/products/{product.id}/restock", json={"quantity": 10}, headers=headers)
    assert response.status_code == 403


def test_admin_restock_increases_stock(client: TestClient, db: Session, admin: User) -> None:
    product = make_product(db, stock=0, is_active=False)
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(f"/api/products/{product.id}/restock", json={"quantity": 20}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["stock_quantity"] == 20
    assert body["is_available"] is True


def test_customer_cannot_change_price(client: TestClient, db: Session, customer: User) -> None:
    product = make_product(db, price=5)
    headers = auth_headers(client, customer.username, "password123")
    response = client.patch(f"/api/products/{product.id}", json={"price": 1}, headers=headers)
    assert response.status_code == 403


def test_infinite_price_rejected_on_create(client: TestClient, admin: User) -> None:
    # Sent as a raw body: httpx's own `json=` encoder refuses to serialize
    # inf/nan at all, but a non-browser client can send it as raw JSON.
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(
        "/api/products",
        content='{"name": "Bad Price", "price": Infinity, "stock_quantity": 1}',
        headers={**headers, "Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_infinite_price_rejected_on_update(client: TestClient, db: Session, admin: User) -> None:
    product = make_product(db, price=5)
    headers = auth_headers(client, admin.username, "password123")
    response = client.patch(
        f"/api/products/{product.id}", content='{"price": Infinity}', headers={**headers, "Content-Type": "application/json"}
    )
    assert response.status_code == 422

    db.refresh(product)
    assert float(product.price) == 5.0


def test_absurdly_large_price_rejected(client: TestClient, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.post("/api/products", json={"name": "Too Expensive", "price": 999_999_999, "stock_quantity": 1}, headers=headers)
    assert response.status_code == 422


def test_product_list_sorted_by_sales_best_seller_first(client: TestClient, db: Session, admin: User) -> None:
    buyer = make_user(db, username="sort_buyer", password="password123", role=UserRole.CUSTOMER, balance=100_000)
    buyer_headers = auth_headers(client, buyer.username, "password123")
    admin_headers = auth_headers(client, admin.username, "password123")

    # Create in a different order than final sales rank to prove sorting
    # isn't just falling back to creation order.
    low = make_product(db, name="Low Seller", price=1, stock=50)
    high = make_product(db, name="High Seller", price=1, stock=50)
    mid = make_product(db, name="Mid Seller", price=1, stock=50)
    make_product(db, name="Never Sold", price=1, stock=50)

    _buy(client, buyer_headers, str(low.id), 5)
    _buy(client, buyer_headers, str(high.id), 30)
    _buy(client, buyer_headers, str(mid.id), 15)

    names = [p["name"] for p in client.get("/api/products", headers=admin_headers).json()]
    assert names == ["High Seller", "Mid Seller", "Low Seller", "Never Sold"]


def test_product_list_ranking_updates_after_sale_shifts_it_to_top(client: TestClient, db: Session, admin: User) -> None:
    buyer = make_user(db, username="sort_buyer2", password="password123", role=UserRole.CUSTOMER, balance=100_000)
    buyer_headers = auth_headers(client, buyer.username, "password123")
    admin_headers = auth_headers(client, admin.username, "password123")

    leader = make_product(db, name="Leader", price=1, stock=100)
    challenger = make_product(db, name="Challenger", price=1, stock=100)

    _buy(client, buyer_headers, str(leader.id), 10)
    _buy(client, buyer_headers, str(challenger.id), 5)
    names = [p["name"] for p in client.get("/api/products", headers=admin_headers).json()]
    assert names[0] == "Leader"

    _buy(client, buyer_headers, str(challenger.id), 20)
    names = [p["name"] for p in client.get("/api/products", headers=admin_headers).json()]
    assert names[0] == "Challenger"
