from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.regions import can_use
from app.db.session import get_db
from app.models.user import Region, User
from app.schemas.giveaway import GiveawayResultRead
from app.services import giveaway_service

router = APIRouter(prefix="/api/giveaway", tags=["giveaway"])


@router.get("", response_model=GiveawayResultRead)
def get_giveaway(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GiveawayResultRead:
    # current_user comes entirely from the verified JWT (see get_current_user)
    # — there is no request body, query param, or header this endpoint reads
    # to determine identity, winners, the prize, or the current time. All of
    # that is computed server-side in giveaway_service.
    #
    # This is Najaf data (see reward_service's mirror-image comment for the
    # Baghdad reward): an account with no Najaf membership gets an empty
    # result rather than another region's winners/prize, exactly like
    # GET /api/rewards/weekly does for Baghdad. can_use checks the caller's
    # actual membership rows, so a forged X-Region header buys nothing here —
    # this endpoint doesn't even read that header.
    if not can_use(current_user, Region.NAJAF):
        return GiveawayResultRead(available=False)

    return giveaway_service.build_result(db, current_user.id)
