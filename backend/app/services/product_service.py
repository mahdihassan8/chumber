import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.product import Product
from app.repositories.order_repository import OrderItemRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate


def get_sales_map(db: Session) -> dict[uuid.UUID, int]:
    """Total completed-order quantity sold per product. Computed fresh from
    the order ledger on every call — there's no stored column to keep in
    sync, so this is always current as of the latest checkout."""
    sold_rows = OrderItemRepository(db).sales_map()
    return {product_id: int(total) for product_id, total in sold_rows}


def list_products(db: Session, *, only_available: bool) -> list[Product]:
    repo = ProductRepository(db)
    products = repo.list_available() if only_available else repo.list_all()

    sold_by_id = get_sales_map(db)
    # Best-selling first; ties (including the common all-zero case) fall back
    # to newest-first, matching the previous default ordering.
    products.sort(key=lambda p: (-sold_by_id.get(p.id, 0), -p.created_at.timestamp()))
    return products


def get_product_or_404(db: Session, product_id: uuid.UUID) -> Product:
    product = ProductRepository(db).get_by_id(product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


def create_product(db: Session, payload: ProductCreate) -> Product:
    product = Product(**payload.model_dump())
    ProductRepository(db).add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product: Product, payload: ProductUpdate) -> Product:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product: Product) -> None:
    ProductRepository(db).delete(product)
    db.commit()


def restock_product(db: Session, product: Product, quantity: int) -> Product:
    product.stock_quantity += quantity
    product.is_active = True
    db.commit()
    db.refresh(product)
    return product
