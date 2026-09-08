import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import Region, User, UserRole
from tests.conftest import auth_headers, make_product, make_user

NAJAF = {"X-Region": "najaf"}
BAGHDAD = {"X-Region": "baghdad"}


def _admin(db: Session, *, region: Region = Region.NAJAF) -> User:
    return make_user(db, username=f"td_admin_{uuid.uuid4().hex[:6]}", password="password123", role=UserRole.ADMIN, region=region)


# ---------------------------------------------------------------------------
# Total Debts: get-or-create, set, clear (same contract as Chumber Required)
# ---------------------------------------------------------------------------


def test_default_value_is_null_but_section_is_readable(client: TestClient, db: Session) -> None:
    admin = _admin(db)
    headers = auth_headers(client, admin.username, "password123")
    response = client.get("/api/admin/total-debts", headers=headers)
    assert response.status_code == 200
    assert response.json()["amount"] is None
    assert response.json()["region"] == "najaf"


def test_customer_cannot_access_total_debts(client: TestClient, customer: User) -> None:
    headers = auth_headers(client, customer.username, "password123")
    assert client.get("/api/admin/total-debts", headers=headers).status_code == 403
    assert client.put("/api/admin/total-debts", json={"amount": 100}, headers=headers).status_code == 403
    assert client.delete("/api/admin/total-debts", headers=headers).status_code == 403


def test_admin_can_set_and_persist_value(client: TestClient, db: Session) -> None:
    admin = _admin(db)
    headers = auth_headers(client, admin.username, "password123")

    response = client.put("/api/admin/total-debts", json={"amount": 100_000}, headers=headers)
    assert response.status_code == 200
    assert response.json()["amount"] == 100_000.0

    refetched = client.get("/api/admin/total-debts", headers=headers).json()
    assert refetched["amount"] == 100_000.0


def test_admin_can_edit_the_value(client: TestClient, db: Session) -> None:
    admin = _admin(db)
    headers = auth_headers(client, admin.username, "password123")
    client.put("/api/admin/total-debts", json={"amount": 1_000}, headers=headers)
    response = client.put("/api/admin/total-debts", json={"amount": 2_000}, headers=headers)
    assert response.status_code == 200
    assert response.json()["amount"] == 2_000.0


def test_negative_amount_rejected(client: TestClient, db: Session) -> None:
    admin = _admin(db)
    headers = auth_headers(client, admin.username, "password123")
    response = client.put("/api/admin/total-debts", json={"amount": -1}, headers=headers)
    assert response.status_code == 422


def test_delete_clears_value_but_section_remains_available(client: TestClient, db: Session) -> None:
    admin = _admin(db)
    headers = auth_headers(client, admin.username, "password123")

    client.put("/api/admin/total-debts", json={"amount": 7_500}, headers=headers)
    delete_resp = client.delete("/api/admin/total-debts", headers=headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json()["amount"] is None

    after_delete = client.get("/api/admin/total-debts", headers=headers)
    assert after_delete.status_code == 200
    assert after_delete.json()["amount"] is None

    set_again = client.put("/api/admin/total-debts", json={"amount": 42}, headers=headers)
    assert set_again.status_code == 200
    assert set_again.json()["amount"] == 42.0


def test_value_is_region_scoped(client: TestClient, db: Session) -> None:
    naj_admin = _admin(db, region=Region.NAJAF)
    bag_admin = _admin(db, region=Region.BAGHDAD)

    client.put("/api/admin/total-debts", json={"amount": 111}, headers=auth_headers(client, naj_admin.username, "password123"))
    client.put("/api/admin/total-debts", json={"amount": 222}, headers=auth_headers(client, bag_admin.username, "password123"))

    naj_view = client.get("/api/admin/total-debts", headers=auth_headers(client, naj_admin.username, "password123")).json()
    bag_view = client.get("/api/admin/total-debts", headers=auth_headers(client, bag_admin.username, "password123")).json()

    assert naj_view["amount"] == 111.0
    assert bag_view["amount"] == 222.0


# ---------------------------------------------------------------------------
# Balance Difference: total_user_balance + total_debts - total_inventory_value
# ---------------------------------------------------------------------------


def test_balance_difference_matches_the_spec_example(client: TestClient, db: Session) -> None:
    """Exactly the worked example from the spec: 600,000 user money +
    100,000 debts - 1,000,000 inventory = -300,000, and it must not be
    clamped to zero."""
    admin = _admin(db, region=Region.NAJAF)
    headers = auth_headers(client, admin.username, "password123")

    cust = make_user(db, username=f"td_cust_{uuid.uuid4().hex[:6]}", password="password123", role=UserRole.CUSTOMER, region=Region.NAJAF)
    client.post(f"/api/users/{cust.id}/balance", json={"amount": 600_000}, headers=headers)

    make_product(db, name="TD Inventory Product", price=100_000, stock=10, region=Region.NAJAF)  # 1,000,000 IQD on hand

    client.put("/api/admin/total-debts", json={"amount": 100_000}, headers=headers)

    overview = client.get("/api/admin/overview", headers=headers).json()
    assert overview["total_user_balance"] == 600_000.0
    assert overview["total_debts"] == 100_000.0
    assert overview["total_inventory_value"] == 1_000_000.0
    assert overview["balance_difference"] == -300_000.0


def test_balance_difference_updates_live_after_a_recharge(client: TestClient, db: Session) -> None:
    admin = _admin(db)
    headers = auth_headers(client, admin.username, "password123")
    cust = make_user(db, username=f"td_cust2_{uuid.uuid4().hex[:6]}", password="password123", role=UserRole.CUSTOMER, region=Region.NAJAF)

    before = client.get("/api/admin/overview", headers=headers).json()["balance_difference"]
    client.post(f"/api/users/{cust.id}/balance", json={"amount": 5_000}, headers=headers)
    after = client.get("/api/admin/overview", headers=headers).json()["balance_difference"]

    assert after == before + 5_000


def test_unset_debts_counts_as_zero_in_balance_difference(client: TestClient, db: Session) -> None:
    admin = _admin(db)
    headers = auth_headers(client, admin.username, "password123")
    overview = client.get("/api/admin/overview", headers=headers).json()
    assert overview["total_debts"] == 0.0
    assert overview["balance_difference"] == overview["total_user_balance"] - overview["total_inventory_value"]


def test_clearing_debts_updates_balance_difference(client: TestClient, db: Session) -> None:
    admin = _admin(db)
    headers = auth_headers(client, admin.username, "password123")

    client.put("/api/admin/total-debts", json={"amount": 50_000}, headers=headers)
    with_debt = client.get("/api/admin/overview", headers=headers).json()["balance_difference"]

    client.delete("/api/admin/total-debts", headers=headers)
    after_clear = client.get("/api/admin/overview", headers=headers).json()["balance_difference"]

    assert after_clear == with_debt - 50_000
