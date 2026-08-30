import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product import ProductRead


class CartItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product: ProductRead
    quantity: int
    subtotal: float


class CartRead(BaseModel):
    items: list[CartItemRead]
    total: float
    balance: float


class AddToCartRequest(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(default=1, ge=1)


class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(ge=1)
