import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.core.regions import can_use, get_admin_scope, get_current_region
from app.models.user import Region
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin import OverviewStats
from app.schemas.chumber_requirement import ChumberRequirementRead, ChumberRequirementSet
from app.schemas.giveaway import AdminGiveawayRead, AdminGiveawayWinnerRead, GiveawayFulfillmentUpdate
from app.schemas.order import OrderRead
from app.schemas.transfer import TransferRead
from app.services import admin_service, chumber_requirement_service, giveaway_service, order_service, transfer_service

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


@router.get("/transfers", response_model=list[TransferRead])
def list_all_transfers(
    _: User = Depends(require_admin), scope: Region | None = Depends(get_admin_scope), db: Session = Depends(get_db)
) -> list[TransferRead]:
    transfers = transfer_service.list_all(db, scope)
    return [TransferRead.model_validate(t) for t in transfers]


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


# --- Giveaway prize fulfillment ---------------------------------------------
# Najaf-only data, same as the customer-facing GET /api/giveaway — an admin
# without Najaf membership has no business context for these prizes, so this
# mirrors that endpoint's can_use guard rather than relying on require_admin
# alone.


def _require_najaf_admin(actor: User) -> None:
    if not can_use(actor, Region.NAJAF):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to that region")


@router.get("/giveaways", response_model=list[AdminGiveawayRead])
def list_giveaways(actor: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[AdminGiveawayRead]:
    _require_najaf_admin(actor)
    return giveaway_service.list_recent_for_admin(db)


@router.patch("/giveaways/{giveaway_id}/winners/{user_id}", response_model=AdminGiveawayWinnerRead)
def set_giveaway_winner_fulfillment(
    giveaway_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: GiveawayFulfillmentUpdate,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminGiveawayWinnerRead:
    _require_najaf_admin(actor)
    winner = giveaway_service.set_winner_fulfillment(db, giveaway_id, user_id, actor, payload.fulfilled)
    return AdminGiveawayWinnerRead(
        user_id=winner.user_id,
        username=winner.user.username,
        full_name=winner.user.full_name,
        fulfilled_at=winner.fulfilled_at,
        fulfilled_by_username=winner.fulfilled_by.username if winner.fulfilled_by else None,
    )
