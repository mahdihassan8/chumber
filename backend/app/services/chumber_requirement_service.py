from sqlalchemy.orm import Session

from app.models.chumber_requirement import ChumberRequirement
from app.models.user import Region, User


def get_or_create(db: Session, region: Region) -> ChumberRequirement:
    row = db.query(ChumberRequirement).filter(ChumberRequirement.region == region).first()
    if row is not None:
        return row
    row = ChumberRequirement(region=region, amount=None, note=None)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def set_value(db: Session, region: Region, amount: float, note: str | None, actor: User) -> ChumberRequirement:
    row = get_or_create(db, region)
    row.amount = amount
    row.note = note
    row.updated_by_id = actor.id
    db.commit()
    db.refresh(row)
    return row


def clear_value(db: Session, region: Region, actor: User) -> ChumberRequirement:
    """Clears the current amount/note back to null. The row itself is never
    deleted, so the section always has something to read and edit into next —
    per the spec, deleting must not remove the input/section itself."""
    row = get_or_create(db, region)
    row.amount = None
    row.note = None
    row.updated_by_id = actor.id
    db.commit()
    db.refresh(row)
    return row
