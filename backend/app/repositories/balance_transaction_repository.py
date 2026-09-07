import uuid

from sqlalchemy import case, func, select, true as sa_true
from sqlalchemy.orm import Session, joinedload

from app.models.transaction import BalanceTransaction, TransactionType
from app.models.user import Region, User
from app.repositories.base import BaseRepository


class BalanceTransactionRepository(BaseRepository[BalanceTransaction]):
    model = BalanceTransaction

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def sum_received_and_spent(self, user_id: uuid.UUID, region: Region) -> tuple[float, float]:
        return self.db.execute(
            select(
                func.coalesce(func.sum(case((BalanceTransaction.amount > 0, BalanceTransaction.amount), else_=0)), 0),
                func.coalesce(func.sum(case((BalanceTransaction.amount < 0, -BalanceTransaction.amount), else_=0)), 0),
            ).where(BalanceTransaction.user_id == user_id, BalanceTransaction.region == region)
        ).one()

    def list_by_user(self, user_id: uuid.UUID, region: Region | None = None) -> list[BalanceTransaction]:
        return (
            self.db.query(BalanceTransaction)
            .options(joinedload(BalanceTransaction.created_by))
            .filter(BalanceTransaction.user_id == user_id)
            .filter(BalanceTransaction.region == region if region is not None else sa_true())
            # created_at is a Postgres now() default, stable for the whole
            # surrounding transaction rather than per-statement — see
            # balance_service.get_balance_summary for the tie-break rationale.
            .order_by(BalanceTransaction.created_at.desc(), BalanceTransaction.id.desc())
            .all()
        )

    def _scoped(self, query, region: Region | None):  # noqa: ANN001, ANN202
        """Each ledger row records its own region, so a Najaf entry can never
        surface in Baghdad history even for a dual-region account."""
        if region is not None:
            return query.filter(BalanceTransaction.region == region)
        return query

    def list_recent(self, limit: int, region: Region | None = None) -> list[BalanceTransaction]:
        query = self.db.query(BalanceTransaction).options(joinedload(BalanceTransaction.user))
        return self._scoped(query, region).order_by(BalanceTransaction.created_at.desc()).limit(limit).all()

    def sum_admin_recharges(self, region: Region | None = None) -> float:
        query = self.db.query(func.coalesce(func.sum(BalanceTransaction.amount), 0)).filter(
            BalanceTransaction.transaction_type == TransactionType.ADMIN_RECHARGE
        )
        return self._scoped(query, region).scalar() or 0
