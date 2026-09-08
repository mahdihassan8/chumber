import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import Region, User, UserRole
from tests.conftest import auth_headers, make_product, make_user

NAJAF = {"X-Region": "najaf"}
BAGHDAD = {"X-Region": "baghdad"}


def _admin(db: Session, *, region: Region = Region.NAJAF) -> User:
    return make_user(db, username=f"cr_admin_{uuid.uuid4().hex[:6]}", password="password123", role=UserRole.ADMIN, region=region)


# ---------------------------------------------------------------------------
# Chumber Required: get-or-create, set, clear
# ---------------------------------------------------------------------------


def test_default_value_is_null_but_section_is_readable(client: TestClient, db: Session) -> None:
    admin = _admin(db)
    headers = auth_headers(client, admin.username, "password123")
    response = client.get("/api/admin/chumber-required", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["amount"] is None
    assert body["note"] is None
    assert body["region"] == "najaf"


def test_customer_cannot_access_chumber_required(client: TestClient, customer: User) -> None:
    headers = auth_headers(client, customer.username, "password123")
    assert client.get("/api/admin/chumber-required", headers=headers).status_code == 403
    assert client.put("/api/admin/chumber-required", json={"amount": 100}, headers=headers).status_code == 403
    assert client.delete("/api/admin/chumber-required", headers=headers).status_code == 403


def test_admin_can_set_and_persist_value_and_note(client: TestClient, db: Session) -> None:
    admin = _admin(db)
    headers = auth_headers(client, admin.username, "password123")

    response = client.put("/api/admin/chumber-required", json={"amount": 50000, "note": "Restock target for the week"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["amount"] == 50000.0
    assert body["note"] == "Restock target for the week"

    # Persists across a fresh GET, i.e. it's really in the database, not just echoed back.
    refetched = client.get("/api/admin/chumber-required", headers=headers).json()
    assert refetched["amount"] == 50000.0
    assert refetched["note"] == "Restock target for the week"


def test_admin_can_edit_the_value(client: TestClient, db: Session) -> None:
    admin = _admin(db)
    headers = auth_headers(client, admin.username, "password123")

    client.put("/api/admin/chumber-required", json={"amount": 1000, "note": "first"}, headers=headers)
    response = client.put("/api/admin/chumber-required", json={"amount": 2000, "note": "second"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["amount"] == 2000.0
    assert response.json()["note"] == "second"


def test_note_is_optional(client: TestClient, db: Session) -> None:
    admin = _admin(db)
    headers = auth_headers(client, admin.username, "password123")
    response = client.put("/api/admin/chumber-required", json={"amount": 5000}, headers=headers)
    assert response.status_code == 200
    assert response.json()["note"] is None


def test_negative_amount_rejected(client: TestClient, db: Session) -> None:
    admin = _admin(db)
    headers = auth_headers(client, admin.username, "password123")
    response = client.put("/api/admin/chumber-required", json={"amount": -100}, headers=headers)
    assert response.status_code == 422


def test_delete_clears_value_but_section_remains_available(client: TestClient, db: Session) -> None:
    admin = _admin(db)
    headers = auth_headers(client, admin.username, "password123")

    client.put("/api/admin/chumber-required", json={"amount": 7500, "note": "note"}, headers=headers)
    delete_resp = client.delete("/api/admin/chumber-required", headers=headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json()["amount"] is None
    assert delete_resp.json()["note"] is None

    # The section is still there afterwards -- GET still works (not 404), and
    # a brand new value can be set right after, proving the row/input wasn't
    # removed, only its contents.
    after_delete = client.get("/api/admin/chumber-required", headers=headers)
    assert after_delete.status_code == 200
    assert after_delete.json()["amount"] is None

    set_again = client.put("/api/admin/chumber-required", json={"amount": 999, "note": None}, headers=headers)
    assert set_again.status_code == 200
    assert set_again.json()["amount"] == 999.0


def test_value_is_region_scoped(client: TestClient, db: Session) -> None:
    naj_admin = _admin(db, region=Region.NAJAF)
    bag_admin = _admin(db, region=Region.BAGHDAD)

    client.put("/api/admin/chumber-required", json={"amount": 111, "note": "najaf figure"}, headers=auth_headers(client, naj_admin.username, "password123"))
    client.put("/api/admin/chumber-required", json={"amount": 222, "note": "baghdad figure"}, headers=auth_headers(client, bag_admin.username, "password123"))

    naj_view = client.get("/api/admin/chumber-required", headers=auth_headers(client, naj_admin.username, "password123")).json()
    bag_view = client.get("/api/admin/chumber-required", headers=auth_headers(client, bag_admin.username, "password123")).json()

    assert naj_view["amount"] == 111.0
    assert bag_view["amount"] == 222.0
    assert naj_view["note"] != bag_view["note"]


def test_super_admin_can_switch_region_to_edit_either(client: TestClient, db: Session) -> None:
    boss = make_user(db, username=f"cr_boss_{uuid.uuid4().hex[:6]}", password="password123", role=UserRole.SUPER_ADMIN, region=Region.NAJAF)
    headers = auth_headers(client, boss.username, "password123")

    client.put("/api/admin/chumber-required", json={"amount": 10}, headers={**headers, **NAJAF})
    client.put("/api/admin/chumber-required", json={"amount": 20}, headers={**headers, **BAGHDAD})

    assert client.get("/api/admin/chumber-required", headers={**headers, **NAJAF}).json()["amount"] == 10.0
    assert client.get("/api/admin/chumber-required", headers={**headers, **BAGHDAD}).json()["amount"] == 20.0


# ---------------------------------------------------------------------------
# Overview: total user money / total inventory value are live, not stored
# ---------------------------------------------------------------------------


def test_total_user_balance_reflects_current_wallets(client: TestClient, db: Session) -> None:
    admin = _admin(db)
    headers = auth_headers(client, admin.username, "password123")
    cust = make_user(db, username=f"cr_cust_{uuid.uuid4().hex[:6]}", password="password123", role=UserRole.CUSTOMER, region=Region.NAJAF, balance=10_000)

    before = client.get("/api/admin/overview", headers=headers).json()["total_user_balance"]

    client.post(f"/api/users/{cust.id}/balance", json={"amount": 5_000}, headers=headers)
    after_credit = client.get("/api/admin/overview", headers=headers).json()["total_user_balance"]
    assert after_credit == before + 5_000

    client.post(f"/api/users/{cust.id}/balance/subtract", json={"amount": 2_000}, headers=headers)
    after_debit = client.get("/api/admin/overview", headers=headers).json()["total_user_balance"]
    assert after_debit == before + 3_000


def test_total_user_balance_decreases_after_checkout_spend(client: TestClient, db: Session) -> None:
    admin = _admin(db)
    headers = auth_headers(client, admin.username, "password123")
    cust = make_user(db, username=f"cr_spend_{uuid.uuid4().hex[:6]}", password="password123", role=UserRole.CUSTOMER, region=Region.NAJAF, balance=10_000)
    product = make_product(db, name="CR Test Product", price=3_000, stock=10, region=Region.NAJAF)

    before = client.get("/api/admin/overview", headers=headers).json()["total_user_balance"]

    cust_headers = auth_headers(client, cust.username, "password123")
    client.post("/api/cart/items", json={"product_id": str(product.id), "quantity": 1}, headers=cust_headers)
    checkout = client.post("/api/orders/checkout", headers=cust_headers)
    assert checkout.status_code == 200

    after = client.get("/api/admin/overview", headers=headers).json()["total_user_balance"]
    assert after == before - 3_000


def test_total_inventory_value_reflects_price_times_stock(client: TestClient, db: Session) -> None:
    admin = _admin(db)
    headers = auth_headers(client, admin.username, "password123")
    product = make_product(db, name="CR Inventory Product", price=1_500, stock=4, region=Region.NAJAF)

    before = client.get("/api/admin/overview", headers=headers).json()["total_inventory_value"]

    client.post(f"/api/products/{product.id}/restock", json={"quantity": 6}, headers=headers)
    after_restock = client.get("/api/admin/overview", headers=headers).json()["total_inventory_value"]
    assert after_restock == before + 1_500 * 6


def test_total_inventory_value_decreases_after_purchase(client: TestClient, db: Session) -> None:
    admin = _admin(db)
    headers = auth_headers(client, admin.username, "password123")
    cust = make_user(db, username=f"cr_inv_cust_{uuid.uuid4().hex[:6]}", password="password123", role=UserRole.CUSTOMER, region=Region.NAJAF, balance=50_000)
    product = make_product(db, name="CR Purchasable", price=2_000, stock=10, region=Region.NAJAF)

    before = client.get("/api/admin/overview", headers=headers).json()["total_inventory_value"]

    cust_headers = auth_headers(client, cust.username, "password123")
    client.post("/api/cart/items", json={"product_id": str(product.id), "quantity": 2}, headers=cust_headers)
    assert client.post("/api/orders/checkout", headers=cust_headers).status_code == 200

    after = client.get("/api/admin/overview", headers=headers).json()["total_inventory_value"]
    assert after == before - 2_000 * 2


def test_overview_totals_are_region_scoped(client: TestClient, db: Session) -> None:
    naj_admin = _admin(db, region=Region.NAJAF)
    bag_admin = _admin(db, region=Region.BAGHDAD)
    make_user(db, username=f"cr_naj_cust_{uuid.uuid4().hex[:6]}", password="password123", role=UserRole.CUSTOMER, region=Region.NAJAF, balance=40_000)
    make_user(db, username=f"cr_bag_cust_{uuid.uuid4().hex[:6]}", password="password123", role=UserRole.CUSTOMER, region=Region.BAGHDAD, balance=99_000)

    naj_total = client.get("/api/admin/overview", headers=auth_headers(client, naj_admin.username, "password123")).json()["total_user_balance"]
    bag_total = client.get("/api/admin/overview", headers=auth_headers(client, bag_admin.username, "password123")).json()["total_user_balance"]

    assert naj_total != bag_total
    assert bag_total >= 99_000
    assert naj_total >= 40_000
