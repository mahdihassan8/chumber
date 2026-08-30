from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin import OverviewStats
from app.schemas.order import OrderRead
from app.services import admin_service, order_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/overview", response_model=OverviewStats)
def get_overview(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> OverviewStats:
    return admin_service.get_overview(db)


@router.get("/orders", response_model=list[OrderRead])
def list_all_orders(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[OrderRead]:
    orders = order_service.list_all(db)
    return [OrderRead.model_validate(o) for o in orders]
