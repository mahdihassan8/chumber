import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.regions import assert_can_access
from app.models.order import Order, OrderItem
from app.models.user import Region
from app.models.product import Product
from app.models.transaction import TransactionType
from app.models.user import User
from app.repositories.cart_repository import CartItemRepository
from app.repositories.order_repository import OrderItemRepository, OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.user_repository import UserRepository
from app.services import balance_service
from app.services.balance_service import record_transaction
from app.services.cart_service import get_or_create_cart


def checkout(db: Session, user: User, region: Region) -> Order:
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
        # Lock this region's wallet (not the user row) — the balance being
        # spent lives on the membership, and each region's wallet is an
        # independent account.
        locked_wallet = balance_service.get_locked_membership(db, user, region)

        cart = get_or_create_cart(db, user)
        item_repo = CartItemRepository(db)
        # Only this region's lines are bought and cleared. A dual-region shopper
        # can hold lines for both regions at once; checking out in Najaf must
        # charge and clear the Najaf lines and leave the Baghdad ones sitting in
        # the cart, not fail because the cart contains something from elsewhere.
        all_items = item_repo.list_by_cart(cart.id)
        items = [i for i in all_items if i.product is not None and i.product.region == region]
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
            # Region check inside the money path too: a cart item can only
            # be paid for from the region it belongs to.
            if product is None or not product.is_active or product.region != region:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Product '{item.product_id}' is no longer available")
            if item.quantity > product.stock_quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"'{product.name}' only has {product.stock_quantity} units in stock",
                )
            total += float(product.price) * item.quantity
            line_items.append((product, item.quantity))

        total = round(total, 2)
        if float(locked_wallet.balance) < total:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient balance")

        order = Order(user_id=user.id, region=region, total_amount=total)
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
            user=user,
            region=region,
            amount=-total,
            transaction_type=TransactionType.PURCHASE,
            related_order_id=order.id,
            description=f"Purchase - order {order.id}",
        )

        # Clear only what was just bought — the other region's lines stay.
        for item in items:
            item_repo.delete(item)

        db.commit()
        db.refresh(order)
        return order
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


def list_by_user(db: Session, user_id: uuid.UUID, region: Region | None = None) -> list[Order]:
    return OrderRepository(db).list_by_user(user_id, region)


def list_all(db: Session, region: Region | None) -> list[Order]:
    return OrderRepository(db).list_all(region)
