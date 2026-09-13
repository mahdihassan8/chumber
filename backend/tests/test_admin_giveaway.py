import uuid
from datetime import date, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import Region, User, UserRole
from app.services import giveaway_service
from tests.conftest import auth_headers, make_product, make_user

BAGHDAD = ZoneInfo("Asia/Baghdad")
SUNDAY = 6


def _next_sunday() -> date:
    today = date.today()
    days_ahead = (SUNDAY - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return today + timedelta(days=days_ahead)


def _generate_giveaway(db: Session, monkeypatch: pytest.MonkeyPatch) -> tuple:
    """Generates a real giveaway via the actual service logic and resolves who
    it actually picked — the `admin` fixture is itself Najaf+Admin, so it's a
    live candidate too and either of the two named users below might not be
    drawn; asserting against the real winner_links avoids depending on which
    2 of the 3-person pool got picked."""
    make_user(db, username=f"admgw1_{uuid.uuid4().hex[:6]}", password="password123", role=UserRole.CUSTOMER)
    make_user(db, username=f"admgw2_{uuid.uuid4().hex[:6]}", password="password123", role=UserRole.CUSTOMER)
    product = make_product(db, name=f"Fulfillment Prize {uuid.uuid4().hex[:6]}", price=5, stock=10)
    sunday = _next_sunday()
    import datetime as dt

    monkeypatch.setattr(giveaway_service, "_now_baghdad", lambda: dt.datetime.combine(sunday, time(11, 5), tzinfo=BAGHDAD))
    giveaway = giveaway_service.get_or_create_for_date(db, sunday)
    winners = [link.user for link in giveaway.winner_links]
    return giveaway, winners, product


def test_customer_cannot_list_giveaways_for_admin(client: TestClient, customer: User) -> None:
    headers = auth_headers(client, customer.username, "password123")
    response = client.get("/api/admin/giveaways", headers=headers)
    assert response.status_code == 403


def test_admin_can_list_giveaways_with_winners_and_fulfillment_status(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, admin: User
) -> None:
    giveaway, winners, product = _generate_giveaway(db, monkeypatch)

    headers = auth_headers(client, admin.username, "password123")
    response = client.get("/api/admin/giveaways", headers=headers)
    assert response.status_code == 200
    body = response.json()

    row = next(g for g in body if g["id"] == str(giveaway.id))
    assert row["product_name"] == product.name
    assert {w["username"] for w in row["winners"]} == {u.username for u in winners}
    assert all(w["fulfilled_at"] is None for w in row["winners"])
    assert all(w["fulfilled_by_username"] is None for w in row["winners"])


def test_admin_can_mark_winner_fulfilled(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, admin: User
) -> None:
    giveaway, winners, _product = _generate_giveaway(db, monkeypatch)
    w1 = winners[0]

    headers = auth_headers(client, admin.username, "password123")
    response = client.patch(
        f"/api/admin/giveaways/{giveaway.id}/winners/{w1.id}", json={"fulfilled": True}, headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["fulfilled_at"] is not None
    assert body["fulfilled_by_username"] == admin.username

    # Reflected back in the list view too.
    listing = client.get("/api/admin/giveaways", headers=headers).json()
    row = next(g for g in listing if g["id"] == str(giveaway.id))
    fulfilled_winner = next(w for w in row["winners"] if w["username"] == w1.username)
    assert fulfilled_winner["fulfilled_at"] is not None


def test_admin_can_unmark_fulfilled_winner(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, admin: User
) -> None:
    giveaway, winners, _product = _generate_giveaway(db, monkeypatch)
    w1 = winners[0]
    headers = auth_headers(client, admin.username, "password123")
    client.patch(f"/api/admin/giveaways/{giveaway.id}/winners/{w1.id}", json={"fulfilled": True}, headers=headers)

    response = client.patch(
        f"/api/admin/giveaways/{giveaway.id}/winners/{w1.id}", json={"fulfilled": False}, headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["fulfilled_at"] is None
    assert body["fulfilled_by_username"] is None


def test_marking_fulfillment_for_nonexistent_winner_404s(client: TestClient, db: Session, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.patch(
        f"/api/admin/giveaways/{uuid.uuid4()}/winners/{uuid.uuid4()}", json={"fulfilled": True}, headers=headers
    )
    assert response.status_code == 404


def test_baghdad_only_admin_cannot_access_najaf_giveaway_fulfillment(client: TestClient, db: Session) -> None:
    baghdad_admin = make_user(
        db, username=f"bagadmin_{uuid.uuid4().hex[:6]}", password="password123", role=UserRole.ADMIN, region=Region.BAGHDAD
    )
    headers = auth_headers(client, baghdad_admin.username, "password123")
    response = client.get("/api/admin/giveaways", headers=headers)
    assert response.status_code == 403
