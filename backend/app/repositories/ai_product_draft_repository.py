import uuid

from sqlalchemy.orm import Session

from app.models.ai_product_draft import AIProductDraft
from app.repositories.base import BaseRepository


class AIProductDraftRepository(BaseRepository[AIProductDraft]):
    model = AIProductDraft

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_by_id(self, draft_id: uuid.UUID) -> AIProductDraft | None:
        return self.db.get(AIProductDraft, draft_id)

    def list_recent(self, limit: int) -> list[AIProductDraft]:
        return self.db.query(AIProductDraft).order_by(AIProductDraft.created_at.desc()).limit(limit).all()
