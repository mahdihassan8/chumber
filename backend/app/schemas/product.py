import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    price: float
    stock_quantity: int
    image_url: str | None
    is_active: bool
    is_available: bool
    is_free: bool
    created_at: datetime


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    # Price in IQD. See AddBalanceRequest.amount for why allow_inf_nan=False +
    # a hard cap matter for any client-supplied monetary field, not just
    # balance ones — price feeds directly into checkout's total, so the same
    # protection applies here. ge=0 (rather than gt=0) so a Free product can be
    # created with price=0 — that's the definition of "free" (Product.is_free).
    price: float = Field(ge=0, le=10_000_000, allow_inf_nan=False)
    stock_quantity: int = Field(ge=0, le=100_000)
    image_url: str | None = None
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    price: float | None = Field(default=None, ge=0, le=10_000_000, allow_inf_nan=False)
    stock_quantity: int | None = Field(default=None, ge=0, le=100_000)
    image_url: str | None = None
    is_active: bool | None = None


class ProductRestock(BaseModel):
    quantity: int = Field(gt=0, le=100000)
