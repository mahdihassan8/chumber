import pytest
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.giveaway import Giveaway, GiveawayWinner
from app.models.user import User, UserRole
from app.services import giveaway_service
from tests.conftest import auth_headers, make_product, make_user

BAGHDAD = ZoneInfo("Asia/Baghdad")
SUNDAY = 6
WEDNESDAY = 2


def _next_occurrence(weekday: int) -> date:
    """A date strictly after real "today" that falls on the given weekday —
    used only to pick a stable target date; the actual "now" the service
    sees is always controlled via `_freeze` below, never real wall-clock
    time."""
    today = date.today()
    days_ahead = (weekday - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return today + timedelta(days=days_ahead)


def _at(d: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(d, time(hour, minute), tzinfo=BAGHDAD)


def _freeze(monkeypatch: pytest.MonkeyPatch, when: datetime) -> None:
    monkeypatch.setattr(giveaway_service, "_now_baghdad", lambda: when)


# ---------------------------------------------------------------------------
# Auth / identity
# ---------------------------------------------------------------------------


def test_unauthenticated_request_rejected(client: TestClient) -> None:
    response = client.get("/api/giveaway")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Scheduling / reveal gate
# ---------------------------------------------------------------------------


def test_no_giveaway_available_before_first_ever_reveal(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, admin: User) -> None:
    sunday = _next_occurrence(SUNDAY)
    _freeze(monkeypatch, _at(sunday, 10, 59))
    headers = auth_headers(client, admin.username, "password123")
    response = client.get("/api/giveaway", headers=headers)
    assert response.status_code == 200
    assert response.json()["available"] is False


def test_giveaway_not_generated_in_db_before_reveal_time(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, admin: User) -> None:
    make_user(db, username="cand1", password="password123", role=UserRole.CUSTOMER)
    make_user(db, username="cand2", password="password123", role=UserRole.CUSTOMER)
    make_product(db, name="Prize")
    sunday = _next_occurrence(SUNDAY)
    _freeze(monkeypatch, _at(sunday, 9, 0))

    headers = auth_headers(client, admin.username, "password123")
    client.get("/api/giveaway", headers=headers)

    assert db.query(Giveaway).filter(Giveaway.scheduled_date == sunday).first() is None


def test_giveaway_revealed_at_exactly_11am(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, admin: User) -> None:
    make_user(db, username="cand1b", password="password123", role=UserRole.CUSTOMER)
    make_user(db, username="cand2b", password="password123", role=UserRole.CUSTOMER)
    make_product(db, name="Prize B")
    sunday = _next_occurrence(SUNDAY)
    _freeze(monkeypatch, _at(sunday, 11, 0))

    headers = auth_headers(client, admin.username, "password123")
    response = client.get("/api/giveaway", headers=headers)
    body = response.json()

    assert body["available"] is True
    assert body["scheduled_date"] == sunday.isoformat()
    assert len(body["winners"]) == 2
    assert body["winners"][0]["id"] != body["winners"][1]["id"]
    assert body["product_name"] == "Prize B"


def test_giveaway_generated_only_once_returns_same_winners_and_product(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, admin: User
) -> None:
    make_user(db, username="cand1c", password="password123", role=UserRole.CUSTOMER)
    make_user(db, username="cand2c", password="password123", role=UserRole.CUSTOMER)
    make_user(db, username="cand3c", password="password123", role=UserRole.CUSTOMER)
    make_product(db, name="Prize C1")
    make_product(db, name="Prize C2")
    wednesday = _next_occurrence(WEDNESDAY)
    _freeze(monkeypatch, _at(wednesday, 12, 0))

    headers = auth_headers(client, admin.username, "password123")
    first = client.get("/api/giveaway", headers=headers).json()
    second = client.get("/api/giveaway", headers=headers).json()

    assert first["product_name"] == second["product_name"]
    assert sorted(w["id"] for w in first["winners"]) == sorted(w["id"] for w in second["winners"])
    assert db.query(Giveaway).filter(Giveaway.scheduled_date == wednesday).count() == 1


def test_non_giveaway_day_shows_most_recent_past_result(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, admin: User) -> None:
    make_user(db, username="cand1d", password="password123", role=UserRole.CUSTOMER)
    make_user(db, username="cand2d", password="password123", role=UserRole.CUSTOMER)
    make_product(db, name="Prize D")
    sunday = _next_occurrence(SUNDAY)
    headers = auth_headers(client, admin.username, "password123")

    _freeze(monkeypatch, _at(sunday, 12, 0))
    generated = client.get("/api/giveaway", headers=headers).json()

    monday = sunday + timedelta(days=1)
    _freeze(monkeypatch, _at(monday, 15, 0))
    later = client.get("/api/giveaway", headers=headers).json()

    assert later["available"] is True
    assert later["scheduled_date"] == generated["scheduled_date"]
    assert sorted(w["id"] for w in later["winners"]) == sorted(w["id"] for w in generated["winners"])


def test_todays_giveaway_never_leaks_before_its_own_reveal_even_if_row_exists(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, admin: User
) -> None:
    """Defense in depth: even if a Giveaway row for *today* already exists
    (e.g. written out of band, not through the normal reveal-gated path),
    the endpoint must still not surface it before 11:00 Baghdad time."""
    winner1 = make_user(db, username="early1", password="password123", role=UserRole.CUSTOMER)
    winner2 = make_user(db, username="early2", password="password123", role=UserRole.CUSTOMER)
    product = make_product(db, name="Early Prize")
    sunday = _next_occurrence(SUNDAY)

    giveaway = Giveaway(scheduled_date=sunday, product_id=product.id)
    db.add(giveaway)
    db.flush()
    db.add(GiveawayWinner(giveaway_id=giveaway.id, user_id=winner1.id))
    db.add(GiveawayWinner(giveaway_id=giveaway.id, user_id=winner2.id))
    db.commit()

    _freeze(monkeypatch, _at(sunday, 8, 0))
    headers = auth_headers(client, admin.username, "password123")
    response = client.get("/api/giveaway", headers=headers)
    assert response.json()["available"] is False


def test_scheduled_date_has_db_level_unique_constraint(db: Session) -> None:
    """Belt-and-suspenders: the "generate only once" guarantee doesn't rely
    solely on the application-level get-or-create check — the column itself
    rejects a second row for the same date."""
    product = make_product(db, name="Constraint Test Prize")
    same_date = _next_occurrence(SUNDAY)
    db.add(Giveaway(scheduled_date=same_date, product_id=product.id))
    db.commit()

    db.add(Giveaway(scheduled_date=same_date, product_id=product.id))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


# ---------------------------------------------------------------------------
# Per-user winner status
# ---------------------------------------------------------------------------


def test_actual_winner_sees_is_winner_true(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    # Pool of exactly 2 eligible customers -> both are deterministically the
    # winners (random.sample of 2-from-2), no reliance on random luck.
    w1 = make_user(db, username="detwin1", password="password123", role=UserRole.CUSTOMER)
    w2 = make_user(db, username="detwin2", password="password123", role=UserRole.CUSTOMER)
    make_product(db, name="Deterministic Prize")
    sunday = _next_occurrence(SUNDAY)
    _freeze(monkeypatch, _at(sunday, 11, 5))

    headers = auth_headers(client, w1.username, "password123")
    response = client.get("/api/giveaway", headers=headers)
    body = response.json()

    assert body["is_winner"] is True
    assert {w["id"] for w in body["winners"]} == {str(w1.id), str(w2.id)}


def test_non_winner_sees_is_winner_false(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, admin: User) -> None:
    make_user(db, username="detwin3", password="password123", role=UserRole.CUSTOMER)
    make_user(db, username="detwin4", password="password123", role=UserRole.CUSTOMER)
    make_product(db, name="Deterministic Prize 2")
    sunday = _next_occurrence(SUNDAY)
    _freeze(monkeypatch, _at(sunday, 11, 5))

    # admin is structurally excluded from the eligible pool (role != CUSTOMER),
    # so this is a guaranteed non-winner regardless of which customers were drawn.
    headers = auth_headers(client, admin.username, "password123")
    response = client.get("/api/giveaway", headers=headers)
    assert response.json()["is_winner"] is False


def test_deactivated_customer_never_selected(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, admin: User) -> None:
    inactive = make_user(db, username="inactive_cust", password="password123", role=UserRole.CUSTOMER)
    inactive.is_active = False
    db.commit()
    make_user(db, username="active1", password="password123", role=UserRole.CUSTOMER)
    make_user(db, username="active2", password="password123", role=UserRole.CUSTOMER)
    make_product(db, name="Active Only Prize")
    sunday = _next_occurrence(SUNDAY)
    _freeze(monkeypatch, _at(sunday, 11, 5))

    headers = auth_headers(client, admin.username, "password123")
    response = client.get("/api/giveaway", headers=headers)
    winner_ids = {w["id"] for w in response.json()["winners"]}
    assert str(inactive.id) not in winner_ids


# ---------------------------------------------------------------------------
# Security: client cannot manipulate identity, winner status, or time
# ---------------------------------------------------------------------------


def test_query_and_header_injection_cannot_forge_winner_status(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    winner1 = make_user(db, username="secwin1", password="password123", role=UserRole.CUSTOMER)
    winner2 = make_user(db, username="secwin2", password="password123", role=UserRole.CUSTOMER)
    make_product(db, name="Security Prize")
    sunday = _next_occurrence(SUNDAY)
    _freeze(monkeypatch, _at(sunday, 11, 5))

    winner_headers = auth_headers(client, winner1.username, "password123")
    generated = client.get("/api/giveaway", headers=winner_headers).json()
    assert generated["is_winner"] is True  # sanity check: winner1 really did win

    # Created *after* generation is locked in, so guaranteed not to be a winner.
    outsider = make_user(db, username="secoutsider", password="password123", role=UserRole.CUSTOMER)
    outsider_headers = {
        **auth_headers(client, outsider.username, "password123"),
        "X-User-Id": str(winner1.id),
        "X-Authenticated-User": winner1.username,
    }

    response = client.get(
        f"/api/giveaway?user_id={winner1.id}&is_winner=true&username={winner1.username}",
        headers=outsider_headers,
    )
    assert response.status_code == 200
    body = response.json()
    # Outsider's own (real) identity governs the result, not anything injected.
    assert body["is_winner"] is False
    # The public winner list itself is correct and unaffected either way.
    assert {w["id"] for w in body["winners"]} == {str(winner1.id), str(winner2.id)}


def test_request_body_cannot_forge_winner_status(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    winner1 = make_user(db, username="bodywin1", password="password123", role=UserRole.CUSTOMER)
    make_user(db, username="bodywin2", password="password123", role=UserRole.CUSTOMER)
    make_product(db, name="Body Security Prize")
    sunday = _next_occurrence(SUNDAY)
    _freeze(monkeypatch, _at(sunday, 11, 5))

    headers = auth_headers(client, winner1.username, "password123")
    client.get("/api/giveaway", headers=headers)  # lock in generation

    outsider = make_user(db, username="bodyoutsider", password="password123", role=UserRole.CUSTOMER)
    outsider_headers = auth_headers(client, outsider.username, "password123")
    response = client.request(
        "GET",
        "/api/giveaway",
        headers=outsider_headers,
        json={"user_id": str(winner1.id), "is_winner": True, "username": winner1.username},
    )
    assert response.status_code == 200
    assert response.json()["is_winner"] is False


def test_client_supplied_time_is_ignored(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, admin: User) -> None:
    make_user(db, username="timecand1", password="password123", role=UserRole.CUSTOMER)
    make_user(db, username="timecand2", password="password123", role=UserRole.CUSTOMER)
    make_product(db, name="Time Prize")
    sunday = _next_occurrence(SUNDAY)
    _freeze(monkeypatch, _at(sunday, 9, 0))  # genuinely before reveal

    headers = {
        **auth_headers(client, admin.username, "password123"),
        "X-Mock-Time": "2099-01-01T12:00:00",
    }
    response = client.get(
        "/api/giveaway?now=2099-01-01T12:00:00&reveal=true&time=11:30",
        headers=headers,
    )
    assert response.json()["available"] is False


# ---------------------------------------------------------------------------
# Free products excluded from the prize pool
# ---------------------------------------------------------------------------


def test_free_product_never_selected_as_prize(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, admin: User) -> None:
    make_user(db, username="freecand1", password="password123", role=UserRole.CUSTOMER)
    make_user(db, username="freecand2", password="password123", role=UserRole.CUSTOMER)
    make_product(db, name="Free Giveaway Bait", price=0, stock=10)
    paid = make_product(db, name="Only Paid Prize", price=5, stock=10)
    sunday = _next_occurrence(SUNDAY)
    _freeze(monkeypatch, _at(sunday, 11, 5))

    headers = auth_headers(client, admin.username, "password123")
    response = client.get("/api/giveaway", headers=headers)
    body = response.json()
    assert body["available"] is True
    assert body["product_name"] == paid.name


def test_giveaway_not_generated_when_only_free_products_exist(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, admin: User
) -> None:
    make_user(db, username="onlyfree1", password="password123", role=UserRole.CUSTOMER)
    make_user(db, username="onlyfree2", password="password123", role=UserRole.CUSTOMER)
    make_product(db, name="Only Free Item", price=0, stock=10)
    sunday = _next_occurrence(SUNDAY)
    _freeze(monkeypatch, _at(sunday, 11, 5))

    headers = auth_headers(client, admin.username, "password123")
    response = client.get("/api/giveaway", headers=headers)
    assert response.json()["available"] is False


def test_two_different_users_get_independently_correct_winner_status(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same giveaway, two different callers -> each sees their *own* status,
    proving is_winner is computed per-caller from their auth token rather
    than being some fixed/shared value."""
    w1 = make_user(db, username="dualwin1", password="password123", role=UserRole.CUSTOMER)
    w2 = make_user(db, username="dualwin2", password="password123", role=UserRole.CUSTOMER)
    make_product(db, name="Dual Prize")
    sunday = _next_occurrence(SUNDAY)
    _freeze(monkeypatch, _at(sunday, 11, 5))

    r1 = client.get("/api/giveaway", headers=auth_headers(client, w1.username, "password123"))
    r2 = client.get("/api/giveaway", headers=auth_headers(client, w2.username, "password123"))

    assert r1.json()["is_winner"] is True
    assert r2.json()["is_winner"] is True  # both of the 2-person pool won
