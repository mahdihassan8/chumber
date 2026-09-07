from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.regions import get_current_region
from app.db.session import get_db
from app.models.user import Region, User
from app.schemas.order import CheckoutResponse, OrderRead
from app.services.order_service import checkout

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("/checkout", response_model=CheckoutResponse)
def checkout_cart(current_user: User = Depends(get_current_user), region: Region = Depends(get_current_region), db: Session = Depends(get_db)) -> CheckoutResponse:
    order = checkout(db, current_user, region)
    db.refresh(current_user)
    # The new balance is this region's wallet, not a cross-region total.
    return CheckoutResponse(order=OrderRead.model_validate(order), new_balance=current_user.balance_in(region))
