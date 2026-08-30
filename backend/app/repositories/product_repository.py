import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    model = Product

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_by_id(self, product_id: uuid.UUID) -> Product | None:
        return self.db.get(Product, product_id)

    def list_all(self) -> list[Product]:
        return self.db.query(Product).all()

    def list_available(self) -> list[Product]:
        return self.db.query(Product).filter(Product.is_active.is_(True), Product.stock_quantity > 0).all()

    def list_active(self) -> list[Product]:
        return self.db.query(Product).filter(Product.is_active.is_(True)).all()

    def get_locked_map(self, product_ids: list[uuid.UUID]) -> dict[uuid.UUID, Product]:
        """SELECT ... FOR UPDATE with populate_existing for every product in
        `product_ids` — see UserRepository.get_locked for why populate_existing
        is required here too (checkout's cart items may already be identity-
        mapped from earlier in the request)."""
        rows = (
            self.db.execute(
                select(Product).where(Product.id.in_(product_ids)).with_for_update().execution_options(populate_existing=True)
            )
            .scalars()
            .all()
        )
        return {p.id: p for p in rows}

    def count(self) -> int:
        return self.db.query(func.count(Product.id)).scalar() or 0

    def count_available(self) -> int:
        return self.db.query(func.count(Product.id)).filter(Product.is_active.is_(True), Product.stock_quantity > 0).scalar() or 0

    def count_out_of_stock(self) -> int:
        return (
            self.db.query(func.count(Product.id)).filter((Product.stock_quantity == 0) | (Product.is_active.is_(False))).scalar() or 0
        )
