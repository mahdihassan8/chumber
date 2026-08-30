import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.transaction import TransactionType
from app.models.user import User
from app.repositories.cart_repository import CartItemRepository
from app.repositories.order_repository import OrderItemRepository, OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.user_repository import UserRepository
from app.services.balance_service import record_transaction
from app.services.cart_service import get_or_create_cart


def checkout(db: Session, user: User) -> Order:
    """Validates and applies a full cart purchase atomically.

    Locks the user row and every product row involved (SELECT ... FOR UPDATE)
    before re-validating stock/balance, so concurrent checkouts or restocks
    can't race this transaction. On any validation failure the transaction is
    rolled back and nothing is written.
    """
    try:
        # Lock the user row so a concurrent recharge/checkout can't interleave.
        #
        # populate_existing=True matters here: `user` was already loaded earlier
        # in this request (by the get_current_user dependency), so it's already
        # in the session's identity map. Without populate_existing, SQLAlchemy
        # returns that *same cached object* as-is on a repeat SELECT — even one
        # using with_for_update() — without overwriting its attributes from the
        # freshly locked row. The lock would then be real but the in-memory
        # `.balance` we read could still be stale, which is exactly the lost-
        # update bug this locking is meant to prevent. Verified empirically:
        # without populate_existing, a concurrently committed balance change is
        # invisible here even though the row lock itself is correctly acquired.
        locked_user = UserRepository(db).get_locked(user.id)

        cart = get_or_create_cart(db, locked_user)
        item_repo = CartItemRepository(db)
        items = item_repo.list_by_cart(cart.id)
        if not items:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")

        product_ids = [item.product_id for item in items]
        # Same populate_existing requirement as above: item.product could already
        # be identity-mapped (e.g. from cart validation elsewhere in the request),
        # and a stale cached price here would mean charging the wrong amount.
        locked_products = ProductRepository(db).get_locked_map(product_ids)

        total = 0.0
        line_items: list[tuple[Product, int]] = []
        for item in items:
            product = locked_products.get(item.product_id)
            if product is None or not product.is_active:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Product '{item.product_id}' is no longer available")
            if item.quantity > product.stock_quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"'{product.name}' only has {product.stock_quantity} units in stock",
                )
            total += float(product.price) * item.quantity
            line_items.append((product, item.quantity))

        total = round(total, 2)
        if float(locked_user.balance) < total:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient balance")

        order = Order(user_id=locked_user.id, total_amount=total)
        order_repo = OrderRepository(db)
        order_repo.add(order)
        db.flush()

        order_item_repo = OrderItemRepository(db)
        for product, quantity in line_items:
            product.stock_quantity -= quantity
            order_item_repo.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    product_name=product.name,
                    unit_price=product.price,
                    quantity=quantity,
                    subtotal=round(float(product.price) * quantity, 2),
                )
            )

        record_transaction(
            db,
            user=locked_user,
            amount=-total,
            transaction_type=TransactionType.PURCHASE,
            related_order_id=order.id,
            description=f"Purchase - order {order.id}",
        )

        item_repo.delete_all_by_cart(cart.id)

        db.commit()
        db.refresh(order)
        return order
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


def list_by_user(db: Session, user_id: uuid.UUID) -> list[Order]:
    return OrderRepository(db).list_by_user(user_id)


def list_all(db: Session) -> list[Order]:
    return OrderRepository(db).list_all()
