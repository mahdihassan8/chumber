import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.user import Region
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    model = Product

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_by_id(self, product_id: uuid.UUID) -> Product | None:
        return self.db.get(Product, product_id)

    def _scoped(self, region: Region | None):  # noqa: ANN202
        """Applies the caller's region confinement to a Product query. None
        means unrestricted (Super Admin); UNASSIGNED matches nothing."""
        query = self.db.query(Product)
        if region is not None:
            return query.filter(Product.region == region)
        return query

    def list_all(self, region: Region | None = None) -> list[Product]:
        return self._scoped(region).all()

    def list_available(self, region: Region | None = None) -> list[Product]:
        return self._scoped(region).filter(Product.is_active.is_(True), Product.stock_quantity > 0).all()

    def list_active(self, region: Region | None = None) -> list[Product]:
        return self._scoped(region).filter(Product.is_active.is_(True)).all()

    def list_giveaway_eligible(self, region: Region | None = None, min_stock: int = 1) -> list[Product]:
        """Active products excluding Free (price 0) ones — a Free item is
        already free, so it can't be offered as a giveaway prize. `min_stock`
        excludes anything that doesn't have enough units on hand to cover
        every winner (the caller passes the winner count) — a product can't
        be promised as a prize it can't actually deliver."""
        return (
            self._scoped(region)
            .filter(Product.is_active.is_(True), Product.price > 0, Product.stock_quantity >= min_stock)
            .all()
        )

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

    def _scoped_count(self, region: Region | None):  # noqa: ANN202
        query = self.db.query(func.count(Product.id))
        if region is not None:
            return query.filter(Product.region == region)
        return query

    def count(self, region: Region | None = None) -> int:
        return self._scoped_count(region).scalar() or 0

    def count_available(self, region: Region | None = None) -> int:
        return self._scoped_count(region).filter(Product.is_active.is_(True), Product.stock_quantity > 0).scalar() or 0

    def count_out_of_stock(self, region: Region | None = None) -> int:
        return (
            self._scoped_count(region).filter((Product.stock_quantity == 0) | (Product.is_active.is_(False))).scalar() or 0
        )

    def sum_inventory_value(self, region: Region | None = None) -> float:
        """price x stock_quantity summed across every product, active or not
        — this is the value of stock on hand, not of what's currently
        orderable. Computed fresh on every call, same as get_sales_map, so it
        can never drift from the product table."""
        query = self.db.query(func.sum(Product.price * Product.stock_quantity))
        if region is not None:
            query = query.filter(Product.region == region)
        return float(query.scalar() or 0)
