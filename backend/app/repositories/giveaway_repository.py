import uuid
from datetime import date

from sqlalchemy.orm import Session, joinedload

from app.models.giveaway import Giveaway, GiveawayWinner
from app.repositories.base import BaseRepository


class GiveawayRepository(BaseRepository[Giveaway]):
    model = Giveaway

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_by_date(self, scheduled_date: date) -> Giveaway | None:
        return self.db.query(Giveaway).filter(Giveaway.scheduled_date == scheduled_date).first()

    def get_most_recent_before(self, before_date: date) -> Giveaway | None:
        return (
            self.db.query(Giveaway)
            .filter(Giveaway.scheduled_date < before_date)
            .order_by(Giveaway.scheduled_date.desc())
            .first()
        )


class GiveawayWinnerRepository(BaseRepository[GiveawayWinner]):
    model = GiveawayWinner

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def list_by_giveaway(self, giveaway_id: uuid.UUID) -> list[GiveawayWinner]:
        return (
            self.db.query(GiveawayWinner)
            .options(joinedload(GiveawayWinner.user))
            .filter(GiveawayWinner.giveaway_id == giveaway_id)
            .all()
        )
