import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.regions import assert_can_access, region_for_new_resource
from app.models.product import Product
from app.models.user import Region, User
from app.repositories.order_repository import OrderItemRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate


def get_sales_map(db: Session) -> dict[uuid.UUID, int]:
    """Total completed-order quantity sold per product. Computed fresh from
    the order ledger on every call — there's no stored column to keep in
    sync, so this is always current as of the latest checkout."""
    sold_rows = OrderItemRepository(db).sales_map()
    return {product_id: int(total) for product_id, total in sold_rows}


def list_products(db: Session, *, only_available: bool, region: Region | None) -> list[Product]:
    repo = ProductRepository(db)
    products = repo.list_available(region) if only_available else repo.list_all(region)

    sold_by_id = get_sales_map(db)
    # Best-selling first; ties (including the common all-zero case) fall back
    # to newest-first, matching the previous default ordering.
    products.sort(key=lambda p: (-sold_by_id.get(p.id, 0), -p.created_at.timestamp()))
    return products


def get_product_or_404(db: Session, product_id: uuid.UUID, viewer: User, current: Region) -> Product:
    """Region check happens here, so *every* by-id product path is covered —
    fetching, editing, restocking, image upload, adding to a cart. A product in
    the other region is reported as not found, never as forbidden."""
    product = ProductRepository(db).get_by_id(product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    assert_can_access(viewer, product.region, current, what="Product")
    return product


def create_product(db: Session, payload: ProductCreate, actor: User, current: Region) -> Product:
    data = payload.model_dump()
    # The product lands in the caller's current region, never one named in
    # the body — a Najaf admin cannot create Baghdad stock.
    data["region"] = region_for_new_resource(actor, current)
    product = Product(**data)
    ProductRepository(db).add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product: Product, payload: ProductUpdate) -> Product:
    # region is not an updatable field: a product stays in the region it was
    # created in, so existing orders and history never change meaning.
    fields = payload.model_dump(exclude_unset=True)
    for field, value in fields.items():
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
