import random
import uuid
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.giveaway import Giveaway, GiveawayWinner
from app.repositories.giveaway_repository import GiveawayRepository, GiveawayWinnerRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.user_repository import UserRepository
from app.schemas.giveaway import GiveawayResultRead, GiveawayWinnerRead

BAGHDAD_TZ = ZoneInfo("Asia/Baghdad")
REVEAL_TIME = time(11, 0)
# date.weekday(): Monday=0 ... Sunday=6.
GIVEAWAY_WEEKDAYS = {6, 2}  # Sunday, Wednesday


def _now_baghdad() -> datetime:
    """Broken out as its own function so tests can monkeypatch "now" instead
    of depending on real wall-clock time to exercise the reveal gate."""
    return datetime.now(BAGHDAD_TZ)


def _is_giveaway_day(d: date) -> bool:
    return d.weekday() in GIVEAWAY_WEEKDAYS


def _generate_for_date(db: Session, scheduled_date: date) -> Giveaway | None:
    """Randomly picks 2 unique winners and 1 prize product and persists a new
    Giveaway row. Returns None (generates nothing) if there isn't a large
    enough pool to draw from yet — a small/fresh install shouldn't 500 on a
    Sunday just because there's only one customer so far.

    Concurrency: two requests racing to generate the same date's giveaway
    both get past `if existing` in get_or_create_for_date, both build a
    Giveaway row, but only one INSERT can win against the unique constraint
    on scheduled_date — the loser's commit raises IntegrityError, which the
    caller catches and turns into a re-fetch of the winner's row. Neither
    request can ever see or return a half-written giveaway.
    """
    eligible_users = UserRepository(db).list_active_customers()
    eligible_products = ProductRepository(db).list_active()
    if len(eligible_users) < 2 or not eligible_products:
        return None

    rng = random.SystemRandom()
    winners = rng.sample(eligible_users, 2)
    product = rng.choice(eligible_products)

    giveaway_repo = GiveawayRepository(db)
    giveaway = Giveaway(scheduled_date=scheduled_date, product_id=product.id)
    giveaway_repo.add(giveaway)
    try:
        db.flush()  # assigns giveaway.id, and is where the unique-constraint race would surface
        winner_repo = GiveawayWinnerRepository(db)
        for winner in winners:
            winner_repo.add(GiveawayWinner(giveaway_id=giveaway.id, user_id=winner.id))
        db.commit()
    except IntegrityError:
        db.rollback()
        return giveaway_repo.get_by_date(scheduled_date)

    db.refresh(giveaway)
    return giveaway


def get_or_create_for_date(db: Session, scheduled_date: date) -> Giveaway | None:
    existing = GiveawayRepository(db).get_by_date(scheduled_date)
    if existing is not None:
        return existing
    return _generate_for_date(db, scheduled_date)


def get_current_giveaway(db: Session) -> Giveaway | None:
    """The giveaway to show right now: today's, once today is a scheduled
    day AND it's past the 11:00 Baghdad reveal threshold (generating it on
    first look if it doesn't exist yet — generation and reveal happen
    atomically together under normal operation, so there's no window where
    a giveaway exists in the database but hasn't been revealed).

    Otherwise, the most recently revealed giveaway *strictly before today*.
    Under this module's own generation logic a row for today can't exist
    before its reveal threshold clears, so "most recent row overall" would
    normally be just as safe — but excluding today explicitly here means
    that invariant doesn't have to hold for this function to stay correct
    (e.g. a row inserted directly/out of band, or a future refactor of
    _generate_for_date) can never leak a same-day result early.
    """
    now = _now_baghdad()
    today = now.date()

    if _is_giveaway_day(today) and now.time() >= REVEAL_TIME:
        todays = get_or_create_for_date(db, today)
        if todays is not None:
            return todays

    return GiveawayRepository(db).get_most_recent_before(today)


def build_result(db: Session, current_user_id: uuid.UUID) -> GiveawayResultRead:
    giveaway = get_current_giveaway(db)
    if giveaway is None:
        return GiveawayResultRead(available=False)

    winners = GiveawayWinnerRepository(db).list_by_giveaway(giveaway.id)
    winner_users = [w.user for w in winners]
    is_winner = any(u.id == current_user_id for u in winner_users)

    return GiveawayResultRead(
        available=True,
        scheduled_date=giveaway.scheduled_date,
        product_name=giveaway.product.name,
        product_image_url=giveaway.product.image_url,
        winners=[GiveawayWinnerRead(id=u.id, username=u.username, full_name=u.full_name) for u in winner_users],
        is_winner=is_winner,
    )
