import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.order import Order, OrderItem, OrderStatus
from app.models.user import Region, User
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    model = Order

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def list_by_user(self, user_id: uuid.UUID, region: Region | None = None) -> list[Order]:
        query = self.db.query(Order).options(joinedload(Order.user)).filter(Order.user_id == user_id)
        return self._scoped(query, region).order_by(Order.created_at.desc()).all()

    def _scoped(self, query, region: Region | None):  # noqa: ANN001, ANN202
        """Orders carry their own region (Order.region), recorded at checkout.
        Deriving it from the buyer would be wrong now that a buyer can belong to
        two regions — their Najaf orders must stay Najaf forever."""
        if region is not None:
            return query.filter(Order.region == region)
        return query

    def list_all(self, region: Region | None = None) -> list[Order]:
        query = self.db.query(Order).options(joinedload(Order.user))
        return self._scoped(query, region).order_by(Order.created_at.desc()).all()

    def list_recent(self, limit: int, region: Region | None = None) -> list[Order]:
        query = self.db.query(Order).options(joinedload(Order.user))
        return self._scoped(query, region).order_by(Order.created_at.desc()).limit(limit).all()

    def count(self, region: Region | None = None) -> int:
        return self._scoped(self.db.query(func.count(Order.id)), region).scalar() or 0


class OrderItemRepository(BaseRepository[OrderItem]):
    model = OrderItem

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def sales_map(self) -> list[tuple[uuid.UUID, int]]:
        """Total completed-order quantity sold per product."""
        return (
            self.db.query(OrderItem.product_id, func.sum(OrderItem.quantity))
            .join(Order, Order.id == OrderItem.order_id)
            .filter(Order.status == OrderStatus.COMPLETED)
            .group_by(OrderItem.product_id)
            .all()
        )
