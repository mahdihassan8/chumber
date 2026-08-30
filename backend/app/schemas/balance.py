import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.transaction import TransactionType
from app.models.user import Currency


class BalanceTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    amount: float
    # Derived from the owning account's *current* User.currency (see
    # BalanceTransaction.currency) — not stored, not admin-selectable per
    # transaction. Present so a transaction list spanning multiple accounts
    # (e.g. the admin overview's recent-activity feed) can render each row
    # in its own account's currency without a second lookup.
    currency: Currency
    transaction_type: TransactionType
    related_order_id: uuid.UUID | None
    created_by_id: uuid.UUID | None
    created_by_username: str | None
    description: str | None
    created_at: datetime


class BalanceRead(BaseModel):
    balance: float
    currency: Currency
    total_received: float
    total_spent: float
    transactions: list[BalanceTransactionRead]
