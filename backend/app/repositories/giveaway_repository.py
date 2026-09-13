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

    def list_recent(self, limit: int = 20) -> list[Giveaway]:
        """Most recent giveaways first, for the admin fulfillment view — with
        the product and every winner (plus who fulfilled them) eager-loaded so
        rendering the list doesn't N+1."""
        return (
            self.db.query(Giveaway)
            .options(
                joinedload(Giveaway.product),
                joinedload(Giveaway.winner_links).joinedload(GiveawayWinner.user),
                joinedload(Giveaway.winner_links).joinedload(GiveawayWinner.fulfilled_by),
            )
            .order_by(Giveaway.scheduled_date.desc())
            .limit(limit)
            .all()
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

    def get(self, giveaway_id: uuid.UUID, user_id: uuid.UUID) -> GiveawayWinner | None:
        return (
            self.db.query(GiveawayWinner)
            .filter(GiveawayWinner.giveaway_id == giveaway_id, GiveawayWinner.user_id == user_id)
            .first()
        )
