import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import Region, region_enum


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Nullable for the same reason as User.region: pre-existing products have
    # no region until a Super Admin assigns one. An unassigned product is
    # visible only to a Super Admin, never to a regional shopper or admin.
    region: Mapped[Region | None] = mapped_column(region_enum, nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @property
    def is_available(self) -> bool:
        return self.is_active and self.stock_quantity > 0

    @property
    def is_free(self) -> bool:
        """A product is free purely by having price 0 — no separate flag to
        keep in sync. Giveaway prize selection excludes these (see
        ProductRepository.list_giveaway_eligible)."""
        return float(self.price) == 0
