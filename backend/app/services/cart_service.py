import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.regions import assert_can_access
from app.models.cart import Cart, CartItem
from app.models.user import Region, User
from app.repositories.cart_repository import CartItemRepository, CartRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.cart import CartItemRead, CartRead


def get_or_create_cart(db: Session, user: User) -> Cart:
    cart_repo = CartRepository(db)
    cart = cart_repo.get_by_user_id(user.id)
    if cart is None:
        cart = Cart(user_id=user.id)
        cart_repo.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def _serialize(cart: Cart, user: User, region: Region) -> CartRead:
    # Only the current region's lines are shown/charged; a cart line from the
    # other region is invisible here and cannot be checked out.
    items = [
        CartItemRead(id=item.id, product=item.product, quantity=item.quantity, subtotal=round(float(item.product.price) * item.quantity, 2))
        for item in cart.items
        if item.product.region == region
    ]
    total = round(sum(item.subtotal for item in items), 2)
    return CartRead(items=items, total=total, balance=user.balance_in(region))


def get_cart(db: Session, user: User, region: Region) -> CartRead:
    cart = get_or_create_cart(db, user)
    db.refresh(cart)
    return _serialize(cart, user, region)


def add_item(db: Session, user: User, product_id: uuid.UUID, quantity: int, region: Region) -> CartRead:
    cart = get_or_create_cart(db, user)
    product = ProductRepository(db).get_by_id(product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    # Guards the direct-API path: knowing another region's product id must not
    # be enough to put it in a cart.
    assert_can_access(user, product.region, region, what="Product")

    item_repo = CartItemRepository(db)
    existing = item_repo.get_by_cart_and_product(cart.id, product_id)
    desired_quantity = quantity + (existing.quantity if existing else 0)
    if desired_quantity > product.stock_quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Only {product.stock_quantity} units available")

    if existing:
        existing.quantity = desired_quantity
    else:
        item_repo.add(CartItem(cart_id=cart.id, product_id=product_id, quantity=desired_quantity))

    db.commit()
    return get_cart(db, user, region)


def update_item_quantity(db: Session, user: User, item_id: uuid.UUID, quantity: int, region: Region) -> CartRead:
    cart = get_or_create_cart(db, user)
    item = CartItemRepository(db).get_by_id_and_cart(item_id, cart.id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

    if quantity > item.product.stock_quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Only {item.product.stock_quantity} units available")

    item.quantity = quantity
    db.commit()
    return get_cart(db, user, region)


def remove_item(db: Session, user: User, item_id: uuid.UUID, region: Region) -> CartRead:
    cart = get_or_create_cart(db, user)
    item_repo = CartItemRepository(db)
    item = item_repo.get_by_id_and_cart(item_id, cart.id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

    item_repo.delete(item)
    db.commit()
    return get_cart(db, user, region)


def clear_cart(db: Session, cart: Cart) -> None:
    CartItemRepository(db).delete_all_by_cart(cart.id)
