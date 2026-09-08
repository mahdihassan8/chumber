from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.regions import get_current_region
from app.db.session import get_db
from app.models.user import Region, User
from app.schemas.transfer import TransferCreate, TransferRead, TransferRecipient
from app.services import transfer_service

router = APIRouter(prefix="/api/transfers", tags=["transfers"])


@router.get("/recipients", response_model=list[TransferRecipient])
def list_recipients(
    current_user: User = Depends(get_current_user), region: Region = Depends(get_current_region), db: Session = Depends(get_db)
) -> list[TransferRecipient]:
    recipients = transfer_service.list_recipients(db, current_user, region)
    return [TransferRecipient.model_validate(u) for u in recipients]


@router.post("", response_model=TransferRead, status_code=status.HTTP_201_CREATED)
def create_transfer(
    payload: TransferCreate,
    current_user: User = Depends(get_current_user),
    region: Region = Depends(get_current_region),
    db: Session = Depends(get_db),
) -> TransferRead:
    transfer = transfer_service.send(
        db, sender=current_user, region=region, recipient_id=payload.recipient_id, amount=payload.amount, note=payload.note
    )
    return TransferRead.model_validate(transfer)


@router.get("/history", response_model=list[TransferRead])
def get_transfer_history(
    current_user: User = Depends(get_current_user), region: Region = Depends(get_current_region), db: Session = Depends(get_db)
) -> list[TransferRead]:
    transfers = transfer_service.list_history(db, current_user, region)
    return [TransferRead.model_validate(t) for t in transfers]
