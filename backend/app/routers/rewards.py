from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.regions import can_use, is_super_admin
from app.db.session import get_db
from app.models.user import Region, User
from app.schemas.reward import WeeklyRewardRead
from app.services import reward_service

router = APIRouter(prefix="/api/rewards", tags=["rewards"])


@router.get("/weekly", response_model=WeeklyRewardRead)
def get_weekly_reward(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> WeeklyRewardRead:
    """The Baghdad weekly reward. Najaf accounts get an empty result — this is
    Baghdad data, so it stays inside Baghdad. A Super Admin sees it too."""
    if not can_use(current_user, Region.BAGHDAD):
        return WeeklyRewardRead(available=False)

    reward = reward_service.get_current_reward(db)
    if reward is None:
        return WeeklyRewardRead(available=False)

    return WeeklyRewardRead(
        available=True,
        reward_date=reward.reward_date,
        winner_username=reward.user.username,
        winner_full_name=reward.user.full_name,
        amount=float(reward.amount),
        is_winner=reward.user_id == current_user.id,
    )
