import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    payload = decode_access_token(credentials.credentials)
    if payload is None or "sub" not in payload:
        raise unauthorized

    try:
        user_id = uuid.UUID(payload["sub"])
    except ValueError:
        raise unauthorized

    user = UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise unauthorized

    # Reject tokens issued before the user's most recent password change —
    # otherwise, with 7-day sessions, changing your password wouldn't log out
    # a stolen/leaked token for up to a week.
    if payload.get("tv") != user.token_version:
        raise unauthorized

    return user


ADMIN_ROLES = (UserRole.ADMIN, UserRole.SUPER_ADMIN)


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Admin *or* Super Admin — the hierarchy is CUSTOMER < ADMIN < SUPER_ADMIN,
    so a Super Admin can do everything an Admin can. Endpoints that must be
    Super-Admin-only use require_super_admin instead."""
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super Admin access required")
    return current_user
