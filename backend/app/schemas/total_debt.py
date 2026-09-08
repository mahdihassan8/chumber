from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import Region


class TotalDebtRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    region: Region
    amount: float | None
    updated_at: datetime | None


class TotalDebtSet(BaseModel):
    amount: float = Field(ge=0, le=10_000_000_000, allow_inf_nan=False)
