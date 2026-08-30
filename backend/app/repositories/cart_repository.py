import uuid

from sqlalchemy.orm import Session

from app.models.cart import Cart, CartItem
from app.repositories.base import BaseRepository


class CartRepository(BaseRepository[Cart]):
    model = Cart

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_by_user_id(self, user_id: uuid.UUID) -> Cart | None:
        return self.db.query(Cart).filter(Cart.user_id == user_id).first()


class CartItemRepository(BaseRepository[CartItem]):
    model = CartItem

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_by_cart_and_product(self, cart_id: uuid.UUID, product_id: uuid.UUID) -> CartItem | None:
        return self.db.query(CartItem).filter(CartItem.cart_id == cart_id, CartItem.product_id == product_id).first()

    def get_by_id_and_cart(self, item_id: uuid.UUID, cart_id: uuid.UUID) -> CartItem | None:
        return self.db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart_id).first()

    def list_by_cart(self, cart_id: uuid.UUID) -> list[CartItem]:
        return self.db.query(CartItem).filter(CartItem.cart_id == cart_id).all()

    def delete_all_by_cart(self, cart_id: uuid.UUID) -> None:
        self.db.query(CartItem).filter(CartItem.cart_id == cart_id).delete()
