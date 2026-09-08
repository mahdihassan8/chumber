import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.transfer import Transfer
from app.models.user import Region, User, UserRole
from tests.conftest import auth_headers, make_user


def _user(db: Session, *, region: Region = Region.NAJAF, balance: float = 100_000, role: UserRole = UserRole.CUSTOMER) -> User:
    return make_user(db, username=f"tr_{uuid.uuid4().hex[:8]}", password="password123", role=role, region=region, balance=balance)


# ---------------------------------------------------------------------------
# Eligible recipients list
# ---------------------------------------------------------------------------


def test_recipient_list_excludes_self(client: TestClient, db: Session) -> None:
    me = _user(db)
    headers = auth_headers(client, me.username, "password123")
    response = client.get("/api/transfers/recipients", headers=headers)
    assert response.status_code == 200
    assert me.username not in [r["username"] for r in response.json()]


def test_recipient_list_only_includes_same_region(client: TestClient, db: Session) -> None:
    me = _user(db, region=Region.NAJAF)
    same_region = _user(db, region=Region.NAJAF)
    other_region = _user(db, region=Region.BAGHDAD)
    headers = auth_headers(client, me.username, "password123")

    usernames = [r["username"] for r in client.get("/api/transfers/recipients", headers=headers).json()]
    assert same_region.username in usernames
    assert other_region.username not in usernames


def test_recipient_list_shows_name_username_and_avatar(client: TestClient, db: Session) -> None:
    me = _user(db)
    target = _user(db)
    headers = auth_headers(client, me.username, "password123")

    response = client.get("/api/transfers/recipients", headers=headers)
    row = next(r for r in response.json() if r["id"] == str(target.id))
    assert row["full_name"] == target.full_name
    assert row["username"] == target.username
    assert "avatar_url" in row


def test_recipient_list_excludes_inactive_users(client: TestClient, db: Session) -> None:
    me = _user(db)
    inactive = _user(db)
    inactive.is_active = False
    db.commit()
    headers = auth_headers(client, me.username, "password123")

    usernames = [r["username"] for r in client.get("/api/transfers/recipients", headers=headers).json()]
    assert inactive.username not in usernames


# ---------------------------------------------------------------------------
# Sending a transfer
# ---------------------------------------------------------------------------


def test_successful_transfer_moves_money_and_returns_the_record(client: TestClient, db: Session) -> None:
    sender = _user(db, balance=10_000)
    recipient = _user(db, balance=0)
    headers = auth_headers(client, sender.username, "password123")

    response = client.post("/api/transfers", json={"recipient_id": str(recipient.id), "amount": 2_500, "note": "for lunch"}, headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert body["amount"] == 2_500.0
    assert body["note"] == "for lunch"
    assert body["status"] == "completed"
    assert body["sender_username"] == sender.username
    assert body["recipient_username"] == recipient.username

    sender_balance = client.get("/api/balance", headers=headers).json()["balance"]
    recipient_balance = client.get("/api/balance", headers=auth_headers(client, recipient.username, "password123")).json()["balance"]
    assert sender_balance == 7_500.0
    assert recipient_balance == 2_500.0


def test_transfer_note_is_optional(client: TestClient, db: Session) -> None:
    sender = _user(db, balance=10_000)
    recipient = _user(db, balance=0)
    headers = auth_headers(client, sender.username, "password123")

    response = client.post("/api/transfers", json={"recipient_id": str(recipient.id), "amount": 1_000}, headers=headers)
    assert response.status_code == 201
    assert response.json()["note"] is None


def test_transfer_amount_must_be_greater_than_zero(client: TestClient, db: Session) -> None:
    sender = _user(db, balance=10_000)
    recipient = _user(db, balance=0)
    headers = auth_headers(client, sender.username, "password123")

    response = client.post("/api/transfers", json={"recipient_id": str(recipient.id), "amount": 0}, headers=headers)
    assert response.status_code == 422

    response = client.post("/api/transfers", json={"recipient_id": str(recipient.id), "amount": -500}, headers=headers)
    assert response.status_code == 422


def test_cannot_transfer_more_than_available_balance(client: TestClient, db: Session) -> None:
    sender = _user(db, balance=1_000)
    recipient = _user(db, balance=0)
    headers = auth_headers(client, sender.username, "password123")

    response = client.post("/api/transfers", json={"recipient_id": str(recipient.id), "amount": 5_000}, headers=headers)
    assert response.status_code == 400
    assert "balance" in response.json()["detail"].lower()

    # Nothing was moved.
    assert client.get("/api/balance", headers=headers).json()["balance"] == 1_000.0


def test_cannot_transfer_to_self(client: TestClient, db: Session) -> None:
    me = _user(db, balance=10_000)
    headers = auth_headers(client, me.username, "password123")

    response = client.post("/api/transfers", json={"recipient_id": str(me.id), "amount": 500}, headers=headers)
    assert response.status_code == 400
    assert "yourself" in response.json()["detail"].lower()
    assert client.get("/api/balance", headers=headers).json()["balance"] == 10_000.0


def test_transfer_to_nonexistent_recipient_is_rejected(client: TestClient, db: Session) -> None:
    sender = _user(db, balance=10_000)
    headers = auth_headers(client, sender.username, "password123")

    response = client.post("/api/transfers", json={"recipient_id": str(uuid.uuid4()), "amount": 500}, headers=headers)
    assert response.status_code == 404


def test_transfer_to_inactive_recipient_is_rejected(client: TestClient, db: Session) -> None:
    sender = _user(db, balance=10_000)
    recipient = _user(db, balance=0)
    recipient.is_active = False
    db.commit()
    headers = auth_headers(client, sender.username, "password123")

    response = client.post("/api/transfers", json={"recipient_id": str(recipient.id), "amount": 500}, headers=headers)
    assert response.status_code == 404
    assert client.get("/api/balance", headers=headers).json()["balance"] == 10_000.0


def test_cross_region_transfer_is_rejected(client: TestClient, db: Session) -> None:
    sender = _user(db, region=Region.NAJAF, balance=10_000)
    recipient = _user(db, region=Region.BAGHDAD, balance=0)
    headers = auth_headers(client, sender.username, "password123")

    response = client.post("/api/transfers", json={"recipient_id": str(recipient.id), "amount": 500}, headers={**headers, "X-Region": "najaf"})
    assert response.status_code == 404

    # Untouched on both sides.
    assert client.get("/api/balance", headers={**headers, "X-Region": "najaf"}).json()["balance"] == 10_000.0
    bag_headers = auth_headers(client, recipient.username, "password123")
    assert client.get("/api/balance", headers={**bag_headers, "X-Region": "baghdad"}).json()["balance"] == 0.0


def test_customer_cannot_forge_a_larger_balance_than_they_actually_have(client: TestClient, db: Session) -> None:
    """The backend must recompute everything itself -- a request claiming an
    amount the sender doesn't actually have must fail regardless of what the
    frontend displayed."""
    sender = _user(db, balance=100)
    recipient = _user(db, balance=0)
    headers = auth_headers(client, sender.username, "password123")

    response = client.post("/api/transfers", json={"recipient_id": str(recipient.id), "amount": 250_000}, headers=headers)
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Atomicity: rollback leaves neither side touched
# ---------------------------------------------------------------------------


def test_failed_transfer_is_fully_rolled_back(client: TestClient, db: Session) -> None:
    """An insufficient-balance failure must not partially apply -- neither
    wallet moves and no history row is written."""
    sender = _user(db, balance=1_000)
    recipient = _user(db, balance=500)
    headers = auth_headers(client, sender.username, "password123")

    response = client.post("/api/transfers", json={"recipient_id": str(recipient.id), "amount": 50_000}, headers=headers)
    assert response.status_code == 400

    assert client.get("/api/balance", headers=headers).json()["balance"] == 1_000.0
    recipient_headers = auth_headers(client, recipient.username, "password123")
    assert client.get("/api/balance", headers=recipient_headers).json()["balance"] == 500.0

    history = client.get("/api/transfers/history", headers=headers).json()
    assert history == []


# ---------------------------------------------------------------------------
# Persistence + history
# ---------------------------------------------------------------------------


def test_transfer_persists_and_appears_in_both_histories(client: TestClient, db: Session) -> None:
    sender = _user(db, balance=10_000)
    recipient = _user(db, balance=0)
    headers = auth_headers(client, sender.username, "password123")
    recipient_headers = auth_headers(client, recipient.username, "password123")

    client.post("/api/transfers", json={"recipient_id": str(recipient.id), "amount": 3_000, "note": "gift"}, headers=headers)

    sender_history = client.get("/api/transfers/history", headers=headers).json()
    recipient_history = client.get("/api/transfers/history", headers=recipient_headers).json()

    assert len(sender_history) == 1
    assert sender_history[0]["amount"] == 3_000.0
    assert sender_history[0]["sender_id"] == str(sender.id)
    assert sender_history[0]["recipient_id"] == str(recipient.id)

    assert len(recipient_history) == 1
    assert recipient_history[0]["id"] == sender_history[0]["id"]


def test_transfer_history_only_shows_own_transfers(client: TestClient, db: Session) -> None:
    sender = _user(db, balance=10_000)
    recipient = _user(db, balance=0)
    bystander = _user(db, balance=0)
    headers = auth_headers(client, sender.username, "password123")

    client.post("/api/transfers", json={"recipient_id": str(recipient.id), "amount": 1_000}, headers=headers)

    bystander_history = client.get("/api/transfers/history", headers=auth_headers(client, bystander.username, "password123")).json()
    assert bystander_history == []


def test_multiple_transfers_accumulate_correctly(client: TestClient, db: Session) -> None:
    sender = _user(db, balance=10_000)
    recipient = _user(db, balance=0)
    headers = auth_headers(client, sender.username, "password123")

    client.post("/api/transfers", json={"recipient_id": str(recipient.id), "amount": 1_000}, headers=headers)
    client.post("/api/transfers", json={"recipient_id": str(recipient.id), "amount": 2_000}, headers=headers)

    assert client.get("/api/balance", headers=headers).json()["balance"] == 7_000.0
    history = client.get("/api/transfers/history", headers=headers).json()
    assert len(history) == 2


# ---------------------------------------------------------------------------
# Total User Money must be unaffected by a transfer -- the money only moves
# between users, it is never created or destroyed.
# ---------------------------------------------------------------------------


def test_transfer_does_not_change_total_user_money(client: TestClient, db: Session) -> None:
    from app.models.user import UserRole as _Role  # local import to avoid unused-at-module-level lint noise

    admin = make_user(db, username=f"tr_admin_{uuid.uuid4().hex[:6]}", password="password123", role=_Role.ADMIN, region=Region.NAJAF)
    sender = _user(db, balance=10_000)
    recipient = _user(db, balance=0)
    headers = auth_headers(client, sender.username, "password123")
    admin_headers = auth_headers(client, admin.username, "password123")

    before = client.get("/api/admin/overview", headers=admin_headers).json()["total_user_balance"]
    client.post("/api/transfers", json={"recipient_id": str(recipient.id), "amount": 4_000}, headers=headers)
    after = client.get("/api/admin/overview", headers=admin_headers).json()["total_user_balance"]

    assert after == before


# ---------------------------------------------------------------------------
# Admin transfer history view
# ---------------------------------------------------------------------------


def test_admin_can_view_transfer_history(client: TestClient, db: Session) -> None:
    admin = make_user(db, username=f"tr_admin2_{uuid.uuid4().hex[:6]}", password="password123", role=UserRole.ADMIN, region=Region.NAJAF)
    sender = _user(db, balance=10_000)
    recipient = _user(db, balance=0)
    headers = auth_headers(client, sender.username, "password123")
    admin_headers = auth_headers(client, admin.username, "password123")

    client.post("/api/transfers", json={"recipient_id": str(recipient.id), "amount": 1_500, "note": "test"}, headers=headers)

    response = client.get("/api/admin/transfers", headers=admin_headers)
    assert response.status_code == 200
    rows = response.json()
    assert any(r["amount"] == 1_500.0 and r["note"] == "test" for r in rows)


def test_customer_cannot_view_admin_transfer_history(client: TestClient, db: Session) -> None:
    customer = _user(db)
    headers = auth_headers(client, customer.username, "password123")
    assert client.get("/api/admin/transfers", headers=headers).status_code == 403


def test_admin_transfer_history_is_region_scoped(client: TestClient, db: Session) -> None:
    naj_admin = make_user(db, username=f"tr_naj_admin_{uuid.uuid4().hex[:6]}", password="password123", role=UserRole.ADMIN, region=Region.NAJAF)
    bag_sender = _user(db, region=Region.BAGHDAD, balance=10_000)
    bag_recipient = _user(db, region=Region.BAGHDAD, balance=0)
    bag_headers = auth_headers(client, bag_sender.username, "password123")

    client.post("/api/transfers", json={"recipient_id": str(bag_recipient.id), "amount": 900}, headers={**bag_headers, "X-Region": "baghdad"})

    naj_admin_headers = auth_headers(client, naj_admin.username, "password123")
    rows = client.get("/api/admin/transfers", headers=naj_admin_headers).json()
    assert all(r["amount"] != 900.0 for r in rows)


# ---------------------------------------------------------------------------
# Permanent account deletion: a transfer is shared history between two
# people, so it must survive one side being deleted -- blanked, not removed.
# ---------------------------------------------------------------------------


def test_permanent_delete_blanks_transfer_party_but_keeps_the_row(client: TestClient, db: Session) -> None:
    super_admin = make_user(db, username=f"tr_super_{uuid.uuid4().hex[:6]}", password="password123", role=UserRole.SUPER_ADMIN, balance=100)
    doomed = _user(db, balance=10_000)
    bystander = _user(db, balance=0)
    headers = auth_headers(client, doomed.username, "password123")

    transfer_resp = client.post("/api/transfers", json={"recipient_id": str(bystander.id), "amount": 1_000}, headers=headers)
    transfer_id = uuid.UUID(transfer_resp.json()["id"])

    super_headers = auth_headers(client, super_admin.username, "password123")
    response = client.post(f"/api/users/{doomed.id}/permanent-delete", json={"confirm_username": doomed.username}, headers=super_headers)
    assert response.status_code == 204, response.text

    row = db.query(Transfer).filter(Transfer.id == transfer_id).one()
    assert row.sender_id is None, "the sender reference is blanked, not the row deleted"
    assert row.recipient_id == bystander.id, "the other party's side of the record is untouched"
    assert row.amount == 1_000.0

    # The bystander's history still shows the transfer happened.
    bystander_history = client.get("/api/transfers/history", headers=auth_headers(client, bystander.username, "password123")).json()
    assert len(bystander_history) == 1
    assert bystander_history[0]["sender_id"] is None
