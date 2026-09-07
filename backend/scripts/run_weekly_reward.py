#!/usr/bin/env python3
"""Draw the Baghdad weekly reward. Run by chumber-weekly-reward.timer.

Safe to run repeatedly and safe to run concurrently with a page view: the draw
goes through reward_service.get_or_create_for_date, and the real guarantee is
the UNIQUE(reward_date, region) constraint, so a second run on the same Tuesday
awards nothing.

Exits 0 when a reward exists for today (whether this run created it or found
it), and 0 with a message on a non-Tuesday, so the timer never reports failure
for ordinary no-op days.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal  # noqa: E402
from app.services import reward_service  # noqa: E402


def main() -> int:
    today = reward_service._now_baghdad().date()
    if not reward_service._is_reward_day(today):
        print(f"{today}: not a Tuesday, nothing to do")
        return 0

    db = SessionLocal()
    try:
        existing = reward_service.get_by_date(db, today)
        if existing is not None:
            print(f"{today}: reward already awarded to user {existing.user_id}")
            return 0

        reward = reward_service.get_or_create_for_date(db, today)
        if reward is None:
            print(f"{today}: no eligible Baghdad customers, nothing awarded")
            return 0

        print(f"{today}: awarded {reward.amount} IQD to user {reward.user_id} ({reward.region.value})")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
