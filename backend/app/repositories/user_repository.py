import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import Region, User, UserRole
from app.models.user_region import UserRegion
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_by_username(self, username: str) -> User | None:
        return self.db.query(User).filter(User.username == username).first()

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def get_by_username_excluding(self, username: str, exclude_id: uuid.UUID) -> User | None:
        return self.db.query(User).filter(User.username == username, User.id != exclude_id).first()

    def get_by_email_excluding(self, email: str, exclude_id: uuid.UUID) -> User | None:
        return self.db.query(User).filter(User.email == email, User.id != exclude_id).first()

    def get_by_username_or_email(self, username: str, email: str) -> User | None:
        return self.db.query(User).filter((User.username == username) | (User.email == email)).first()

    def get_locked(self, user_id: uuid.UUID) -> User:
        """SELECT ... FOR UPDATE with populate_existing — see the lost-update
        comment on order_service.checkout for why populate_existing matters
        when `user_id` may already be identity-mapped in this session."""
        return self.db.execute(
            select(User).where(User.id == user_id).with_for_update().execution_options(populate_existing=True)
        ).scalar_one()

    def _scoped(self, query, region: Region | None):  # noqa: ANN001, ANN202
        """Region confinement for a User query. None is unrestricted (a Super
        Admin viewing ALL). Otherwise the account must hold a membership in that
        region — a dual-region user therefore shows up for both regions' admins,
        which is correct: they really are a member of both.
        """
        if region is not None:
            return query.join(UserRegion, UserRegion.user_id == User.id).filter(UserRegion.region == region)
        return query

    def list_all(self, region: Region | None = None) -> list[User]:
        return self._scoped(self.db.query(User), region).order_by(User.created_at.desc()).all()

    def list_active_customers(self, region: Region | None = None) -> list[User]:
        query = self.db.query(User).filter(User.role == UserRole.CUSTOMER, User.is_active.is_(True))
        return self._scoped(query, region).all()

    def count(self, region: Region | None = None) -> int:
        return self._scoped(self.db.query(func.count(User.id)), region).scalar() or 0

    def count_by_role(self, role: UserRole, region: Region | None = None) -> int:
        query = self.db.query(func.count(User.id)).filter(User.role == role)
        return self._scoped(query, region).scalar() or 0

    def sum_balances(self, region: Region | None = None) -> float:
        """Total money currently held across every wallet. Summed directly
        over UserRegion rows rather than joined off User: a dual-region user
        has two separate wallets, and going through `_scoped`'s User-join
        would either double their row or require an extra DISTINCT, either of
        which risks silently mis-summing money. None sums every wallet in
        both regions, i.e. the whole system's total."""
        query = self.db.query(func.sum(UserRegion.balance))
        if region is not None:
            query = query.filter(UserRegion.region == region)
        return float(query.scalar() or 0)
