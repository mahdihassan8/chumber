from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import Region


class ChumberRequirementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    region: Region
    amount: float | None
    note: str | None
    updated_at: datetime | None


class ChumberRequirementSet(BaseModel):
    # Same protections as every other client-supplied monetary field (see
    # AddBalanceRequest.amount): finite, non-negative, capped.
    amount: float = Field(ge=0, le=10_000_000_000, allow_inf_nan=False)
    note: str | None = Field(default=None, max_length=1000)
