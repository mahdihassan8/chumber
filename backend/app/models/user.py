import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Region(str, enum.Enum):
    """The two isolated halves of the system. Every account and every product
    belongs to exactly one, and data never crosses between them — only a
    SUPER_ADMIN sees both (see app.core.regions)."""

    BAGHDAD = "baghdad"
    NAJAF = "najaf"


# Shared instance: both users.region and products.region point at the *same*
# Postgres enum type, so it must be one object or create_all would try to
# CREATE TYPE region twice.
region_enum = Enum(Region, name="region")


class UserRole(str, enum.Enum):
    """Privilege hierarchy: CUSTOMER < ADMIN < SUPER_ADMIN.

    SUPER_ADMIN is deliberately not assignable through any API surface (see
    user_service._assert_can_assign_role) — the only way an account gets it is
    the bootstrap seed, so no admin can escalate themselves or anyone else.
    """

    CUSTOMER = "customer"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), default=UserRole.CUSTOMER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Bumped on every password change; embedded in issued JWTs and checked on
    # every request (see core/deps.get_current_user). Since sessions now last
    # 7 days, this is what makes "change password" actually invalidate any
    # other outstanding tokens instead of leaving them valid for the rest of
    # that week.
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Which regions this account may use, and its separate wallet in each.
    # A user has one or two; an Admin exactly one; a Super Admin both.
    memberships: Mapped[list["UserRegion"]] = relationship(
        "UserRegion", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def regions(self) -> list[Region]:
        return sorted((m.region for m in self.memberships), key=lambda r: r.value)

    def balance_in(self, region: Region) -> float:
        """This account's wallet for one region. Regions never share money, so
        there is deliberately no "total balance" anywhere in the app."""
        for m in self.memberships:
            if m.region == region:
                return float(m.balance)
        return 0.0

    cart: Mapped["Cart | None"] = relationship("Cart", back_populates="user", uselist=False, cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user", foreign_keys="Order.user_id")
    transactions: Mapped[list["BalanceTransaction"]] = relationship(
        "BalanceTransaction", back_populates="user", foreign_keys="BalanceTransaction.user_id"
    )
