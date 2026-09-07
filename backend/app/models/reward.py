import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import Region, region_enum


class WeeklyReward(Base):
    """One Baghdad reward per Tuesday.

    Same shape as Giveaway: the unique constraint on reward_date is what
    actually enforces "only once per Tuesday" under concurrent requests — the
    get-or-create check in reward_service is just the fast path, and the losing
    request of a race gets an IntegrityError and re-reads the winner's row.
    """

    __tablename__ = "weekly_rewards"
    __table_args__ = (UniqueConstraint("reward_date", "region", name="uq_weekly_reward_date_region"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reward_date: Mapped[date] = mapped_column(Date, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    # IQD, like every money column.
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    region: Mapped[Region] = mapped_column(region_enum, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User")
