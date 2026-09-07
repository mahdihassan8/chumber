import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import ADMIN_ROLES, get_current_user, require_admin
from app.core.regions import get_admin_scope, get_current_region
from app.models.user import Region
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.product import ProductCreate, ProductRead, ProductRestock, ProductUpdate
from app.services import product_service

router = APIRouter(prefix="/api/products", tags=["products"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "static" / "uploads" / "products"
ALLOWED_CONTENT_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


@router.get("", response_model=list[ProductRead])
def list_products(
    current_user: User = Depends(get_current_user),
    # Admin scope rather than current region: it resolves to the caller's own
    # region for everyone except a Super Admin, who may also ask for ALL.
    scope: Region | None = Depends(get_admin_scope),
    db: Session = Depends(get_db),
) -> list[ProductRead]:
    # Super Admin counts as staff here too, so use the shared role set
    # rather than an equality check against ADMIN alone.
    only_available = current_user.role not in ADMIN_ROLES
    products = product_service.list_products(db, only_available=only_available, region=scope)
    return [ProductRead.model_validate(p) for p in products]


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: uuid.UUID, current_user: User = Depends(get_current_user), region: Region = Depends(get_current_region), db: Session = Depends(get_db)) -> ProductRead:
    product = product_service.get_product_or_404(db, product_id, current_user, region)
    if current_user.role not in ADMIN_ROLES and not product.is_available:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return ProductRead.model_validate(product)


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, current_user: User = Depends(require_admin), region: Region = Depends(get_current_region), db: Session = Depends(get_db)) -> ProductRead:
    product = product_service.create_product(db, payload, current_user, region)
    return ProductRead.model_validate(product)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: uuid.UUID, payload: ProductUpdate, current_user: User = Depends(require_admin), region: Region = Depends(get_current_region), db: Session = Depends(get_db)
) -> ProductRead:
    product = product_service.get_product_or_404(db, product_id, current_user, region)
    product = product_service.update_product(db, product, payload)
    return ProductRead.model_validate(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: uuid.UUID, current_user: User = Depends(require_admin), region: Region = Depends(get_current_region), db: Session = Depends(get_db)) -> None:
    product = product_service.get_product_or_404(db, product_id, current_user, region)
    try:
        product_service.delete_product(db, product)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This product has existing orders and cannot be deleted; deactivate it instead",
        )


@router.post("/{product_id}/restock", response_model=ProductRead)
def restock_product(
    product_id: uuid.UUID, payload: ProductRestock, current_user: User = Depends(require_admin), region: Region = Depends(get_current_region), db: Session = Depends(get_db)
) -> ProductRead:
    product = product_service.get_product_or_404(db, product_id, current_user, region)
    product = product_service.restock_product(db, product, payload.quantity)
    return ProductRead.model_validate(product)


@router.post("/{product_id}/image", response_model=ProductRead)
async def upload_product_image(
    product_id: uuid.UUID, file: UploadFile, current_user: User = Depends(require_admin), region: Region = Depends(get_current_region), db: Session = Depends(get_db)
) -> ProductRead:
    product = product_service.get_product_or_404(db, product_id, current_user, region)

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PNG, JPEG or WEBP images are allowed")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File too large (max 5MB)")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    extension = ALLOWED_CONTENT_TYPES[file.content_type]
    filename = f"{product.id}-{uuid.uuid4().hex[:8]}{extension}"
    (UPLOAD_DIR / filename).write_bytes(contents)

    product.image_url = f"/uploads/products/{filename}"
    db.commit()
    db.refresh(product)
    return ProductRead.model_validate(product)
