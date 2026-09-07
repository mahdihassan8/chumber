"""Baghdad weekly reward: every Tuesday, one random Baghdad customer gets
5,000 IQD.

Driven by a systemd timer (scripts/run_weekly_reward.py + the units in
deploy/), so the draw happens every Tuesday whether or not anyone opens the app.
Viewing the page can still trigger it as a safety net; both paths funnel through
the same get_or_create, and a UNIQUE(reward_date, region) constraint — not an
application-level "if exists" check — is what makes a double award impossible
when the timer and a page view race.
"""

import random
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.reward import WeeklyReward
from app.models.transaction import TransactionType
from app.models.user import Region, User, UserRole
from app.models.user_region import UserRegion
from app.services import balance_service
from app.services.balance_service import record_transaction

BAGHDAD_TZ = ZoneInfo("Asia/Baghdad")
# date.weekday(): Monday=0 ... Sunday=6.
REWARD_WEEKDAY = 1  # Tuesday
REWARD_AMOUNT_IQD = 5_000.0
REWARD_DESCRIPTION = "Baghdad Weekly Reward"
REWARD_REGION = Region.BAGHDAD


def _now_baghdad() -> datetime:
    """Its own function so tests can freeze "now" instead of waiting for a
    real Tuesday."""
    return datetime.now(BAGHDAD_TZ)


def _is_reward_day(d: date) -> bool:
    return d.weekday() == REWARD_WEEKDAY


def get_by_date(db: Session, reward_date: date) -> WeeklyReward | None:
    return (
        db.query(WeeklyReward)
        .filter(WeeklyReward.reward_date == reward_date, WeeklyReward.region == REWARD_REGION)
        .first()
    )


def _eligible_users(db: Session) -> list[User]:
    """Customers and Admins with Baghdad membership.

    Joining the membership table means a dual-region user appears exactly once,
    so holding both regions gives no extra chance of winning. Super Admins are
    excluded, as is every Najaf-only account.
    """
    return (
        db.query(User)
        .join(UserRegion, UserRegion.user_id == User.id)
        .filter(
            UserRegion.region == REWARD_REGION,
            User.role.in_((UserRole.CUSTOMER, UserRole.ADMIN)),
            User.is_active.is_(True),
        )
        .all()
    )


def _generate_for_date(db: Session, reward_date: date) -> WeeklyReward | None:
    """Draws one winner and credits them, atomically.

    The reward row and the ledger entry are written in a single transaction, so
    there is no window where a winner is recorded without being paid or paid
    without being recorded. If a concurrent request wins the race to INSERT the
    same date, the UNIQUE constraint on reward_date raises IntegrityError here,
    this call rolls back its own (unpaid) attempt and returns the winner that
    actually landed — so the reward can never be issued twice for one Tuesday.
    """
    candidates = _eligible_users(db)
    if not candidates:
        return None

    winner = random.SystemRandom().choice(candidates)

    try:
        # Lock the winner's *Baghdad wallet* — the money goes there and only
        # there, never to their Najaf balance.
        balance_service.get_locked_membership(db, winner, REWARD_REGION)

        reward = WeeklyReward(
            reward_date=reward_date, user_id=winner.id, amount=REWARD_AMOUNT_IQD, region=REWARD_REGION
        )
        db.add(reward)
        db.flush()  # where the once-per-Tuesday race surfaces

        record_transaction(
            db,
            user=winner,
            region=REWARD_REGION,
            amount=REWARD_AMOUNT_IQD,
            transaction_type=TransactionType.REWARD,
            description=f"{REWARD_DESCRIPTION} — {reward_date.isoformat()}",
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        return get_by_date(db, reward_date)

    db.refresh(reward)
    return reward


def get_or_create_for_date(db: Session, reward_date: date) -> WeeklyReward | None:
    existing = get_by_date(db, reward_date)
    if existing is not None:
        return existing
    return _generate_for_date(db, reward_date)


def get_current_reward(db: Session) -> WeeklyReward | None:
    """Today's reward when today is a Tuesday (drawing it on first look),
    otherwise the most recent past one."""
    today = _now_baghdad().date()

    if _is_reward_day(today):
        todays = get_or_create_for_date(db, today)
        if todays is not None:
            return todays

    return (
        db.query(WeeklyReward)
        .filter(WeeklyReward.reward_date < today, WeeklyReward.region == REWARD_REGION)
        .order_by(WeeklyReward.reward_date.desc())
        .first()
    )
