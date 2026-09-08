from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.core.regions import get_admin_scope, get_current_region
from app.models.user import Region
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin import OverviewStats
from app.schemas.chumber_requirement import ChumberRequirementRead, ChumberRequirementSet
from app.schemas.order import OrderRead
from app.services import admin_service, chumber_requirement_service, order_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/overview", response_model=OverviewStats)
def get_overview(
    _: User = Depends(require_admin), scope: Region | None = Depends(get_admin_scope), db: Session = Depends(get_db)
) -> OverviewStats:
    return admin_service.get_overview(db, scope)


@router.get("/orders", response_model=list[OrderRead])
def list_all_orders(
    _: User = Depends(require_admin), scope: Region | None = Depends(get_admin_scope), db: Session = Depends(get_db)
) -> list[OrderRead]:
    orders = order_service.list_all(db, scope)
    return [OrderRead.model_validate(o) for o in orders]


# --- Chumber Required ------------------------------------------------------
# Unlike the read-only overview stats above (which can show an all-regions
# total for a Super Admin), this is a mutable per-region record, so it always
# resolves to one concrete region via get_current_region rather than the
# all-or-one get_admin_scope — there's no meaningful single value to edit
# across two regions at once.


@router.get("/chumber-required", response_model=ChumberRequirementRead)
def get_chumber_required(
    _: User = Depends(require_admin), region: Region = Depends(get_current_region), db: Session = Depends(get_db)
) -> ChumberRequirementRead:
    row = chumber_requirement_service.get_or_create(db, region)
    return ChumberRequirementRead.model_validate(row)


@router.put("/chumber-required", response_model=ChumberRequirementRead)
def set_chumber_required(
    payload: ChumberRequirementSet,
    actor: User = Depends(require_admin),
    region: Region = Depends(get_current_region),
    db: Session = Depends(get_db),
) -> ChumberRequirementRead:
    row = chumber_requirement_service.set_value(db, region, payload.amount, payload.note, actor)
    return ChumberRequirementRead.model_validate(row)


@router.delete("/chumber-required", response_model=ChumberRequirementRead, status_code=status.HTTP_200_OK)
def clear_chumber_required(
    actor: User = Depends(require_admin), region: Region = Depends(get_current_region), db: Session = Depends(get_db)
) -> ChumberRequirementRead:
    row = chumber_requirement_service.clear_value(db, region, actor)
    return ChumberRequirementRead.model_validate(row)
