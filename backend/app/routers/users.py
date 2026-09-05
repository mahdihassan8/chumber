import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.balance import BalanceRead
from app.schemas.order import OrderRead
from app.schemas.user import (
    AddBalanceRequest,
    AdminResetPasswordRequest,
    ChangePasswordRequest,
    MessageResponse,
    UserCreate,
    UserRead,
    UserUpdateByAdmin,
    UserUpdateProfile,
)
from app.services import balance_service, order_service, user_service

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[UserRead]:
    users = user_service.list_users(db)
    return [UserRead.model_validate(u) for u in users]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, _: User = Depends(require_admin), db: Session = Depends(get_db)) -> UserRead:
    user = user_service.create_user(db, payload)
    return UserRead.model_validate(user)


@router.get("/me", response_model=UserRead)
def read_own_profile(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead)
def update_own_profile(
    payload: UserUpdateProfile, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> UserRead:
    user = user_service.update_own_profile(db, current_user, payload)
    return UserRead.model_validate(user)


@router.post("/me/password", response_model=MessageResponse)
def change_own_password(
    payload: ChangePasswordRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> MessageResponse:
    user_service.change_own_password(db, current_user, payload)
    return MessageResponse(message="Password updated successfully")


@router.get("/me/orders", response_model=list[OrderRead])
def read_own_orders(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[OrderRead]:
    orders = order_service.list_by_user(db, current_user.id)
    return [OrderRead.model_validate(o) for o in orders]


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: uuid.UUID, _: User = Depends(require_admin), db: Session = Depends(get_db)) -> UserRead:
    user = user_service.get_user_or_404(db, user_id)
    return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: uuid.UUID, payload: UserUpdateByAdmin, _: User = Depends(require_admin), db: Session = Depends(get_db)
) -> UserRead:
    user = user_service.get_user_or_404(db, user_id)
    user = user_service.update_user_by_admin(db, user, payload)
    return UserRead.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: uuid.UUID, current_admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> None:
    user = user_service.get_user_or_404(db, user_id)
    try:
        user_service.delete_user(db, user, current_admin)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user has existing orders, transactions, or other history and cannot be deleted; deactivate it instead",
        )


@router.post("/{user_id}/password", response_model=MessageResponse)
def admin_reset_password(
    user_id: uuid.UUID, payload: AdminResetPasswordRequest, _: User = Depends(require_admin), db: Session = Depends(get_db)
) -> MessageResponse:
    user = user_service.get_user_or_404(db, user_id)
    user_service.admin_reset_password(db, user, payload.new_password)
    return MessageResponse(message=f"Password reset for {user.username}")


@router.get("/{user_id}/orders", response_model=list[OrderRead])
def get_user_orders(user_id: uuid.UUID, _: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[OrderRead]:
    user_service.get_user_or_404(db, user_id)
    orders = order_service.list_by_user(db, user_id)
    return [OrderRead.model_validate(o) for o in orders]


@router.get("/{user_id}/balance", response_model=BalanceRead)
def get_user_balance(user_id: uuid.UUID, _: User = Depends(require_admin), db: Session = Depends(get_db)) -> BalanceRead:
    user = user_service.get_user_or_404(db, user_id)
    return balance_service.get_balance_summary(db, user)


@router.post("/{user_id}/balance", response_model=BalanceRead)
def add_user_balance(
    user_id: uuid.UUID, payload: AddBalanceRequest, admin: User = Depends(require_admin), db: Session = Depends(get_db)
) -> BalanceRead:
    user = user_service.get_user_or_404(db, user_id)
    balance_service.add_admin_recharge(db, user=user, admin_id=admin.id, amount=payload.amount, description=payload.description)
    return balance_service.get_balance_summary(db, user)


@router.post("/{user_id}/balance/subtract", response_model=BalanceRead)
def subtract_user_balance(
    user_id: uuid.UUID, payload: AddBalanceRequest, admin: User = Depends(require_admin), db: Session = Depends(get_db)
) -> BalanceRead:
    user = user_service.get_user_or_404(db, user_id)
    balance_service.subtract_admin_balance(db, user=user, admin_id=admin.id, amount=payload.amount, description=payload.description)
    return balance_service.get_balance_summary(db, user)
