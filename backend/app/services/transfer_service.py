import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.transfer import Transfer
from app.models.user import Region, User
from app.repositories.transfer_repository import TransferRepository
from app.repositories.user_repository import UserRepository
from app.services import balance_service


def list_recipients(db: Session, current_user: User, region: Region) -> list[User]:
    return UserRepository(db).list_transfer_recipients(region, exclude_id=current_user.id)


def send(db: Session, *, sender: User, region: Region, recipient_id: uuid.UUID, amount: float, note: str | None) -> Transfer:
    """Moves `amount` from sender's wallet to recipient's wallet, in the same
    region, as one atomic DB transaction -- either both legs land or neither
    does.

    Never trusts the frontend: recipient eligibility and the sender's
    available balance are both re-checked here against the database, even
    though the recipient list and displayed balance were already filtered/
    shown correctly on the frontend.
    """
    if recipient_id == sender.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot transfer money to yourself")

    recipient = UserRepository(db).get_by_id(recipient_id)
    # An invalid, inactive, or out-of-region recipient all look identical
    # from outside -- a 404, never a 403 that would confirm the account
    # exists in another region. Same anti-enumeration reasoning as
    # core.regions.assert_can_access.
    if recipient is None or not recipient.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient not found")
    if balance_service.get_membership(db, recipient, region) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient not found")

    try:
        # Lock both wallets in a deterministic order (lower user id first) so
        # two transfers running in opposite directions at the same time can
        # never deadlock against each other. sorted() only compares the
        # string keys, never the User objects themselves.
        first, second = sorted([sender, recipient], key=lambda u: str(u.id))
        locked_first = balance_service.get_locked_membership(db, first, region)
        locked_second = balance_service.get_locked_membership(db, second, region)
        locked_sender = locked_first if first.id == sender.id else locked_second
        locked_recipient = locked_second if first.id == sender.id else locked_first

        if float(locked_sender.balance) < amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient balance")

        locked_sender.balance = float(locked_sender.balance) - amount
        locked_recipient.balance = float(locked_recipient.balance) + amount

        transfer = Transfer(sender_id=sender.id, recipient_id=recipient.id, region=region, amount=amount, note=note)
        TransferRepository(db).add(transfer)
        db.commit()
        db.refresh(transfer)
        return transfer
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


def list_history(db: Session, user: User, region: Region) -> list[Transfer]:
    return TransferRepository(db).list_for_user(user.id, region)


def list_all(db: Session, region: Region | None) -> list[Transfer]:
    return TransferRepository(db).list_all(region)
