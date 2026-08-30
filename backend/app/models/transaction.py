import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import Currency


class TransactionType(str, enum.Enum):
    ADMIN_RECHARGE = "admin_recharge"
    PURCHASE = "purchase"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"


class BalanceTransaction(Base):
    __tablename__ = "balance_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    # Currency lives on the owning User, not per-transaction — a user's
    # ledger is always denominated in whatever currency their account is
    # currently set to (see User.currency), so every row here is displayed
    # in that same currency with no per-row label needed.
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    transaction_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType, name="transaction_type"), nullable=False)
    related_order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="transactions", foreign_keys=[user_id])
    created_by: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_id])
    related_order: Mapped["Order | None"] = relationship("Order")

    @property
    def created_by_username(self) -> str | None:
        return self.created_by.username if self.created_by is not None else None

    @property
    def currency(self) -> Currency:
        """Derived, not stored — always the owning account's *current*
        currency (see User.currency), so a single-account transaction list
        can never show mixed currencies, and a cross-account feed (e.g. the
        admin overview's recent-activity list) still renders each row
        correctly even though its rows belong to different accounts."""
        return self.user.currency
