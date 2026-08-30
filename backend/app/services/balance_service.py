import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.transaction import BalanceTransaction, TransactionType
from app.models.user import User
from app.repositories.balance_transaction_repository import BalanceTransactionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.balance import BalanceRead, BalanceTransactionRead


def record_transaction(
    db: Session,
    *,
    user: User,
    amount: float,
    transaction_type: TransactionType,
    related_order_id: uuid.UUID | None = None,
    created_by_id: uuid.UUID | None = None,
    description: str | None = None,
) -> BalanceTransaction:
    """Applies `amount` (positive or negative) to user.balance and appends a ledger row.

    Caller is responsible for the surrounding transaction/commit boundary so this
    can participate in a larger atomic operation (e.g. checkout). Caller must also
    have already locked+refreshed `user` (see add_admin_recharge below) — this
    function trusts the balance it's given. The amount is always in `user.currency`
    (see User.currency) — there's no per-transaction currency, so a user's ledger
    can never mix currencies.
    """
    user.balance = float(user.balance) + amount
    txn = BalanceTransaction(
        user_id=user.id,
        amount=amount,
        transaction_type=transaction_type,
        related_order_id=related_order_id,
        created_by_id=created_by_id,
        description=description,
    )
    BalanceTransactionRepository(db).add(txn)
    return txn


def get_balance_summary(db: Session, user: User) -> BalanceRead:
    """Full balance breakdown for one user: current balance, lifetime totals
    received/spent (computed straight from the ledger, not just echoing the
    cached `balance` column), and the complete transaction history, newest
    first, with the recharging admin's username resolved.
    """
    txn_repo = BalanceTransactionRepository(db)
    received, spent = txn_repo.sum_received_and_spent(user.id)
    transactions = txn_repo.list_by_user(user.id)

    return BalanceRead(
        balance=float(user.balance),
        currency=user.currency,
        total_received=float(received),
        total_spent=float(spent),
        transactions=[BalanceTransactionRead.model_validate(t) for t in transactions],
    )


def add_admin_recharge(db: Session, *, user: User, admin_id: uuid.UUID, amount: float, description: str | None = None) -> BalanceTransaction:
    # Lock + refresh before mutating: `user` may already be identity-mapped
    # from an earlier read in this request, and a plain with_for_update()
    # re-select would still hand back that stale cached balance (see the
    # comment in order_service.checkout for why). populate_existing=True
    # forces the fresh, lock-protected value into the object we mutate below,
    # so a concurrent checkout's deduction can never be silently overwritten.
    # Verified with tests/test_balance_concurrency.py against real concurrent
    # DB connections, not just the single-session test fixture.
    locked_user = UserRepository(db).get_locked(user.id)

    txn = record_transaction(
        db,
        user=locked_user,
        amount=amount,
        transaction_type=TransactionType.ADMIN_RECHARGE,
        created_by_id=admin_id,
        description=description,
    )
    db.commit()
    db.refresh(locked_user)
    return txn


def subtract_admin_balance(db: Session, *, user: User, admin_id: uuid.UUID, amount: float, description: str | None = None) -> BalanceTransaction:
    """Admin-initiated deduction — logged as an ADJUSTMENT (negative amount)
    rather than a new transaction type, matching the ledger's existing
    Recharge/Purchase/Refund/Adjustment vocabulary. Same lock+refresh pattern
    as add_admin_recharge, for the same lost-update reason.
    """
    locked_user = UserRepository(db).get_locked(user.id)

    if amount > float(locked_user.balance):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot subtract more than the user's current balance ({locked_user.balance})",
        )

    txn = record_transaction(
        db,
        user=locked_user,
        amount=-amount,
        transaction_type=TransactionType.ADJUSTMENT,
        created_by_id=admin_id,
        description=description,
    )
    db.commit()
    db.refresh(locked_user)
    return txn
