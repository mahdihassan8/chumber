from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.giveaway import GiveawayResultRead
from app.services import giveaway_service

router = APIRouter(prefix="/api/giveaway", tags=["giveaway"])


@router.get("", response_model=GiveawayResultRead)
def get_giveaway(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GiveawayResultRead:
    # current_user comes entirely from the verified JWT (see get_current_user)
    # — there is no request body, query param, or header this endpoint reads
    # to determine identity, winners, the prize, or the current time. All of
    # that is computed server-side in giveaway_service.
    return giveaway_service.build_result(db, current_user.id)
