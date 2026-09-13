import random
import uuid
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.giveaway import Giveaway, GiveawayWinner
from app.repositories.giveaway_repository import GiveawayRepository, GiveawayWinnerRepository
from app.repositories.product_repository import ProductRepository
from app.models.user import Region, User, UserRole
from app.models.user_region import UserRegion
from app.schemas.giveaway import AdminGiveawayRead, AdminGiveawayWinnerRead, GiveawayResultRead, GiveawayWinnerRead

BAGHDAD_TZ = ZoneInfo("Asia/Baghdad")
REVEAL_TIME = time(11, 0)
# date.weekday(): Monday=0 ... Sunday=6.
GIVEAWAY_WEEKDAYS = {6, 2}  # Sunday, Wednesday
WINNER_COUNT = 2


def _now_baghdad() -> datetime:
    """Broken out as its own function so tests can monkeypatch "now" instead
    of depending on real wall-clock time to exercise the reveal gate."""
    return datetime.now(BAGHDAD_TZ)


def _is_giveaway_day(d: date) -> bool:
    return d.weekday() in GIVEAWAY_WEEKDAYS


def _eligible_najaf_customers(db: Session) -> list[User]:
    """Active Customers and Admins holding Najaf membership. Super Admins are
    never eligible, regardless of the regions they happen to be a member of.

    The join yields one row per user, so an account that holds *both* regions is
    a single participant with no extra weight in the Najaf draw.
    """
    return (
        db.query(User)
        .join(UserRegion, UserRegion.user_id == User.id)
        .filter(
            UserRegion.region == Region.NAJAF,
            User.role.in_((UserRole.CUSTOMER, UserRole.ADMIN)),
            User.is_active.is_(True),
        )
        .all()
    )


def _generate_for_date(db: Session, scheduled_date: date) -> Giveaway | None:
    """Randomly picks WINNER_COUNT unique winners and 1 prize product and
    persists a new Giveaway row, reserving that many units of the product's
    stock for the winners in the same transaction. Returns None (generates
    nothing) if there isn't a large enough pool to draw from yet — a
    small/fresh install shouldn't 500 on a Sunday just because there's only
    one customer so far, and it also isn't required to sell out a product to
    zero just to run a giveaway.

    Concurrency: two requests racing to generate the same date's giveaway
    both get past `if existing` in get_or_create_for_date, both build a
    Giveaway row, but only one INSERT can win against the unique constraint
    on scheduled_date — the loser's commit raises IntegrityError, which the
    caller catches and turns into a re-fetch of the winner's row. Neither
    request can ever see or return a half-written giveaway.
    """
    eligible_users = _eligible_najaf_customers(db)
    # Free (price 0) products and anything without enough stock for every
    # winner are excluded — see list_giveaway_eligible.
    eligible_products = ProductRepository(db).list_giveaway_eligible(Region.NAJAF, min_stock=WINNER_COUNT)
    if len(eligible_users) < WINNER_COUNT or not eligible_products:
        return None

    rng = random.SystemRandom()
    winners = rng.sample(eligible_users, WINNER_COUNT)
    product = rng.choice(eligible_products)

    giveaway_repo = GiveawayRepository(db)
    giveaway = Giveaway(scheduled_date=scheduled_date, product_id=product.id)
    giveaway_repo.add(giveaway)
    try:
        db.flush()  # assigns giveaway.id, and is where the unique-constraint race would surface

        # Lock the chosen product and re-check + reserve its stock now, inside
        # this same transaction. This closes the window between the unlocked
        # candidate SELECT above and here, during which a concurrent checkout
        # could have sold the units we're about to promise to winners — the
        # same populate_existing-locking pattern checkout itself uses (see
        # ProductRepository.get_locked_map).
        locked_product = ProductRepository(db).get_locked_map([product.id]).get(product.id)
        if locked_product is None or locked_product.stock_quantity < WINNER_COUNT:
            db.rollback()
            return None
        locked_product.stock_quantity -= WINNER_COUNT

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


def list_recent_for_admin(db: Session, limit: int = 20) -> list[AdminGiveawayRead]:
    """Recent giveaways with per-winner fulfillment status, for the admin
    dashboard's prize fulfillment view."""
    giveaways = GiveawayRepository(db).list_recent(limit)
    return [
        AdminGiveawayRead(
            id=g.id,
            scheduled_date=g.scheduled_date,
            product_id=g.product_id,
            product_name=g.product.name,
            product_image_url=g.product.image_url,
            winners=[
                AdminGiveawayWinnerRead(
                    user_id=w.user_id,
                    username=w.user.username,
                    full_name=w.user.full_name,
                    fulfilled_at=w.fulfilled_at,
                    fulfilled_by_username=w.fulfilled_by.username if w.fulfilled_by else None,
                )
                for w in g.winner_links
            ],
        )
        for g in giveaways
    ]


def set_winner_fulfillment(
    db: Session, giveaway_id: uuid.UUID, user_id: uuid.UUID, admin: User, fulfilled: bool
) -> GiveawayWinner:
    """Marks (or un-marks, in case of a mistaken click) one winner's prize as
    handed over. Idempotent either way — re-marking an already-fulfilled
    winner just refreshes who/when."""
    winner = GiveawayWinnerRepository(db).get(giveaway_id, user_id)
    if winner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Giveaway winner not found")

    winner.fulfilled_at = _now_baghdad() if fulfilled else None
    winner.fulfilled_by_admin_id = admin.id if fulfilled else None
    db.commit()
    db.refresh(winner)
    return winner
