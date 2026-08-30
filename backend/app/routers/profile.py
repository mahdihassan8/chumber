import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import AvatarSelectRequest, UserRead

router = APIRouter(prefix="/api/profile", tags=["profile"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "static" / "uploads" / "avatars"
ALLOWED_CONTENT_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

PREDEFINED_AVATARS = [f"/avatars/avatar-{i}.svg" for i in range(1, 9)]


@router.get("/avatars", response_model=list[str])
def list_predefined_avatars() -> list[str]:
    return PREDEFINED_AVATARS


@router.post("/avatar/select", response_model=UserRead)
def select_avatar(payload: AvatarSelectRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserRead:
    if payload.avatar_url not in PREDEFINED_AVATARS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown predefined avatar")
    current_user.avatar_url = payload.avatar_url
    db.commit()
    db.refresh(current_user)
    return UserRead.model_validate(current_user)


@router.post("/avatar/upload", response_model=UserRead)
async def upload_avatar(
    file: UploadFile, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> UserRead:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PNG, JPEG or WEBP images are allowed")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File too large (max 5MB)")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    extension = ALLOWED_CONTENT_TYPES[file.content_type]
    filename = f"{current_user.id}-{uuid.uuid4().hex[:8]}{extension}"
    (UPLOAD_DIR / filename).write_bytes(contents)

    current_user.avatar_url = f"/uploads/avatars/{filename}"
    db.commit()
    db.refresh(current_user)
    return UserRead.model_validate(current_user)
