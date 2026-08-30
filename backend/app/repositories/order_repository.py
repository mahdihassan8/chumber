import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.order import Order, OrderItem, OrderStatus
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    model = Order

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def list_by_user(self, user_id: uuid.UUID) -> list[Order]:
        return (
            self.db.query(Order)
            .options(joinedload(Order.user))
            .filter(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .all()
        )

    def list_all(self) -> list[Order]:
        return self.db.query(Order).options(joinedload(Order.user)).order_by(Order.created_at.desc()).all()

    def list_recent(self, limit: int) -> list[Order]:
        return self.db.query(Order).options(joinedload(Order.user)).order_by(Order.created_at.desc()).limit(limit).all()

    def count(self) -> int:
        return self.db.query(func.count(Order.id)).scalar() or 0


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
