import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import BalanceTransaction, TransactionType
from app.models.user import Region, User
from app.models.user_region import UserRegion
from app.repositories.balance_transaction_repository import BalanceTransactionRepository
from app.schemas.balance import BalanceRead, BalanceTransactionRead


def get_membership(db: Session, user: User, region: Region) -> UserRegion | None:
    return db.query(UserRegion).filter(UserRegion.user_id == user.id, UserRegion.region == region).first()


def get_locked_membership(db: Session, user: User, region: Region) -> UserRegion:
    """SELECT ... FOR UPDATE on the wallet row, with populate_existing.

    Same lost-update hazard as the old user-row lock: the membership may already
    be identity-mapped from an earlier read in this request, and without
    populate_existing SQLAlchemy hands back that cached object — lock held, stale
    balance read. See order_service.checkout for the full explanation.
    """
    membership = db.execute(
        select(UserRegion)
        .where(UserRegion.user_id == user.id, UserRegion.region == region)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account does not have access to that region",
        )
    return membership


def record_transaction(
    db: Session,
    *,
    user: User,
    region: Region,
    amount: float,
    transaction_type: TransactionType,
    related_order_id: uuid.UUID | None = None,
    created_by_id: uuid.UUID | None = None,
    description: str | None = None,
) -> BalanceTransaction:
    """Applies `amount` to the user's wallet *for one region* and appends a
    ledger row tagged with that region.

    Caller owns the surrounding transaction/commit boundary so this can take part
    in a larger atomic operation (checkout), and must already have locked the
    membership via get_locked_membership.
    """
    membership = get_membership(db, user, region)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account does not have access to that region",
        )

    membership.balance = float(membership.balance) + amount
    txn = BalanceTransaction(
        user_id=user.id,
        region=region,
        amount=amount,
        transaction_type=transaction_type,
        related_order_id=related_order_id,
        created_by_id=created_by_id,
        description=description,
    )
    BalanceTransactionRepository(db).add(txn)
    return txn


def get_balance_summary(db: Session, user: User, region: Region) -> BalanceRead:
    """One region's wallet: its balance, its lifetime totals, and only its own
    transactions. There is deliberately no cross-region total anywhere."""
    txn_repo = BalanceTransactionRepository(db)
    received, spent = txn_repo.sum_received_and_spent(user.id, region)
    transactions = txn_repo.list_by_user(user.id, region)

    return BalanceRead(
        region=region,
        balance=user.balance_in(region),
        total_received=float(received),
        total_spent=float(spent),
        transactions=[BalanceTransactionRead.model_validate(t) for t in transactions],
    )


def add_admin_recharge(
    db: Session, *, user: User, region: Region, admin_id: uuid.UUID, amount: float, description: str | None = None
) -> BalanceTransaction:
    locked = get_locked_membership(db, user, region)
    txn = record_transaction(
        db,
        user=user,
        region=locked.region,
        amount=amount,
        transaction_type=TransactionType.ADMIN_RECHARGE,
        created_by_id=admin_id,
        description=description,
    )
    db.commit()
    db.refresh(locked)
    return txn


def subtract_admin_balance(
    db: Session, *, user: User, region: Region, admin_id: uuid.UUID, amount: float, description: str | None = None
) -> BalanceTransaction:
    """Admin-initiated deduction, logged as an ADJUSTMENT. Overdraft protection
    is per region — a Baghdad wallet can't be paid down using Najaf money."""
    locked = get_locked_membership(db, user, region)

    if amount > float(locked.balance):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot subtract more than the user's current balance ({locked.balance})",
        )

    txn = record_transaction(
        db,
        user=user,
        region=locked.region,
        amount=-amount,
        transaction_type=TransactionType.ADJUSTMENT,
        created_by_id=admin_id,
        description=description,
    )
    db.commit()
    db.refresh(locked)
    return txn
