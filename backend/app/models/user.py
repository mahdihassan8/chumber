import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(str, enum.Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"


class Currency(str, enum.Enum):
    USD = "USD"
    IQD = "IQD"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), default=UserRole.CUSTOMER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    balance: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    # The currency this account's balance is denominated in — admin-selectable
    # (see user_service.set_currency), never auto-converted. Every balance
    # figure/transaction amount for this user is displayed in this currency;
    # switching it just relabels the existing raw balance, it never rescales
    # it. Lives on the account rather than per-transaction so a user's ledger
    # can never mix currencies.
    currency: Mapped[Currency] = mapped_column(Enum(Currency, name="currency"), default=Currency.USD, server_default=Currency.USD.value, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Bumped on every password change; embedded in issued JWTs and checked on
    # every request (see core/deps.get_current_user). Since sessions now last
    # 7 days, this is what makes "change password" actually invalidate any
    # other outstanding tokens instead of leaving them valid for the rest of
    # that week.
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    cart: Mapped["Cart | None"] = relationship("Cart", back_populates="user", uselist=False, cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user", foreign_keys="Order.user_id")
    transactions: Mapped[list["BalanceTransaction"]] = relationship(
        "BalanceTransaction", back_populates="user", foreign_keys="BalanceTransaction.user_id"
    )
