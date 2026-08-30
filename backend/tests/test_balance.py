from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from tests.conftest import auth_headers


def test_customer_can_view_own_balance(client: TestClient, customer: User) -> None:
    headers = auth_headers(client, customer.username, "password123")
    response = client.get("/api/balance", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["balance"] == 100.0
    # The customer fixture's starting balance is a plain DB seed, not a
    # ledger transaction, so received/spent are 0 even though balance is 100.
    assert body["total_received"] == 0.0
    assert body["total_spent"] == 0.0


def test_balance_breakdown_reflects_received_and_spent(client: TestClient, db: Session, customer: User, admin: User) -> None:
    from tests.conftest import make_product

    product = make_product(db, price=30, stock=10)
    admin_headers = auth_headers(client, admin.username, "password123")
    customer_headers = auth_headers(client, customer.username, "password123")

    client.post(f"/api/users/{customer.id}/balance", json={"amount": 50, "description": "First top-up"}, headers=admin_headers)
    client.post(f"/api/users/{customer.id}/balance", json={"amount": 20, "description": "Second top-up"}, headers=admin_headers)

    client.post("/api/cart/items", json={"product_id": str(product.id), "quantity": 1}, headers=customer_headers)
    client.post("/api/orders/checkout", headers=customer_headers)

    response = client.get(f"/api/users/{customer.id}/balance", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    # balance: 100 (seed) + 50 + 20 - 30 = 140
    assert body["balance"] == 140.0
    assert body["total_received"] == 70.0  # 50 + 20 (seed balance isn't a ledger transaction)
    assert body["total_spent"] == 30.0
    assert len(body["transactions"]) == 3
    # the recharging admin is identified by username, not just a raw id
    recharge_txns = [t for t in body["transactions"] if t["transaction_type"] == "admin_recharge"]
    assert all(t["created_by_username"] == admin.username for t in recharge_txns)
    purchase_txn = next(t for t in body["transactions"] if t["transaction_type"] == "purchase")
    assert purchase_txn["created_by_username"] is None


def test_balance_transactions_ordered_newest_first(client: TestClient, db: Session, customer: User, admin: User) -> None:
    from datetime import datetime, timedelta, timezone

    from app.models.transaction import BalanceTransaction, TransactionType

    base = datetime.now(timezone.utc)
    # Insert directly with explicit, distinct timestamps: the API always
    # uses now() (see get_balance_summary's comment on why that ties within
    # a transaction), so this is the only way to test the sort itself rather
    # than the tie-breaker.
    for i, label in enumerate(["oldest", "middle", "newest"]):
        db.add(
            BalanceTransaction(
                user_id=customer.id,
                amount=10,
                transaction_type=TransactionType.ADJUSTMENT,
                description=label,
                created_at=base + timedelta(minutes=i),
            )
        )
    db.commit()

    headers = auth_headers(client, admin.username, "password123")
    response = client.get(f"/api/users/{customer.id}/balance", headers=headers)
    assert response.status_code == 200
    descriptions = [t["description"] for t in response.json()["transactions"]]
    assert descriptions == ["newest", "middle", "oldest"]


def test_admin_can_add_balance_to_customer(client: TestClient, db: Session, customer: User, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(f"/api/users/{customer.id}/balance", json={"amount": 50, "description": "Top up"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["balance"] == 150.0

    db.refresh(customer)
    assert float(customer.balance) == 150.0


def test_customer_cannot_add_own_balance(client: TestClient, customer: User) -> None:
    headers = auth_headers(client, customer.username, "password123")
    response = client.post(f"/api/users/{customer.id}/balance", json={"amount": 50}, headers=headers)
    assert response.status_code == 403


def test_customer_cannot_add_balance_to_another_user(client: TestClient, db: Session, customer: User) -> None:
    from tests.conftest import make_user
    from app.models.user import UserRole

    other = make_user(db, username="othercust", password="password123", role=UserRole.CUSTOMER)
    headers = auth_headers(client, customer.username, "password123")
    response = client.post(f"/api/users/{other.id}/balance", json={"amount": 999}, headers=headers)
    assert response.status_code == 403


def test_negative_amount_rejected(client: TestClient, customer: User, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(f"/api/users/{customer.id}/balance", json={"amount": -10}, headers=headers)
    assert response.status_code == 422


def test_zero_amount_rejected(client: TestClient, customer: User, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(f"/api/users/{customer.id}/balance", json={"amount": 0}, headers=headers)
    assert response.status_code == 422


def test_infinite_amount_rejected(client: TestClient, db: Session, customer: User, admin: User) -> None:
    # httpx's own `json=` convenience encoder refuses to serialize inf/nan at
    # all (stricter than Python's stdlib json module), so this is sent as a
    # raw body — which is exactly how a non-browser client (curl, requests,
    # a hand-crafted request) would actually deliver this payload.
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(
        f"/api/users/{customer.id}/balance", content='{"amount": Infinity}', headers={**headers, "Content-Type": "application/json"}
    )
    assert response.status_code == 422

    db.refresh(customer)
    assert float(customer.balance) == 100.0  # untouched


def test_nan_amount_rejected(client: TestClient, db: Session, customer: User, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(
        f"/api/users/{customer.id}/balance", content='{"amount": NaN}', headers={**headers, "Content-Type": "application/json"}
    )
    assert response.status_code == 422

    db.refresh(customer)
    assert float(customer.balance) == 100.0


def test_overflowing_amount_rejected(client: TestClient, db: Session, customer: User, admin: User) -> None:
    """A finite-looking exponent that overflows a double to +inf on parse —
    doesn't need the literal word Infinity to trigger the same bug."""
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(
        f"/api/users/{customer.id}/balance", content='{"amount": 1e400}', headers={**headers, "Content-Type": "application/json"}
    )
    assert response.status_code == 422

    db.refresh(customer)
    assert float(customer.balance) == 100.0


def test_absurdly_large_but_finite_amount_rejected(client: TestClient, customer: User, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(f"/api/users/{customer.id}/balance", json={"amount": 999_999_999}, headers=headers)
    assert response.status_code == 422


def test_description_too_long_rejected(client: TestClient, customer: User, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(
        f"/api/users/{customer.id}/balance", json={"amount": 10, "description": "x" * 501}, headers=headers
    )
    assert response.status_code == 422


def test_admin_can_subtract_balance_from_customer(client: TestClient, db: Session, customer: User, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(f"/api/users/{customer.id}/balance/subtract", json={"amount": 30, "description": "Correction"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["balance"] == 70.0
    assert body["total_spent"] == 30.0

    db.refresh(customer)
    assert float(customer.balance) == 70.0


def test_subtract_creates_adjustment_transaction(client: TestClient, customer: User, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    client.post(f"/api/users/{customer.id}/balance/subtract", json={"amount": 15, "description": "Penalty"}, headers=headers)

    response = client.get(f"/api/users/{customer.id}/balance", headers=headers)
    txn = response.json()["transactions"][0]
    assert txn["transaction_type"] == "adjustment"
    assert txn["amount"] == -15.0
    assert txn["description"] == "Penalty"
    assert txn["created_by_username"] == admin.username


def test_cannot_subtract_more_than_current_balance(client: TestClient, db: Session, customer: User, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(f"/api/users/{customer.id}/balance/subtract", json={"amount": 150}, headers=headers)
    assert response.status_code == 400

    db.refresh(customer)
    assert float(customer.balance) == 100.0  # untouched


def test_subtract_exactly_full_balance_allowed(client: TestClient, db: Session, customer: User, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(f"/api/users/{customer.id}/balance/subtract", json={"amount": 100}, headers=headers)
    assert response.status_code == 200
    assert response.json()["balance"] == 0.0


def test_customer_cannot_subtract_own_balance(client: TestClient, customer: User) -> None:
    headers = auth_headers(client, customer.username, "password123")
    response = client.post(f"/api/users/{customer.id}/balance/subtract", json={"amount": 10}, headers=headers)
    assert response.status_code == 403


def test_customer_cannot_subtract_from_another_user(client: TestClient, db: Session, customer: User) -> None:
    from app.models.user import UserRole
    from tests.conftest import make_user

    other = make_user(db, username="othercust2", password="password123", role=UserRole.CUSTOMER, balance=50)
    headers = auth_headers(client, customer.username, "password123")
    response = client.post(f"/api/users/{other.id}/balance/subtract", json={"amount": 10}, headers=headers)
    assert response.status_code == 403


def test_subtract_negative_amount_rejected(client: TestClient, customer: User, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(f"/api/users/{customer.id}/balance/subtract", json={"amount": -10}, headers=headers)
    assert response.status_code == 422


def test_subtract_unknown_user_404(client: TestClient, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(
        "/api/users/00000000-0000-0000-0000-000000000000/balance/subtract", json={"amount": 10}, headers=headers
    )
    assert response.status_code == 404


def test_new_user_defaults_to_usd_currency(client: TestClient, customer: User, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.get(f"/api/users/{customer.id}/balance", headers=headers)
    assert response.status_code == 200
    assert response.json()["currency"] == "USD"


def test_admin_can_switch_user_currency_to_iqd(client: TestClient, db: Session, customer: User, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.patch(f"/api/users/{customer.id}/currency", json={"currency": "IQD"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["currency"] == "IQD"

    db.refresh(customer)
    assert customer.currency.value == "IQD"


def test_switching_currency_does_not_convert_balance(client: TestClient, db: Session, customer: User, admin: User) -> None:
    """No exchange-rate math is ever applied — switching currency only
    relabels the existing raw balance number."""
    headers = auth_headers(client, admin.username, "password123")
    response = client.patch(f"/api/users/{customer.id}/currency", json={"currency": "IQD"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["balance"] == 100.0  # unchanged seed balance, just relabeled
    assert body["currency"] == "IQD"


def test_top_up_after_switching_to_iqd_uses_raw_amount(client: TestClient, db: Session, customer: User, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    client.patch(f"/api/users/{customer.id}/currency", json={"currency": "IQD"}, headers=headers)

    response = client.post(f"/api/users/{customer.id}/balance", json={"amount": 5000}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["balance"] == 5100.0  # 100 (seed) + 5000 raw, no conversion
    assert body["currency"] == "IQD"

    db.refresh(customer)
    assert float(customer.balance) == 5100.0


def test_transaction_currency_is_derived_from_account_not_stored_per_transaction(
    client: TestClient, db: Session, customer: User, admin: User
) -> None:
    """The per-transaction currency dropdown is gone — a transaction's
    `currency` field always mirrors its account's *current* currency (see
    BalanceTransaction.currency), so it moves when the account is switched
    rather than being fixed at the moment the transaction was created."""
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(f"/api/users/{customer.id}/balance", json={"amount": 25}, headers=headers)
    assert response.status_code == 200
    txn = response.json()["transactions"][0]
    assert txn["currency"] == "USD"

    client.patch(f"/api/users/{customer.id}/currency", json={"currency": "IQD"}, headers=headers)
    response = client.get(f"/api/users/{customer.id}/balance", headers=headers)
    txn = next(t for t in response.json()["transactions"] if t["id"] == txn["id"])
    assert txn["currency"] == "IQD"  # same transaction, relabeled after the account switch


def test_top_up_with_currency_field_in_body_is_ignored_not_error(client: TestClient, customer: User, admin: User) -> None:
    """The old per-transaction currency dropdown is removed; a stray
    `currency` field in the request body is simply ignored by Pydantic
    (extra fields aren't forbidden), not rejected."""
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(f"/api/users/{customer.id}/balance", json={"amount": 10, "currency": "IQD"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["currency"] == "USD"  # account currency unaffected by the stray field


def test_customer_cannot_switch_own_currency(client: TestClient, customer: User) -> None:
    headers = auth_headers(client, customer.username, "password123")
    response = client.patch(f"/api/users/{customer.id}/currency", json={"currency": "IQD"}, headers=headers)
    assert response.status_code == 403


def test_invalid_currency_value_rejected(client: TestClient, customer: User, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.patch(f"/api/users/{customer.id}/currency", json={"currency": "EUR"}, headers=headers)
    assert response.status_code == 422


def test_switch_currency_unknown_user_404(client: TestClient, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.patch(
        "/api/users/00000000-0000-0000-0000-000000000000/currency", json={"currency": "IQD"}, headers=headers
    )
    assert response.status_code == 404


def test_amount_not_multiple_of_quarter_rejected(client: TestClient, customer: User, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(f"/api/users/{customer.id}/balance", json={"amount": 10.10}, headers=headers)
    assert response.status_code == 422


def test_amount_that_is_quarter_increment_accepted(client: TestClient, customer: User, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(f"/api/users/{customer.id}/balance", json={"amount": 10.25}, headers=headers)
    assert response.status_code == 200
    assert response.json()["balance"] == 110.25
