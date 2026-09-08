import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.transfer import TransferStatus
from app.models.user import Region


class TransferRecipient(BaseModel):
    """One entry in the eligible-recipient list: an active account sharing
    the caller's current region, never the caller themselves -- see
    user_repository.list_transfer_recipients."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    full_name: str
    avatar_url: str | None


class TransferCreate(BaseModel):
    recipient_id: uuid.UUID
    # Same bounds/reasoning as AddBalanceRequest.amount: gt=0 (never zero or
    # negative), allow_inf_nan=False (JSON can smuggle Infinity/NaN past a
    # plain gt=0 check), le=10_000_000 as a sane per-transfer ceiling, and
    # multiple_of=250 keeps every balance-changing operation a whole number
    # of Beans (250 IQD = 1 Bean).
    amount: float = Field(gt=0, le=10_000_000, allow_inf_nan=False, multiple_of=250)
    note: str | None = Field(default=None, max_length=500)


class TransferRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sender_id: uuid.UUID | None
    sender_username: str | None
    sender_full_name: str | None
    sender_avatar_url: str | None
    recipient_id: uuid.UUID | None
    recipient_username: str | None
    recipient_full_name: str | None
    recipient_avatar_url: str | None
    region: Region
    amount: float
    note: str | None
    status: TransferStatus
    created_at: datetime
