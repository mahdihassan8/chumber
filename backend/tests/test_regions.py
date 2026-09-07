import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.reward import WeeklyReward
from app.models.transaction import BalanceTransaction, TransactionType
from app.models.user import Region, User, UserRole
from app.services import reward_service
from tests.conftest import auth_headers, make_product, make_user

BAGHDAD_TZ = ZoneInfo("Asia/Baghdad")
NAJAF = {"X-Region": "najaf"}
BAGHDAD = {"X-Region": "baghdad"}


def _u(
    db: Session,
    name: str,
    *,
    role: UserRole = UserRole.CUSTOMER,
    region: Region | None = Region.NAJAF,
    regions: list[Region] | None = None,
    balance: float = 0,
) -> User:
    return make_user(
        db,
        username=f"{name}_{uuid.uuid4().hex[:6]}",
        password="password123",
        role=role,
        region=region,
        regions=regions,
        balance=balance,
    )


def _h(client: TestClient, user: User, region_header: dict[str, str] | None = None) -> dict[str, str]:
    headers = auth_headers(client, user.username, "password123")
    return {**headers, **(region_header or {})}


# ---------------------------------------------------------------------------
# Single-region isolation
# ---------------------------------------------------------------------------


def test_najaf_only_user_sees_only_najaf(client: TestClient, db: Session) -> None:
    najafi = _u(db, "naj", region=Region.NAJAF)
    make_product(db, name="Najaf Sprite", region=Region.NAJAF)
    make_product(db, name="Baghdad Pepsi", region=Region.BAGHDAD)

    names = [p["name"] for p in client.get("/api/products", headers=_h(client, najafi)).json()]
    assert names == ["Najaf Sprite"]


def test_baghdad_only_user_sees_only_baghdad(client: TestClient, db: Session) -> None:
    baghdadi = _u(db, "bag", region=Region.BAGHDAD)
    make_product(db, name="Najaf Sprite", region=Region.NAJAF)
    make_product(db, name="Baghdad Pepsi", region=Region.BAGHDAD)

    names = [p["name"] for p in client.get("/api/products", headers=_h(client, baghdadi)).json()]
    assert names == ["Baghdad Pepsi"]


def test_user_cannot_request_a_region_they_do_not_hold(client: TestClient, db: Session) -> None:
    najafi = _u(db, "naj", region=Region.NAJAF)
    resp = client.get("/api/products", headers=_h(client, najafi, BAGHDAD))
    assert resp.status_code == 403


def test_cross_region_product_by_id_is_404(client: TestClient, db: Session) -> None:
    najafi = _u(db, "naj", region=Region.NAJAF)
    baghdad_product = make_product(db, name="Baghdad Pepsi", region=Region.BAGHDAD)
    assert client.get(f"/api/products/{baghdad_product.id}", headers=_h(client, najafi)).status_code == 404


def test_cannot_add_cross_region_product_to_cart(client: TestClient, db: Session) -> None:
    najafi = _u(db, "naj", region=Region.NAJAF, balance=100_000)
    baghdad_product = make_product(db, name="Baghdad Pepsi", region=Region.BAGHDAD)
    resp = client.post(
        "/api/cart/items", json={"product_id": str(baghdad_product.id), "quantity": 1}, headers=_h(client, najafi)
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Dual-region users: separate wallets, separate history
# ---------------------------------------------------------------------------


def test_dual_region_user_has_two_independent_balances(client: TestClient, db: Session) -> None:
    """The headline rule: never show a combined total."""
    ahmed = _u(db, "ahmed", regions=[Region.NAJAF, Region.BAGHDAD])
    boss = _u(db, "boss", role=UserRole.SUPER_ADMIN)
    boss_h = auth_headers(client, boss.username, "password123")

    client.post(f"/api/users/{ahmed.id}/balance", json={"amount": 100_000}, headers={**boss_h, **NAJAF})
    client.post(f"/api/users/{ahmed.id}/balance", json={"amount": 25_000}, headers={**boss_h, **BAGHDAD})

    najaf_view = client.get("/api/balance", headers=_h(client, ahmed, NAJAF)).json()
    baghdad_view = client.get("/api/balance", headers=_h(client, ahmed, BAGHDAD)).json()

    assert najaf_view["balance"] == 100_000.0
    assert baghdad_view["balance"] == 25_000.0
    assert najaf_view["balance"] + baghdad_view["balance"] == 125_000.0, "sanity: the two wallets do add up..."
    for view in (najaf_view, baghdad_view):
        assert view["balance"] != 125_000.0, "...but neither view may ever show the combined total"


def test_dual_region_transactions_never_cross(client: TestClient, db: Session) -> None:
    ahmed = _u(db, "ahmed", regions=[Region.NAJAF, Region.BAGHDAD])
    boss = _u(db, "boss", role=UserRole.SUPER_ADMIN)
    boss_h = auth_headers(client, boss.username, "password123")

    client.post(f"/api/users/{ahmed.id}/balance", json={"amount": 1_000, "description": "najaf topup"}, headers={**boss_h, **NAJAF})
    client.post(f"/api/users/{ahmed.id}/balance", json={"amount": 2_000, "description": "baghdad topup"}, headers={**boss_h, **BAGHDAD})

    najaf_desc = [t["description"] for t in client.get("/api/balance", headers=_h(client, ahmed, NAJAF)).json()["transactions"]]
    baghdad_desc = [t["description"] for t in client.get("/api/balance", headers=_h(client, ahmed, BAGHDAD)).json()["transactions"]]

    assert "najaf topup" in najaf_desc and "baghdad topup" not in najaf_desc
    assert "baghdad topup" in baghdad_desc and "najaf topup" not in baghdad_desc


def test_dual_region_orders_stay_in_the_region_they_were_placed_in(client: TestClient, db: Session) -> None:
    ahmed = _u(db, "ahmed", regions=[Region.NAJAF, Region.BAGHDAD], balance=100_000)
    boss = _u(db, "boss", role=UserRole.SUPER_ADMIN)
    boss_h = auth_headers(client, boss.username, "password123")
    client.post(f"/api/users/{ahmed.id}/balance", json={"amount": 50_000}, headers={**boss_h, **BAGHDAD})

    najaf_product = make_product(db, name="Najaf Sprite", price=1_000, region=Region.NAJAF)
    baghdad_product = make_product(db, name="Baghdad Pepsi", price=2_000, region=Region.BAGHDAD)

    client.post("/api/cart/items", json={"product_id": str(najaf_product.id), "quantity": 1}, headers=_h(client, ahmed, NAJAF))
    assert client.post("/api/orders/checkout", headers=_h(client, ahmed, NAJAF)).status_code == 200
    client.post("/api/cart/items", json={"product_id": str(baghdad_product.id), "quantity": 1}, headers=_h(client, ahmed, BAGHDAD))
    assert client.post("/api/orders/checkout", headers=_h(client, ahmed, BAGHDAD)).status_code == 200

    najaf_orders = client.get("/api/users/me/orders", headers=_h(client, ahmed, NAJAF)).json()
    baghdad_orders = client.get("/api/users/me/orders", headers=_h(client, ahmed, BAGHDAD)).json()

    assert [o["items"][0]["product_name"] for o in najaf_orders] == ["Najaf Sprite"]
    assert [o["items"][0]["product_name"] for o in baghdad_orders] == ["Baghdad Pepsi"]


def test_checkout_spends_only_the_current_region_wallet(client: TestClient, db: Session) -> None:
    ahmed = _u(db, "ahmed", regions=[Region.NAJAF, Region.BAGHDAD], balance=100_000)  # Najaf wallet
    product = make_product(db, name="Najaf Sprite", price=10_000, region=Region.NAJAF)

    client.post("/api/cart/items", json={"product_id": str(product.id), "quantity": 1}, headers=_h(client, ahmed, NAJAF))
    resp = client.post("/api/orders/checkout", headers=_h(client, ahmed, NAJAF))
    assert resp.status_code == 200
    assert resp.json()["new_balance"] == 90_000.0

    db.refresh(ahmed)
    assert ahmed.balance_in(Region.NAJAF) == 90_000.0
    assert ahmed.balance_in(Region.BAGHDAD) == 0.0, "the Baghdad wallet must be untouched"


def test_granting_a_region_does_not_move_existing_money_or_history(client: TestClient, db: Session) -> None:
    najafi = _u(db, "naj", region=Region.NAJAF, balance=40_000)
    boss = _u(db, "boss", role=UserRole.SUPER_ADMIN)
    boss_h = auth_headers(client, boss.username, "password123")

    resp = client.put(f"/api/users/{najafi.id}/regions", json={"regions": ["najaf", "baghdad"]}, headers=boss_h)
    assert resp.status_code == 200
    assert set(resp.json()["regions"]) == {"najaf", "baghdad"}

    db.refresh(najafi)
    assert najafi.balance_in(Region.NAJAF) == 40_000.0, "existing Najaf money stays put"
    assert najafi.balance_in(Region.BAGHDAD) == 0.0, "the new region starts empty"


def test_revoking_a_region_leaves_its_history_intact(client: TestClient, db: Session) -> None:
    ahmed = _u(db, "ahmed", regions=[Region.NAJAF, Region.BAGHDAD], balance=30_000)
    boss = _u(db, "boss", role=UserRole.SUPER_ADMIN)
    boss_h = auth_headers(client, boss.username, "password123")
    client.post(f"/api/users/{ahmed.id}/balance", json={"amount": 7_000}, headers={**boss_h, **BAGHDAD})

    assert client.put(f"/api/users/{ahmed.id}/regions", json={"regions": ["najaf"]}, headers=boss_h).status_code == 200

    # The Baghdad ledger rows survive even though access is gone.
    baghdad_txns = (
        db.query(BalanceTransaction)
        .filter(BalanceTransaction.user_id == ahmed.id, BalanceTransaction.region == Region.BAGHDAD)
        .count()
    )
    assert baghdad_txns == 1
    db.refresh(ahmed)
    assert ahmed.balance_in(Region.NAJAF) == 30_000.0


# ---------------------------------------------------------------------------
# Region membership authorization
# ---------------------------------------------------------------------------


def test_only_super_admin_can_change_region_membership(client: TestClient, db: Session) -> None:
    admin = _u(db, "naj_admin", role=UserRole.ADMIN, region=Region.NAJAF)
    cust = _u(db, "naj_cust", region=Region.NAJAF)

    assert client.put(f"/api/users/{cust.id}/regions", json={"regions": ["baghdad"]}, headers=_h(client, admin)).status_code == 403
    assert client.put(f"/api/users/{cust.id}/regions", json={"regions": ["baghdad"]}, headers=_h(client, cust)).status_code == 403

    db.refresh(cust)
    assert cust.regions == [Region.NAJAF]


def test_admin_must_belong_to_exactly_one_region(client: TestClient, db: Session) -> None:
    admin = _u(db, "naj_admin", role=UserRole.ADMIN, region=Region.NAJAF)
    boss = _u(db, "boss", role=UserRole.SUPER_ADMIN)
    resp = client.put(
        f"/api/users/{admin.id}/regions", json={"regions": ["najaf", "baghdad"]}, headers=_h(client, boss)
    )
    assert resp.status_code == 400


def test_admin_created_user_lands_in_the_admins_region(client: TestClient, db: Session) -> None:
    bag_admin = _u(db, "bag_admin", role=UserRole.ADMIN, region=Region.BAGHDAD)
    resp = client.post(
        "/api/users",
        json={"username": "new_one", "email": "new_one@ex.com", "full_name": "N", "password": "password123", "role": "customer"},
        headers=_h(client, bag_admin),
    )
    assert resp.status_code == 201
    assert resp.json()["regions"] == ["baghdad"]


def test_admin_created_product_lands_in_the_admins_region(client: TestClient, db: Session) -> None:
    bag_admin = _u(db, "bag_admin", role=UserRole.ADMIN, region=Region.BAGHDAD)
    resp = client.post(
        "/api/products",
        json={"name": "Sneaky", "price": 1_000, "stock_quantity": 5, "region": "najaf"},
        headers=_h(client, bag_admin),
    )
    assert resp.status_code == 201
    assert resp.json()["region"] == "baghdad", "the body's region claim must be ignored"


# ---------------------------------------------------------------------------
# Regional admins
# ---------------------------------------------------------------------------


def test_regional_admin_cannot_reach_the_other_region(client: TestClient, db: Session) -> None:
    naj_admin = _u(db, "naj_admin", role=UserRole.ADMIN, region=Region.NAJAF)
    bag_cust = _u(db, "bag_cust", region=Region.BAGHDAD, balance=50_000)
    bag_product = make_product(db, name="Baghdad Pepsi", region=Region.BAGHDAD)
    h = _h(client, naj_admin)

    assert client.get(f"/api/users/{bag_cust.id}", headers=h).status_code == 404
    assert client.get(f"/api/users/{bag_cust.id}/balance", headers=h).status_code == 404
    assert client.post(f"/api/users/{bag_cust.id}/balance", json={"amount": 1_000}, headers=h).status_code == 404
    assert client.patch(f"/api/products/{bag_product.id}", json={"price": 1}, headers=h).status_code == 404

    usernames = [u["username"] for u in client.get("/api/users", headers=h).json()]
    assert bag_cust.username not in usernames


def test_super_admin_can_scope_the_dashboard_or_see_all(client: TestClient, db: Session) -> None:
    boss = _u(db, "boss", role=UserRole.SUPER_ADMIN)
    _u(db, "naj_cust", region=Region.NAJAF)
    _u(db, "bag_cust", region=Region.BAGHDAD)
    make_product(db, name="Najaf Sprite", region=Region.NAJAF)
    make_product(db, name="Baghdad Pepsi", region=Region.BAGHDAD)
    h = auth_headers(client, boss.username, "password123")

    all_products = [p["name"] for p in client.get("/api/products", headers={**h, "X-Region": "all"}).json()]
    assert "Najaf Sprite" in all_products and "Baghdad Pepsi" in all_products

    najaf_users = [u["username"] for u in client.get("/api/users", headers={**h, **NAJAF}).json()]
    assert any("naj_cust" in u for u in najaf_users)
    assert not any("bag_cust" in u for u in najaf_users)


# ---------------------------------------------------------------------------
# Najaf giveaway: dual-region users get exactly one entry
# ---------------------------------------------------------------------------


def test_najaf_giveaway_excludes_baghdad_only_users(client: TestClient, db: Session) -> None:
    from app.services import giveaway_service

    najafis = [_u(db, f"naj{i}", region=Region.NAJAF) for i in range(3)]
    baghdadi = _u(db, "bag_only", region=Region.BAGHDAD)
    make_product(db, name="Prize", price=1_000, region=Region.NAJAF)

    eligible = giveaway_service._eligible_najaf_customers(db)
    ids = {u.id for u in eligible}
    assert {u.id for u in najafis} <= ids
    assert baghdadi.id not in ids


def test_dual_region_user_gets_exactly_one_najaf_entry(client: TestClient, db: Session) -> None:
    from app.services import giveaway_service

    dual = _u(db, "dual", regions=[Region.NAJAF, Region.BAGHDAD])
    eligible = giveaway_service._eligible_najaf_customers(db)
    assert [u.id for u in eligible].count(dual.id) == 1, "membership of both regions must not double an entry"


def test_najaf_user_and_admin_both_eligible_for_giveaway(client: TestClient, db: Session) -> None:
    """A regional Admin is eligible for their own region's giveaway, same as
    a Customer — only Super Admin is categorically excluded (see below)."""
    from app.services import giveaway_service

    naj_user = _u(db, "naj_user_gv", region=Region.NAJAF)
    naj_admin = _u(db, "naj_admin_gv", role=UserRole.ADMIN, region=Region.NAJAF)
    eligible_ids = {u.id for u in giveaway_service._eligible_najaf_customers(db)}
    assert naj_user.id in eligible_ids
    assert naj_admin.id in eligible_ids


def test_super_admin_never_eligible_for_giveaway(client: TestClient, db: Session) -> None:
    from app.services import giveaway_service

    boss = _u(db, "boss_gv", role=UserRole.SUPER_ADMIN, region=Region.NAJAF)
    eligible_ids = {u.id for u in giveaway_service._eligible_najaf_customers(db)}
    assert boss.id not in eligible_ids


def test_dual_region_admin_gets_exactly_one_giveaway_entry(client: TestClient, db: Session) -> None:
    from app.services import giveaway_service

    dual_admin = _u(db, "dual_admin_gv", role=UserRole.ADMIN, regions=[Region.NAJAF, Region.BAGHDAD])
    eligible = giveaway_service._eligible_najaf_customers(db)
    assert [u.id for u in eligible].count(dual_admin.id) == 1, "membership of both regions must not double an entry"


# ---------------------------------------------------------------------------
# Baghdad Tuesday reward
# ---------------------------------------------------------------------------


def _next_tuesday() -> date:
    today = datetime.now(BAGHDAD_TZ).date()
    return today + timedelta(days=(1 - today.weekday()) % 7 or 7)


def _freeze(monkeypatch: pytest.MonkeyPatch, when: datetime) -> None:
    monkeypatch.setattr(reward_service, "_now_baghdad", lambda: when)


def _at(day: date, hour: int = 12) -> datetime:
    return datetime(day.year, day.month, day.day, hour, 0, tzinfo=BAGHDAD_TZ)


def test_reward_pays_5000_into_the_baghdad_wallet_only(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    dual = _u(db, "dual", regions=[Region.NAJAF, Region.BAGHDAD], balance=10_000)  # 10k in Najaf
    tuesday = _next_tuesday()
    _freeze(monkeypatch, _at(tuesday))

    body = client.get("/api/rewards/weekly", headers=_h(client, dual, BAGHDAD)).json()
    assert body["available"] is True
    assert body["amount"] == 5_000.0

    db.refresh(dual)
    assert dual.balance_in(Region.BAGHDAD) == 5_000.0, "the reward lands in Baghdad"
    assert dual.balance_in(Region.NAJAF) == 10_000.0, "the Najaf wallet is untouched"

    txn = (
        db.query(BalanceTransaction)
        .filter(BalanceTransaction.user_id == dual.id, BalanceTransaction.transaction_type == TransactionType.REWARD)
        .one()
    )
    assert txn.region == Region.BAGHDAD
    assert float(txn.amount) == 5_000.0


def test_reward_cannot_be_issued_twice_for_the_same_tuesday(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    pool = [_u(db, f"bag{i}", region=Region.BAGHDAD) for i in range(4)]
    tuesday = _next_tuesday()
    _freeze(monkeypatch, _at(tuesday))
    h = _h(client, pool[0], BAGHDAD)

    first = client.get("/api/rewards/weekly", headers=h).json()
    for _ in range(4):
        assert client.get("/api/rewards/weekly", headers=h).json()["winner_username"] == first["winner_username"]

    assert db.query(WeeklyReward).filter(WeeklyReward.reward_date == tuesday).count() == 1
    total = sum(u.balance_in(Region.BAGHDAD) for u in db.query(User).filter(User.id.in_([u.id for u in pool])).all())
    assert total == 5_000.0, "exactly one payout in total"


def test_reward_excludes_najaf_only_users(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Wrong-region membership can't participate, regardless of role: a Najaf
    Customer and a Najaf Admin are both excluded from the Baghdad draw, while
    a same-region Admin remains eligible (see test_baghdad_admin_eligible_for_reward)."""
    bag_cust = _u(db, "bag_cust", region=Region.BAGHDAD)
    bag_admin = _u(db, "bag_admin", role=UserRole.ADMIN, region=Region.BAGHDAD)
    najafis = [_u(db, f"naj{i}", region=Region.NAJAF) for i in range(4)]
    naj_admin = _u(db, "naj_admin_rw", role=UserRole.ADMIN, region=Region.NAJAF)
    _freeze(monkeypatch, _at(_next_tuesday()))

    client.get("/api/rewards/weekly", headers=_h(client, bag_cust, BAGHDAD))

    reward = db.query(WeeklyReward).one()
    assert reward.user_id in {bag_cust.id, bag_admin.id}
    for u in [*najafis, naj_admin]:
        db.refresh(u)
        assert u.balance_in(Region.BAGHDAD) == 0.0


def test_baghdad_admin_eligible_for_reward(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """An Admin belonging to Baghdad is eligible for the Baghdad reward, same
    as a Customer would be — only the region membership matters, not the role."""
    bag_admin = _u(db, "bag_admin_solo", role=UserRole.ADMIN, region=Region.BAGHDAD)
    _freeze(monkeypatch, _at(_next_tuesday()))

    body = client.get("/api/rewards/weekly", headers=_h(client, bag_admin, BAGHDAD)).json()
    assert body["available"] is True
    assert body["winner_username"] == bag_admin.username

    db.refresh(bag_admin)
    assert bag_admin.balance_in(Region.BAGHDAD) == 5_000.0


def test_super_admin_never_eligible_for_reward(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """A Super Admin can view the Baghdad reward (it's global), but can never
    win one — the only eligible account in this pool is the Baghdad customer."""
    boss = _u(db, "boss_rw", role=UserRole.SUPER_ADMIN, region=Region.BAGHDAD)
    bag_cust = _u(db, "bag_cust_su", region=Region.BAGHDAD)
    _freeze(monkeypatch, _at(_next_tuesday()))

    client.get("/api/rewards/weekly", headers=_h(client, boss, BAGHDAD))

    reward = db.query(WeeklyReward).one()
    assert reward.user_id == bag_cust.id
    db.refresh(boss)
    assert boss.balance_in(Region.BAGHDAD) == 0.0


def test_dual_region_customer_gets_one_reward_entry(client: TestClient, db: Session) -> None:
    from app.services import reward_service

    dual = _u(db, "dual_rw_cust", regions=[Region.NAJAF, Region.BAGHDAD])
    eligible = reward_service._eligible_users(db)
    assert [u.id for u in eligible].count(dual.id) == 1, "membership of both regions must not double an entry"


def test_najaf_only_user_cannot_see_the_baghdad_reward(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _u(db, "bag", region=Region.BAGHDAD)
    najafi = _u(db, "naj", region=Region.NAJAF)
    _freeze(monkeypatch, _at(_next_tuesday()))
    assert client.get("/api/rewards/weekly", headers=_h(client, najafi, NAJAF)).json()["available"] is False


def test_no_reward_on_a_non_tuesday(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    cust = _u(db, "bag", region=Region.BAGHDAD)
    _freeze(monkeypatch, _at(_next_tuesday() + timedelta(days=1)))
    assert client.get("/api/rewards/weekly", headers=_h(client, cust, BAGHDAD)).json()["available"] is False
    assert db.query(WeeklyReward).count() == 0


def test_scheduled_job_is_idempotent(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """The systemd timer path: running the draw twice must not pay twice."""
    pool = [_u(db, f"bag{i}", region=Region.BAGHDAD) for i in range(3)]
    tuesday = _next_tuesday()
    _freeze(monkeypatch, _at(tuesday))

    first = reward_service.get_or_create_for_date(db, tuesday)
    second = reward_service.get_or_create_for_date(db, tuesday)
    assert first is not None and second is not None
    assert first.id == second.id

    assert db.query(WeeklyReward).filter(WeeklyReward.reward_date == tuesday).count() == 1
    total = sum(u.balance_in(Region.BAGHDAD) for u in db.query(User).filter(User.id.in_([u.id for u in pool])).all())
    assert total == 5_000.0


def test_checkout_ignores_the_other_regions_cart_lines(client: TestClient, db: Session) -> None:
    """A dual-region shopper may hold lines for both regions at once. Checking
    out in one region must buy and clear only that region's lines, and leave
    the other region's basket untouched — not fail because the cart contains
    something from elsewhere."""
    ahmed = _u(db, "ahmed", regions=[Region.NAJAF, Region.BAGHDAD], balance=100_000)
    boss = _u(db, "boss", role=UserRole.SUPER_ADMIN)
    boss_h = auth_headers(client, boss.username, "password123")
    client.post(f"/api/users/{ahmed.id}/balance", json={"amount": 50_000}, headers={**boss_h, **BAGHDAD})

    najaf_product = make_product(db, name="Najaf Sprite", price=1_000, region=Region.NAJAF)
    baghdad_product = make_product(db, name="Baghdad Pepsi", price=2_000, region=Region.BAGHDAD)

    client.post("/api/cart/items", json={"product_id": str(najaf_product.id), "quantity": 1}, headers=_h(client, ahmed, NAJAF))
    client.post("/api/cart/items", json={"product_id": str(baghdad_product.id), "quantity": 1}, headers=_h(client, ahmed, BAGHDAD))

    resp = client.post("/api/orders/checkout", headers=_h(client, ahmed, NAJAF))
    assert resp.status_code == 200, resp.text
    assert resp.json()["order"]["total_amount"] == 1_000.0, "only the Najaf line is charged"

    # The Baghdad basket survived the Najaf checkout.
    baghdad_cart = client.get("/api/cart", headers=_h(client, ahmed, BAGHDAD)).json()
    assert [i["product"]["name"] for i in baghdad_cart["items"]] == ["Baghdad Pepsi"]
    najaf_cart = client.get("/api/cart", headers=_h(client, ahmed, NAJAF)).json()
    assert najaf_cart["items"] == []
