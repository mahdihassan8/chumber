import uuid
from datetime import date

from pydantic import BaseModel


class WeeklyRewardRead(BaseModel):
    """False `available` means no Tuesday reward has been drawn yet — every
    other field is meaningless in that case."""

    available: bool
    reward_date: date | None = None
    winner_username: str | None = None
    winner_full_name: str | None = None
    amount: float | None = None
    # Computed server-side from the caller's own identity, never by the client.
    is_winner: bool = False
