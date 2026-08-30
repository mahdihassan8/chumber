import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.ai import AIRequestInputType, AIRequestStatus


class AIRestockParseRequest(BaseModel):
    message: str
    input_type: AIRequestInputType = AIRequestInputType.TEXT


class AIRestockRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    raw_input: str
    input_type: AIRequestInputType
    parsed_action: str | None
    parsed_product_name: str | None
    parsed_quantity: int | None
    resolved_product_id: uuid.UUID | None
    resolved_product_name: str | None = None
    current_stock: int | None = None
    status: AIRequestStatus
    error_message: str | None
    created_at: datetime
