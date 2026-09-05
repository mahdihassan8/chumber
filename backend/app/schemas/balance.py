import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.transaction import TransactionType


class BalanceTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    # IQD, like every money field in the API.
    amount: float
    transaction_type: TransactionType
    related_order_id: uuid.UUID | None
    created_by_id: uuid.UUID | None
    created_by_username: str | None
    description: str | None
    created_at: datetime


class BalanceRead(BaseModel):
    balance: float
    total_received: float
    total_spent: float
    transactions: list[BalanceTransactionRead]
