from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from tests.conftest import auth_headers


def test_customer_cannot_list_users(client: TestClient, customer: User) -> None:
    headers = auth_headers(client, customer.username, "password123")
    response = client.get("/api/users", headers=headers)
    assert response.status_code == 403


def test_admin_can_create_customer(client: TestClient, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(
        "/api/users",
        json={"username": "newcust", "email": "newcust@example.com", "full_name": "New Cust", "password": "password123", "role": "customer"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["role"] == "customer"


def test_admin_can_create_admin(client: TestClient, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(
        "/api/users",
        json={"username": "newadmin", "email": "newadmin@example.com", "full_name": "New Admin", "password": "password123", "role": "admin"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["role"] == "admin"


def test_customer_cannot_create_users(client: TestClient, customer: User) -> None:
    headers = auth_headers(client, customer.username, "password123")
    response = client.post(
        "/api/users",
        json={"username": "hacker", "email": "hacker@example.com", "full_name": "Hacker", "password": "password123", "role": "admin"},
        headers=headers,
    )
    assert response.status_code == 403


def test_admin_can_deactivate_user(client: TestClient, db: Session, admin: User, customer: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.patch(f"/api/users/{customer.id}", json={"is_active": False}, headers=headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    login_resp = client.post("/api/auth/login", json={"username": customer.username, "password": "password123"})
    assert login_resp.status_code == 401


def test_admin_can_change_role(client: TestClient, admin: User, customer: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.patch(f"/api/users/{customer.id}", json={"role": "admin"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_customer_cannot_change_own_role(client: TestClient, customer: User) -> None:
    headers = auth_headers(client, customer.username, "password123")
    response = client.patch(f"/api/users/{customer.id}", json={"role": "admin"}, headers=headers)
    assert response.status_code == 403


def test_admin_route_forbidden_for_customer(client: TestClient, customer: User) -> None:
    headers = auth_headers(client, customer.username, "password123")
    response = client.get("/api/admin/overview", headers=headers)
    assert response.status_code == 403


def test_admin_overview_accessible_to_admin(client: TestClient, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.get("/api/admin/overview", headers=headers)
    assert response.status_code == 200
    assert "total_users" in response.json()


def test_admin_overview_recent_activity_shows_each_row_in_its_own_account_currency(
    client: TestClient, db: Session, customer: User, admin: User
) -> None:
    """recent_transactions spans multiple users' ledgers — since currency now
    lives on the account (not the transaction), each row must reflect its
    own owning account's currency rather than one currency for the whole
    feed."""
    from tests.conftest import make_user

    iqd_user = make_user(db, username="iqd_overview_user", password="password123", role=UserRole.CUSTOMER, balance=0)
    headers = auth_headers(client, admin.username, "password123")

    client.patch(f"/api/users/{iqd_user.id}/currency", json={"currency": "IQD"}, headers=headers)
    client.post(f"/api/users/{iqd_user.id}/balance", json={"amount": 1000, "description": "iqd row"}, headers=headers)
    client.post(f"/api/users/{customer.id}/balance", json={"amount": 25, "description": "usd row"}, headers=headers)

    response = client.get("/api/admin/overview", headers=headers)
    assert response.status_code == 200
    txns = response.json()["recent_transactions"]
    iqd_row = next(t for t in txns if t["description"] == "iqd row")
    usd_row = next(t for t in txns if t["description"] == "usd row")
    assert iqd_row["currency"] == "IQD"
    assert usd_row["currency"] == "USD"


def test_admin_is_also_a_normal_customer(client: TestClient, db: Session, admin: User) -> None:
    from tests.conftest import make_product

    product = make_product(db, price=5, stock=10)
    headers = auth_headers(client, admin.username, "password123")

    add_resp = client.post("/api/cart/items", json={"product_id": str(product.id), "quantity": 2}, headers=headers)
    assert add_resp.status_code == 201

    checkout_resp = client.post("/api/orders/checkout", headers=headers)
    assert checkout_resp.status_code == 200
    assert checkout_resp.json()["new_balance"] == 90.0


def test_customer_cannot_list_all_orders(client: TestClient, customer: User) -> None:
    headers = auth_headers(client, customer.username, "password123")
    response = client.get("/api/admin/orders", headers=headers)
    assert response.status_code == 403


def test_admin_orders_list_includes_buyer_info(client: TestClient, db: Session, admin: User, customer: User) -> None:
    from tests.conftest import make_product

    product = make_product(db, price=5, stock=10)
    customer_headers = auth_headers(client, customer.username, "password123")
    client.post("/api/cart/items", json={"product_id": str(product.id), "quantity": 1}, headers=customer_headers)
    checkout_resp = client.post("/api/orders/checkout", headers=customer_headers)
    assert checkout_resp.status_code == 200
    order_id = checkout_resp.json()["order"]["id"]
    assert checkout_resp.json()["order"]["user_username"] == customer.username
    assert checkout_resp.json()["order"]["user_full_name"] == customer.full_name

    admin_headers = auth_headers(client, admin.username, "password123")
    response = client.get("/api/admin/orders", headers=admin_headers)
    assert response.status_code == 200
    order = next(o for o in response.json() if o["id"] == order_id)
    assert order["user_username"] == customer.username
    assert order["user_full_name"] == customer.full_name
