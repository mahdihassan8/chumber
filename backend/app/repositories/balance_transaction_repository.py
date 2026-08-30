import uuid

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.transaction import BalanceTransaction, TransactionType
from app.repositories.base import BaseRepository


class BalanceTransactionRepository(BaseRepository[BalanceTransaction]):
    model = BalanceTransaction

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def sum_received_and_spent(self, user_id: uuid.UUID) -> tuple[float, float]:
        return self.db.execute(
            select(
                func.coalesce(func.sum(case((BalanceTransaction.amount > 0, BalanceTransaction.amount), else_=0)), 0),
                func.coalesce(func.sum(case((BalanceTransaction.amount < 0, -BalanceTransaction.amount), else_=0)), 0),
            ).where(BalanceTransaction.user_id == user_id)
        ).one()

    def list_by_user(self, user_id: uuid.UUID) -> list[BalanceTransaction]:
        return (
            self.db.query(BalanceTransaction)
            .options(joinedload(BalanceTransaction.created_by))
            .filter(BalanceTransaction.user_id == user_id)
            # created_at is a Postgres now() default, stable for the whole
            # surrounding transaction rather than per-statement — see
            # balance_service.get_balance_summary for the tie-break rationale.
            .order_by(BalanceTransaction.created_at.desc(), BalanceTransaction.id.desc())
            .all()
        )

    def list_recent(self, limit: int) -> list[BalanceTransaction]:
        return (
            self.db.query(BalanceTransaction)
            .options(joinedload(BalanceTransaction.user))
            .order_by(BalanceTransaction.created_at.desc())
            .limit(limit)
            .all()
        )

    def sum_admin_recharges(self) -> float:
        return (
            self.db.query(func.coalesce(func.sum(BalanceTransaction.amount), 0))
            .filter(BalanceTransaction.transaction_type == TransactionType.ADMIN_RECHARGE)
            .scalar()
            or 0
        )
