import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.ai import AIRequestInputType, AIRequestStatus, AIRestockRequest
from app.models.cart import Cart, CartItem
from app.models.giveaway import Giveaway, GiveawayWinner
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.transaction import BalanceTransaction, TransactionType
from app.models.user import Region, User, UserRole
from tests.conftest import auth_headers, make_product, make_user


def _super_admin(db: Session) -> User:
    return make_user(db, username=f"super_{uuid.uuid4().hex[:8]}", password="password123", role=UserRole.SUPER_ADMIN, balance=100)


# ---------------------------------------------------------------------------
# Who may grant / revoke ADMIN
# ---------------------------------------------------------------------------


def test_customer_cannot_create_admin(client: TestClient, customer: User) -> None:
    headers = auth_headers(client, customer.username, "password123")
    response = client.post(
        "/api/users",
        json={"username": "esc1", "email": "esc1@example.com", "full_name": "Esc", "password": "password123", "role": "admin"},
        headers=headers,
    )
    assert response.status_code == 403


def test_customer_cannot_promote_themselves(client: TestClient, customer: User) -> None:
    headers = auth_headers(client, customer.username, "password123")
    response = client.patch(f"/api/users/{customer.id}", json={"role": "admin"}, headers=headers)
    assert response.status_code == 403


def test_admin_cannot_create_admin(client: TestClient, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(
        "/api/users",
        json={"username": "esc2", "email": "esc2@example.com", "full_name": "Esc", "password": "password123", "role": "admin"},
        headers=headers,
    )
    assert response.status_code == 403


def test_admin_can_still_create_a_customer(client: TestClient, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(
        "/api/users",
        json={"username": "cust_ok", "email": "cust_ok@example.com", "full_name": "Cust", "password": "password123", "role": "customer"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["role"] == "customer"


def test_admin_cannot_promote_user_to_admin(client: TestClient, admin: User, customer: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.patch(f"/api/users/{customer.id}", json={"role": "admin"}, headers=headers)
    assert response.status_code == 403


def test_admin_cannot_demote_another_admin(client: TestClient, db: Session, admin: User) -> None:
    other_admin = make_user(db, username="other_admin", password="password123", role=UserRole.ADMIN)
    headers = auth_headers(client, admin.username, "password123")
    response = client.patch(f"/api/users/{other_admin.id}", json={"role": "customer"}, headers=headers)
    assert response.status_code == 403


def test_nobody_can_assign_super_admin_role(client: TestClient, db: Session, customer: User) -> None:
    """Not even a Super Admin can hand the role out through the API — the
    bootstrap seed is the only source of it."""
    super_admin = _super_admin(db)
    headers = auth_headers(client, super_admin.username, "password123")
    response = client.patch(f"/api/users/{customer.id}", json={"role": "super_admin"}, headers=headers)
    assert response.status_code == 403

    db.refresh(customer)
    assert customer.role == UserRole.CUSTOMER


def test_super_admin_can_promote_customer_to_admin(client: TestClient, db: Session, customer: User) -> None:
    super_admin = _super_admin(db)
    headers = auth_headers(client, super_admin.username, "password123")
    response = client.patch(f"/api/users/{customer.id}", json={"role": "admin"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_super_admin_can_demote_admin_to_customer(client: TestClient, db: Session, admin: User) -> None:
    super_admin = _super_admin(db)
    headers = auth_headers(client, super_admin.username, "password123")
    response = client.patch(f"/api/users/{admin.id}", json={"role": "customer"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["role"] == "customer"


def test_super_admin_can_create_an_admin(client: TestClient, db: Session) -> None:
    super_admin = _super_admin(db)
    headers = auth_headers(client, super_admin.username, "password123")
    response = client.post(
        "/api/users",
        json={"username": "made_admin", "email": "made_admin@example.com", "full_name": "A", "password": "password123", "role": "admin"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["role"] == "admin"


# ---------------------------------------------------------------------------
# Super Admin account protection
# ---------------------------------------------------------------------------


def test_admin_cannot_modify_super_admin_account(client: TestClient, db: Session, admin: User) -> None:
    super_admin = _super_admin(db)
    headers = auth_headers(client, admin.username, "password123")
    response = client.patch(f"/api/users/{super_admin.id}", json={"is_active": False}, headers=headers)
    assert response.status_code == 403

    db.refresh(super_admin)
    assert super_admin.is_active is True


def test_admin_cannot_reset_super_admin_password(client: TestClient, db: Session, admin: User) -> None:
    super_admin = _super_admin(db)
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(f"/api/users/{super_admin.id}/password", json={"new_password": "hijacked123"}, headers=headers)
    assert response.status_code == 403


def test_super_admin_cannot_be_deactivated_even_by_themselves(client: TestClient, db: Session) -> None:
    """A deactivated account can't log in, so allowing this would strand the
    protected account outside the app."""
    super_admin = _super_admin(db)
    headers = auth_headers(client, super_admin.username, "password123")
    response = client.patch(f"/api/users/{super_admin.id}", json={"is_active": False}, headers=headers)
    assert response.status_code == 403

    db.refresh(super_admin)
    assert super_admin.is_active is True


def test_super_admin_account_cannot_be_permanently_deleted(client: TestClient, db: Session) -> None:
    super_admin = _super_admin(db)
    other_super = make_user(db, username="second_super", password="password123", role=UserRole.SUPER_ADMIN)
    headers = auth_headers(client, super_admin.username, "password123")
    response = client.post(
        f"/api/users/{other_super.id}/permanent-delete", json={"confirm_username": other_super.username}, headers=headers
    )
    assert response.status_code == 403

    assert db.query(User).filter(User.id == other_super.id).count() == 1


# ---------------------------------------------------------------------------
# Permanent deletion: authorization
# ---------------------------------------------------------------------------


def test_customer_cannot_permanently_delete(client: TestClient, db: Session, customer: User) -> None:
    victim = make_user(db, username="victim1", password="password123", role=UserRole.CUSTOMER)
    headers = auth_headers(client, customer.username, "password123")
    response = client.post(
        f"/api/users/{victim.id}/permanent-delete", json={"confirm_username": victim.username}, headers=headers
    )
    assert response.status_code == 403
    assert db.query(User).filter(User.id == victim.id).count() == 1


def test_admin_cannot_permanently_delete(client: TestClient, db: Session, admin: User) -> None:
    victim = make_user(db, username="victim2", password="password123", role=UserRole.CUSTOMER)
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(
        f"/api/users/{victim.id}/permanent-delete", json={"confirm_username": victim.username}, headers=headers
    )
    assert response.status_code == 403
    assert db.query(User).filter(User.id == victim.id).count() == 1


def test_unauthenticated_permanent_delete_is_rejected(client: TestClient, db: Session) -> None:
    victim = make_user(db, username="victim3", password="password123", role=UserRole.CUSTOMER)
    response = client.post(f"/api/users/{victim.id}/permanent-delete", json={"confirm_username": victim.username})
    assert response.status_code == 401
    assert db.query(User).filter(User.id == victim.id).count() == 1


def test_admin_cannot_delete_another_admin_with_the_plain_delete(client: TestClient, db: Session, admin: User) -> None:
    other_admin = make_user(db, username="other_admin2", password="password123", role=UserRole.ADMIN)
    headers = auth_headers(client, admin.username, "password123")
    response = client.delete(f"/api/users/{other_admin.id}", headers=headers)
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Permanent deletion: username confirmation
# ---------------------------------------------------------------------------


def test_permanent_delete_requires_exact_username(client: TestClient, db: Session) -> None:
    super_admin = _super_admin(db)
    victim = make_user(db, username="victim4", password="password123", role=UserRole.CUSTOMER)
    headers = auth_headers(client, super_admin.username, "password123")

    response = client.post(
        f"/api/users/{victim.id}/permanent-delete", json={"confirm_username": "victim4_wrong"}, headers=headers
    )
    assert response.status_code == 400
    assert db.query(User).filter(User.id == victim.id).count() == 1


def test_permanent_delete_confirmation_is_case_sensitive(client: TestClient, db: Session) -> None:
    super_admin = _super_admin(db)
    victim = make_user(db, username="victim5", password="password123", role=UserRole.CUSTOMER)
    headers = auth_headers(client, super_admin.username, "password123")

    response = client.post(
        f"/api/users/{victim.id}/permanent-delete", json={"confirm_username": "VICTIM5"}, headers=headers
    )
    assert response.status_code == 400
    assert db.query(User).filter(User.id == victim.id).count() == 1


def test_permanent_delete_rejects_missing_confirmation(client: TestClient, db: Session) -> None:
    super_admin = _super_admin(db)
    victim = make_user(db, username="victim6", password="password123", role=UserRole.CUSTOMER)
    headers = auth_headers(client, super_admin.username, "password123")

    response = client.post(f"/api/users/{victim.id}/permanent-delete", json={}, headers=headers)
    assert response.status_code == 422
    assert db.query(User).filter(User.id == victim.id).count() == 1


def test_super_admin_cannot_delete_their_own_account(client: TestClient, db: Session) -> None:
    super_admin = _super_admin(db)
    headers = auth_headers(client, super_admin.username, "password123")
    response = client.post(
        f"/api/users/{super_admin.id}/permanent-delete", json={"confirm_username": super_admin.username}, headers=headers
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Permanent deletion: what actually gets removed
# ---------------------------------------------------------------------------


def test_super_admin_permanently_deletes_user_and_all_owned_data(client: TestClient, db: Session) -> None:
    super_admin = _super_admin(db)
    victim = make_user(db, username="victim_full", password="password123", role=UserRole.CUSTOMER, balance=100_000)
    product = make_product(db, price=1_000, stock=10)

    # Give the victim a full footprint: an order (with items), a purchase
    # ledger row, a cart item, and a giveaway win.
    victim_headers = auth_headers(client, victim.username, "password123")
    client.post("/api/cart/items", json={"product_id": str(product.id), "quantity": 2}, headers=victim_headers)
    assert client.post("/api/orders/checkout", headers=victim_headers).status_code == 200
    client.post("/api/cart/items", json={"product_id": str(product.id), "quantity": 1}, headers=victim_headers)

    giveaway = Giveaway(scheduled_date=date(2026, 1, 4), product_id=product.id)
    db.add(giveaway)
    db.flush()
    db.add(GiveawayWinner(giveaway_id=giveaway.id, user_id=victim.id))
    db.commit()

    victim_id = victim.id
    order_ids = [o.id for o in db.query(Order).filter(Order.user_id == victim_id).all()]
    assert order_ids, "victim should have an order before deletion"

    headers = auth_headers(client, super_admin.username, "password123")
    response = client.post(
        f"/api/users/{victim_id}/permanent-delete", json={"confirm_username": "victim_full"}, headers=headers
    )
    assert response.status_code == 204, response.text

    assert db.query(User).filter(User.id == victim_id).count() == 0
    assert db.query(Order).filter(Order.user_id == victim_id).count() == 0
    assert db.query(OrderItem).filter(OrderItem.order_id.in_(order_ids)).count() == 0
    assert db.query(BalanceTransaction).filter(BalanceTransaction.user_id == victim_id).count() == 0
    assert db.query(Cart).filter(Cart.user_id == victim_id).count() == 0
    assert db.query(GiveawayWinner).filter(GiveawayWinner.user_id == victim_id).count() == 0

    # Shared/global data survives: the product and the giveaway itself remain.
    assert db.query(Product).filter(Product.id == product.id).count() == 1
    assert db.query(Giveaway).filter(Giveaway.id == giveaway.id).count() == 1


def test_permanent_delete_keeps_other_users_ledger_rows(client: TestClient, db: Session) -> None:
    """An admin's recharges live on *other* people's ledgers. Deleting the admin
    must keep those rows (blanking the attribution), not delete them."""
    super_admin = _super_admin(db)
    doomed_admin = make_user(db, username="doomed_admin", password="password123", role=UserRole.ADMIN)
    bystander = make_user(db, username="bystander", password="password123", role=UserRole.CUSTOMER)

    admin_headers = auth_headers(client, doomed_admin.username, "password123")
    resp = client.post(
        f"/api/users/{bystander.id}/balance", json={"amount": 5_000, "description": "topup"}, headers=admin_headers
    )
    assert resp.status_code == 200

    bystander_id = bystander.id
    before = db.query(BalanceTransaction).filter(BalanceTransaction.user_id == bystander_id).count()
    assert before == 1

    headers = auth_headers(client, super_admin.username, "password123")
    response = client.post(
        f"/api/users/{doomed_admin.id}/permanent-delete", json={"confirm_username": "doomed_admin"}, headers=headers
    )
    assert response.status_code == 204, response.text

    rows = db.query(BalanceTransaction).filter(BalanceTransaction.user_id == bystander_id).all()
    assert len(rows) == 1, "the bystander's ledger row must survive"
    assert rows[0].created_by_id is None, "attribution is blanked, the row is kept"

    db.refresh(bystander)
    assert bystander.balance_in(Region.NAJAF) == 5_000.0, "bystander's balance is untouched"


def test_permanent_delete_removes_ai_restock_history(client: TestClient, db: Session) -> None:
    super_admin = _super_admin(db)
    doomed_admin = make_user(db, username="ai_admin", password="password123", role=UserRole.ADMIN)
    db.add(
        AIRestockRequest(
            admin_id=doomed_admin.id,
            raw_input="add 10 cola",
            input_type=AIRequestInputType.TEXT,
            status=AIRequestStatus.PENDING,
        )
    )
    db.commit()
    admin_id = doomed_admin.id
    assert db.query(AIRestockRequest).filter(AIRestockRequest.admin_id == admin_id).count() == 1

    headers = auth_headers(client, super_admin.username, "password123")
    response = client.post(
        f"/api/users/{admin_id}/permanent-delete", json={"confirm_username": "ai_admin"}, headers=headers
    )
    assert response.status_code == 204, response.text
    assert db.query(AIRestockRequest).filter(AIRestockRequest.admin_id == admin_id).count() == 0


def test_super_admin_can_permanently_delete_an_admin(client: TestClient, db: Session) -> None:
    super_admin = _super_admin(db)
    doomed = make_user(db, username="doomed_admin2", password="password123", role=UserRole.ADMIN)
    headers = auth_headers(client, super_admin.username, "password123")

    response = client.post(
        f"/api/users/{doomed.id}/permanent-delete", json={"confirm_username": "doomed_admin2"}, headers=headers
    )
    assert response.status_code == 204, response.text
    assert db.query(User).filter(User.username == "doomed_admin2").count() == 0


def test_failed_permanent_delete_rolls_everything_back(client: TestClient, db: Session, monkeypatch) -> None:
    """If any step of the purge blows up, the account and all of its data must
    still be there — no half-deleted state."""
    super_admin = _super_admin(db)
    victim = make_user(db, username="victim_rb", password="password123", role=UserRole.CUSTOMER, balance=100_000)
    product = make_product(db, price=1_000, stock=10)

    victim_headers = auth_headers(client, victim.username, "password123")
    client.post("/api/cart/items", json={"product_id": str(product.id), "quantity": 1}, headers=victim_headers)
    assert client.post("/api/orders/checkout", headers=victim_headers).status_code == 200

    victim_id = victim.id
    orders_before = db.query(Order).filter(Order.user_id == victim_id).count()
    txns_before = db.query(BalanceTransaction).filter(BalanceTransaction.user_id == victim_id).count()
    assert orders_before == 1 and txns_before == 1

    # Blow up on the final commit, i.e. after every row has already been
    # deleted inside the transaction — the rollback has to undo all of it.
    # Patched on this session instance only, so nothing else is affected.
    def boom() -> None:
        raise RuntimeError("simulated failure mid-delete")

    monkeypatch.setattr(db, "commit", boom)

    headers = auth_headers(client, super_admin.username, "password123")
    try:
        client.post(
            f"/api/users/{victim_id}/permanent-delete", json={"confirm_username": "victim_rb"}, headers=headers
        )
    except RuntimeError:
        pass
    monkeypatch.undo()

    assert db.query(User).filter(User.id == victim_id).count() == 1, "account must survive a failed purge"
    assert db.query(Order).filter(Order.user_id == victim_id).count() == orders_before
    assert db.query(BalanceTransaction).filter(BalanceTransaction.user_id == victim_id).count() == txns_before


def test_existing_admin_functionality_still_works(client: TestClient, db: Session, admin: User, customer: User) -> None:
    """Regression guard: the ordinary admin surfaces keep working unchanged."""
    headers = auth_headers(client, admin.username, "password123")

    assert client.get("/api/users", headers=headers).status_code == 200
    assert client.get(f"/api/users/{customer.id}", headers=headers).status_code == 200
    assert client.patch(f"/api/users/{customer.id}", json={"full_name": "Renamed"}, headers=headers).status_code == 200
    assert (
        client.post(f"/api/users/{customer.id}/balance", json={"amount": 1_000}, headers=headers).status_code == 200
    )
    assert client.post(f"/api/users/{customer.id}/password", json={"new_password": "newpass123"}, headers=headers).status_code == 200
