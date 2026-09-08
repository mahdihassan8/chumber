import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import Region, region_enum


class TotalDebt(Base):
    """A manually-entered "total debts" figure per region, same shape and
    same reasoning as ChumberRequirement: one mutable row per region rather
    than a history log, so clearing it just nulls the amount and the row
    (and therefore the section/input) stays available for a new value.
    """

    __tablename__ = "total_debts"
    __table_args__ = (UniqueConstraint("region", name="uq_total_debt_region"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region: Mapped[Region] = mapped_column(region_enum, nullable=False, index=True)
    amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    updated_by: Mapped["User | None"] = relationship("User")
