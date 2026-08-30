import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Giveaway(Base):
    __tablename__ = "giveaways"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # One row per scheduled date (a Sunday or Wednesday, Baghdad calendar) —
    # the unique constraint is what actually enforces "generated only once
    # per date" under concurrent requests, not just the get-or-create check
    # in giveaway_service (see get_or_create_for_date).
    scheduled_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    product: Mapped["Product"] = relationship("Product")
    winner_links: Mapped[list["GiveawayWinner"]] = relationship(
        "GiveawayWinner", back_populates="giveaway", cascade="all, delete-orphan"
    )


class GiveawayWinner(Base):
    __tablename__ = "giveaway_winners"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    giveaway_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("giveaways.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    giveaway: Mapped["Giveaway"] = relationship("Giveaway", back_populates="winner_links")
    user: Mapped["User"] = relationship("User")

    __table_args__ = (UniqueConstraint("giveaway_id", "user_id", name="uq_giveaway_winner_user"),)
