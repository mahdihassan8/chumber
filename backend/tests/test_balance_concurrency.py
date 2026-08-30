"""Regression tests for the row-locking fix in checkout() / add_admin_recharge().

These use genuinely independent DB connections (not the shared, rollback-only
`db` fixture) because the bug only reproduces with two real concurrent
transactions: an object already sitting in one session's identity map, and a
second session committing a change to that same row in between.
"""

import threading
import time
import uuid

from sqlalchemy import select

from app.core.security import hash_password
from app.models.cart import Cart, CartItem
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.transaction import BalanceTransaction
from app.models.user import User, UserRole
from app.services.balance_service import add_admin_recharge
from app.services.order_service import checkout
from tests.conftest import TestSessionLocal


def _make_user(db, *, balance: float) -> User:
    user = User(
        username=f"race_{uuid.uuid4().hex[:10]}",
        email=f"race_{uuid.uuid4().hex[:10]}@example.com",
        full_name="Race Test",
        hashed_password=hash_password("password123"),
        role=UserRole.CUSTOMER,
        is_active=True,
        balance=balance,
    )
    db.add(user)
    db.flush()
    db.add(Cart(user_id=user.id))
    db.commit()
    db.refresh(user)
    return user


def _cleanup(user_id: uuid.UUID, product_id: uuid.UUID | None = None) -> None:
    db = TestSessionLocal()
    try:
        order_ids = [o.id for o in db.query(Order.id).filter(Order.user_id == user_id).all()]
        # BalanceTransaction references orders (related_order_id), so it must
        # go before Order/OrderItem, in addition to before User.
        db.query(BalanceTransaction).filter(
            (BalanceTransaction.user_id == user_id) | (BalanceTransaction.created_by_id == user_id)
        ).delete(synchronize_session=False)
        if order_ids:
            db.query(OrderItem).filter(OrderItem.order_id.in_(order_ids)).delete(synchronize_session=False)
            db.query(Order).filter(Order.id.in_(order_ids)).delete(synchronize_session=False)
        db.query(CartItem).filter(CartItem.cart_id.in_(db.query(Cart.id).filter(Cart.user_id == user_id))).delete(
            synchronize_session=False
        )
        db.query(Cart).filter(Cart.user_id == user_id).delete(synchronize_session=False)
        db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
        if product_id is not None:
            db.query(Product).filter(Product.id == product_id).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def test_concurrent_recharge_and_checkout_do_not_lose_an_update() -> None:
    """Admin recharges +$50 while the customer concurrently checks out a $30
    cart. Whichever happens first, the other must see it: final balance must
    be exactly 100 + 50 - 30 = 120, never 150 (recharge clobbering checkout's
    deduction) or 70 (checkout clobbering the recharge)."""
    setup_db = TestSessionLocal()
    user = _make_user(setup_db, balance=100)
    product = Product(name="Race Product", description="", price=30, stock_quantity=5, is_active=True)
    setup_db.add(product)
    setup_db.commit()
    setup_db.refresh(product)
    setup_db.add(CartItem(cart_id=setup_db.query(Cart).filter(Cart.user_id == user.id).first().id, product_id=product.id, quantity=1))
    setup_db.commit()
    user_id, product_id = user.id, product.id
    setup_db.close()

    barrier = threading.Barrier(2)
    errors: list[Exception] = []

    def do_checkout() -> None:
        db = TestSessionLocal()
        try:
            u = db.get(User, user_id)  # pre-load into this session's identity map, like get_current_user does
            barrier.wait(timeout=5)
            checkout(db, u)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            db.close()

    def do_recharge() -> None:
        db = TestSessionLocal()
        try:
            u = db.get(User, user_id)
            barrier.wait(timeout=5)
            time.sleep(0.05)  # let checkout acquire its lock first, so recharge queues behind it
            add_admin_recharge(db, user=u, admin_id=user_id, amount=50, description="race test recharge")
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            db.close()

    t1 = threading.Thread(target=do_checkout)
    t2 = threading.Thread(target=do_recharge)
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    try:
        assert not errors, f"unexpected errors: {errors}"
        verify_db = TestSessionLocal()
        final_user = verify_db.get(User, user_id)
        assert float(final_user.balance) == 120.0, f"expected 120.0 (lost-update bug would give 150 or 70), got {final_user.balance}"

        # The ledger must independently reconcile to the same number.
        total = sum(float(t.amount) for t in verify_db.query(BalanceTransaction).filter(BalanceTransaction.user_id == user_id).all())
        assert round(100 + total, 2) == 120.0
        verify_db.close()
    finally:
        _cleanup(user_id, product_id)


def test_concurrent_recharges_do_not_lose_an_update() -> None:
    """Two admin recharges of +$20 each, fired concurrently, must both land:
    final balance must be exactly 140, never 120 (one clobbering the other)."""
    setup_db = TestSessionLocal()
    user = _make_user(setup_db, balance=100)
    user_id = user.id
    setup_db.close()

    barrier = threading.Barrier(2)
    errors: list[Exception] = []

    def do_recharge() -> None:
        db = TestSessionLocal()
        try:
            u = db.get(User, user_id)
            barrier.wait(timeout=5)
            add_admin_recharge(db, user=u, admin_id=user_id, amount=20, description="race test recharge")
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            db.close()

    t1 = threading.Thread(target=do_recharge)
    t2 = threading.Thread(target=do_recharge)
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    try:
        assert not errors, f"unexpected errors: {errors}"
        verify_db = TestSessionLocal()
        final_user = verify_db.get(User, user_id)
        assert float(final_user.balance) == 140.0
        verify_db.close()
    finally:
        _cleanup(user_id)
