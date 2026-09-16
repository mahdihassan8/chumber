import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.ai import AIRequestStatus


class AIProductDraftRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class AIProductDraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    requested_name: str
    source_url: str | None
    source_title: str | None
    extracted_name: str | None
    extracted_description: str | None
    suggested_price: float | None
    image_prompt: str | None
    staged_image_url: str | None
    has_transparency: bool
    status: AIRequestStatus
    error_message: str | None
    created_product_id: uuid.UUID | None
    created_at: datetime


class AIProductDraftConfirm(BaseModel):
    """What the admin actually commits.

    Stock is required — it is the one value the AI never guesses. The rest
    default to the draft's extracted values when omitted, so the admin can
    correct a wrong name or price without being forced to retype the others.
    The bounds mirror ProductCreate exactly, since this feeds the same
    create_product call.
    """

    stock_quantity: int = Field(ge=0, le=100_000)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    price: float | None = Field(default=None, ge=0, le=10_000_000, allow_inf_nan=False)
