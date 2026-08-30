import uuid
from datetime import date

from pydantic import BaseModel


class GiveawayWinnerRead(BaseModel):
    id: uuid.UUID
    username: str
    full_name: str


class GiveawayResultRead(BaseModel):
    # False only when no giveaway has ever been revealed yet (e.g. the very
    # first scheduled date hasn't reached 11:00 Baghdad time). Every other
    # field below is meaningless/absent in that case.
    available: bool
    scheduled_date: date | None = None
    product_name: str | None = None
    product_image_url: str | None = None
    winners: list[GiveawayWinnerRead] = []
    # Computed server-side from the caller's authenticated identity — never
    # accepted as input, never derived from anything the client sent.
    is_winner: bool = False
