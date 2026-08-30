from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.balance import BalanceRead
from app.services.balance_service import get_balance_summary

router = APIRouter(prefix="/api/balance", tags=["balance"])


@router.get("", response_model=BalanceRead)
def get_own_balance(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> BalanceRead:
    return get_balance_summary(db, current_user)
