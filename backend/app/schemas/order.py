import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.order import OrderStatus


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    unit_price: float
    quantity: int
    subtotal: float


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    user_username: str
    user_full_name: str
    total_amount: float
    status: OrderStatus
    created_at: datetime
    items: list[OrderItemRead]


class CheckoutResponse(BaseModel):
    order: OrderRead
    new_balance: float
