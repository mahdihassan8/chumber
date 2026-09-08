import uuid

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.transfer import Transfer
from app.models.user import Region
from app.repositories.base import BaseRepository


class TransferRepository(BaseRepository[Transfer]):
    model = Transfer

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def _with_parties(self, query):  # noqa: ANN001, ANN202
        return query.options(joinedload(Transfer.sender), joinedload(Transfer.recipient))

    def list_for_user(self, user_id: uuid.UUID, region: Region) -> list[Transfer]:
        """Both sent and received transfers, for one region's wallet only --
        a transfer never crosses regions, so this can't leak the other
        region's history into view."""
        query = self._with_parties(self.db.query(Transfer)).filter(
            Transfer.region == region,
            or_(Transfer.sender_id == user_id, Transfer.recipient_id == user_id),
        )
        return query.order_by(Transfer.created_at.desc(), Transfer.id.desc()).all()

    def list_all(self, region: Region | None = None) -> list[Transfer]:
        query = self._with_parties(self.db.query(Transfer))
        if region is not None:
            query = query.filter(Transfer.region == region)
        return query.order_by(Transfer.created_at.desc(), Transfer.id.desc()).all()
