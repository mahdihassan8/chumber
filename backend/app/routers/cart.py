import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.cart import AddToCartRequest, CartRead, UpdateCartItemRequest
from app.services import cart_service

router = APIRouter(prefix="/api/cart", tags=["cart"])


@router.get("", response_model=CartRead)
def get_cart(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CartRead:
    return cart_service.get_cart(db, current_user)


@router.post("/items", response_model=CartRead, status_code=status.HTTP_201_CREATED)
def add_item(payload: AddToCartRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CartRead:
    return cart_service.add_item(db, current_user, payload.product_id, payload.quantity)


@router.patch("/items/{item_id}", response_model=CartRead)
def update_item(
    item_id: uuid.UUID, payload: UpdateCartItemRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> CartRead:
    return cart_service.update_item_quantity(db, current_user, item_id, payload.quantity)


@router.delete("/items/{item_id}", response_model=CartRead)
def remove_item(item_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CartRead:
    return cart_service.remove_item(db, current_user, item_id)
