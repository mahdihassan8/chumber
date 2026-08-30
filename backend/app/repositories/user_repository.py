import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
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

    def list_all(self) -> list[User]:
        return self.db.query(User).order_by(User.created_at.desc()).all()

    def list_active_customers(self) -> list[User]:
        return self.db.query(User).filter(User.role == UserRole.CUSTOMER, User.is_active.is_(True)).all()

    def count(self) -> int:
        return self.db.query(func.count(User.id)).scalar() or 0

    def count_by_role(self, role: UserRole) -> int:
        return self.db.query(func.count(User.id)).filter(User.role == role).scalar() or 0
