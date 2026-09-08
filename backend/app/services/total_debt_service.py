from sqlalchemy import func

from sqlalchemy.orm import Session

from app.models.total_debt import TotalDebt
from app.models.user import Region, User


def get_or_create(db: Session, region: Region) -> TotalDebt:
    row = db.query(TotalDebt).filter(TotalDebt.region == region).first()
    if row is not None:
        return row
    row = TotalDebt(region=region, amount=None)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def set_value(db: Session, region: Region, amount: float, actor: User) -> TotalDebt:
    row = get_or_create(db, region)
    row.amount = amount
    row.updated_by_id = actor.id
    db.commit()
    db.refresh(row)
    return row


def clear_value(db: Session, region: Region, actor: User) -> TotalDebt:
    """Clears the amount back to null without deleting the row, so the
    section/input stays available for a new value — same contract as
    chumber_requirement_service.clear_value."""
    row = get_or_create(db, region)
    row.amount = None
    row.updated_by_id = actor.id
    db.commit()
    db.refresh(row)
    return row


def sum_debts(db: Session, region: Region | None) -> float:
    """Total debts across the given scope, for the Balance Difference
    calculation -- an unset (null) region's debts count as 0, and None sums
    both regions, matching how total_user_balance/total_inventory_value
    treat an all-regions scope."""
    query = db.query(func.sum(TotalDebt.amount))
    if region is not None:
        query = query.filter(TotalDebt.region == region)
    return float(query.scalar() or 0)
