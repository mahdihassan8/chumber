from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = UserRepository(db).get_by_username(username)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
