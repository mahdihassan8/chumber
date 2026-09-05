"""Import every model module so Base.metadata is fully populated for Alembic
autogenerate and for `Base.metadata.create_all()` in tests.
"""

from app.models.ai import AIRequestInputType, AIRequestStatus, AIRestockRequest
from app.models.cart import Cart, CartItem
from app.models.giveaway import Giveaway, GiveawayWinner
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.transaction import BalanceTransaction, TransactionType
from app.models.user import User, UserRole

__all__ = [
    "AIRequestInputType",
    "AIRequestStatus",
    "AIRestockRequest",
    "Cart",
    "CartItem",
    "Giveaway",
    "GiveawayWinner",
    "Order",
    "OrderItem",
    "OrderStatus",
    "Product",
    "BalanceTransaction",
    "TransactionType",
    "User",
    "UserRole",
]
