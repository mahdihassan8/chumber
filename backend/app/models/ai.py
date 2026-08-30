import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AIRequestInputType(str, enum.Enum):
    TEXT = "text"
    VOICE = "voice"


class AIRequestStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    FAILED = "failed"


class AIRestockRequest(Base):
    __tablename__ = "ai_restock_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    raw_input: Mapped[str] = mapped_column(String(1000), nullable=False)
    input_type: Mapped[AIRequestInputType] = mapped_column(Enum(AIRequestInputType, name="ai_input_type"), nullable=False)

    parsed_action: Mapped[str | None] = mapped_column(String(50), nullable=True)
    parsed_product_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    parsed_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resolved_product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)

    status: Mapped[AIRequestStatus] = mapped_column(Enum(AIRequestStatus, name="ai_request_status"), default=AIRequestStatus.PENDING, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    admin: Mapped["User"] = relationship("User", foreign_keys=[admin_id])
    resolved_product: Mapped["Product | None"] = relationship("Product")
