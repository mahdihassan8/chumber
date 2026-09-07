import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import Region, region_enum


class UserRegion(Base):
    """One account's membership of one region — and its wallet there.

    Membership and balance live on the same row on purpose: a region a user can
    use always has exactly one balance, and a region they cannot use has none.
    That makes "switching region must not move money" structural rather than
    something each query has to remember.
    """

    __tablename__ = "user_regions"
    __table_args__ = (UniqueConstraint("user_id", "region", name="uq_user_region"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    region: Mapped[Region] = mapped_column(region_enum, nullable=False, index=True)
    # IQD, for this region only.
    balance: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="memberships")
