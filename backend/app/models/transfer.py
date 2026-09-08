import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import Region, region_enum


class TransferStatus(str, enum.Enum):
    COMPLETED = "completed"


class Transfer(Base):
    """One already-completed user-to-user money movement, within a single
    region's wallets.

    A row here is only ever created after both legs (debit sender, credit
    recipient) have already been applied atomically in the same DB
    transaction -- see transfer_service.send. There is no "pending" or
    "failed" row: if anything goes wrong, the whole transaction rolls back
    and nothing here is written, which is why status has just one value
    today.
    """

    __tablename__ = "transfers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Nullable + blanked (never the row deleted) if either account is later
    # permanently deleted -- same convention as balance_transactions.created_by_id.
    # This row is shared history between two people, not exclusively either
    # one's data, so it must survive one side's account being removed.
    sender_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    recipient_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    region: Mapped[Region] = mapped_column(region_enum, nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[TransferStatus] = mapped_column(Enum(TransferStatus, name="transfer_status"), default=TransferStatus.COMPLETED, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sender: Mapped["User | None"] = relationship("User", foreign_keys=[sender_id])
    recipient: Mapped["User | None"] = relationship("User", foreign_keys=[recipient_id])

    @property
    def sender_username(self) -> str | None:
        return self.sender.username if self.sender is not None else None

    @property
    def sender_full_name(self) -> str | None:
        return self.sender.full_name if self.sender is not None else None

    @property
    def sender_avatar_url(self) -> str | None:
        return self.sender.avatar_url if self.sender is not None else None

    @property
    def recipient_username(self) -> str | None:
        return self.recipient.username if self.recipient is not None else None

    @property
    def recipient_full_name(self) -> str | None:
        return self.recipient.full_name if self.recipient is not None else None

    @property
    def recipient_avatar_url(self) -> str | None:
        return self.recipient.avatar_url if self.recipient is not None else None
