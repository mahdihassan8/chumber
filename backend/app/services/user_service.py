import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.cart import Cart
from app.models.user import Currency, User
from app.repositories.cart_repository import CartRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import ChangePasswordRequest, UserCreate, UserUpdateByAdmin, UserUpdateProfile


def list_users(db: Session) -> list[User]:
    return UserRepository(db).list_all()


def get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def create_user(db: Session, payload: UserCreate) -> User:
    user_repo = UserRepository(db)
    if user_repo.get_by_username(payload.username) is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")
    if user_repo.get_by_email(payload.email) is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
        balance=0,
    )
    user_repo.add(user)
    db.flush()
    CartRepository(db).add(Cart(user_id=user.id))
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User, current_admin: User) -> None:
    if user.id == current_admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account")
    UserRepository(db).delete(user)
    db.commit()


def update_user_by_admin(db: Session, user: User, payload: UserUpdateByAdmin) -> User:
    if payload.email is not None and payload.email != user.email:
        if UserRepository(db).get_by_email_excluding(payload.email, user.id) is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        user.email = payload.email
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active

    db.commit()
    db.refresh(user)
    return user


def update_own_profile(db: Session, user: User, payload: UserUpdateProfile) -> User:
    if payload.username is not None and payload.username != user.username:
        if UserRepository(db).get_by_username_excluding(payload.username, user.id) is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")
        user.username = payload.username
    if payload.full_name is not None:
        user.full_name = payload.full_name

    db.commit()
    db.refresh(user)
    return user


def change_own_password(db: Session, user: User, payload: ChangePasswordRequest) -> None:
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    user.hashed_password = hash_password(payload.new_password)
    # Invalidate any other outstanding sessions for this account — see the
    # token_version comment on the User model.
    user.token_version += 1
    db.commit()


def admin_reset_password(db: Session, user: User, new_password: str) -> None:
    user.hashed_password = hash_password(new_password)
    user.token_version += 1
    db.commit()


def set_currency(db: Session, user: User, currency: Currency) -> User:
    """Relabels the account's balance/ledger currency — never rescales
    `user.balance` or any past transaction amount, per the no-conversion
    rule (see User.currency)."""
    user.currency = currency
    db.commit()
    db.refresh(user)
    return user
