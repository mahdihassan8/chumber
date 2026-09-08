import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import Region, region_enum


class ChumberRequirement(Base):
    """One editable "Chumber required" figure per region.

    Deliberately a single mutable row per region rather than a history log:
    the admin dashboard shows one current value/note, and clearing it means
    the row's amount/note go back to null — the row itself is never deleted,
    so the section always has something to render into and edit.
    """

    __tablename__ = "chumber_requirements"
    __table_args__ = (UniqueConstraint("region", name="uq_chumber_requirement_region"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region: Mapped[Region] = mapped_column(region_enum, nullable=False, index=True)
    amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    updated_by: Mapped["User | None"] = relationship("User")
