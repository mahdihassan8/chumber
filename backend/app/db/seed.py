from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models import Cart, User, UserRole
from app.repositories.cart_repository import CartRepository
from app.repositories.user_repository import UserRepository


def seed_bootstrap_admin(db: Session) -> None:
    user_repo = UserRepository(db)
    # Match on username OR email: either one alone already existing means the
    # bootstrap admin was seeded before (an admin may have since renamed
    # their own username via self-service profile editing).
    existing = user_repo.get_by_username_or_email(settings.bootstrap_admin_username, settings.bootstrap_admin_email)
    if existing is not None:
        return

    admin = User(
        username=settings.bootstrap_admin_username,
        email=settings.bootstrap_admin_email,
        full_name="Chumber Admin",
        hashed_password=hash_password(settings.bootstrap_admin_password),
        role=UserRole.ADMIN,
        is_active=True,
        balance=0,
    )
    user_repo.add(admin)
    db.flush()
    CartRepository(db).add(Cart(user_id=admin.id))
    db.commit()
