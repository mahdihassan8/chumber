import uuid

from sqlalchemy.orm import Session

from app.models.ai import AIRestockRequest
from app.repositories.base import BaseRepository


class AIRestockRequestRepository(BaseRepository[AIRestockRequest]):
    model = AIRestockRequest

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_by_id(self, request_id: uuid.UUID) -> AIRestockRequest | None:
        return self.db.get(AIRestockRequest, request_id)

    def list_recent(self, limit: int) -> list[AIRestockRequest]:
        return self.db.query(AIRestockRequest).order_by(AIRestockRequest.created_at.desc()).limit(limit).all()
