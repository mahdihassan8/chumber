from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models import Cart, Region, User, UserRegion, UserRole
from app.repositories.cart_repository import CartRepository
from app.repositories.user_repository import UserRepository


def seed_bootstrap_admin(db: Session) -> None:
    """Guarantees the protected Super Admin account exists on every boot.

    This is the *only* place SUPER_ADMIN is ever granted — no API surface can
    assign it (see user_service._assert_can_assign_role), so the role cannot be
    escalated into from inside the running app. An operator changes who holds it
    by pointing BOOTSTRAP_ADMIN_USERNAME at a different account and restarting.
    """
    user_repo = UserRepository(db)
    # Match on username OR email: either one alone already existing means the
    # bootstrap admin was seeded before (an admin may have since renamed
    # their own username via self-service profile editing).
    existing = user_repo.get_by_username_or_email(settings.bootstrap_admin_username, settings.bootstrap_admin_email)
    if existing is not None:
        # Idempotent promote — nothing else about the account is touched, so an
        # existing install keeps its username, password, balance and history.
        if existing.role != UserRole.SUPER_ADMIN:
            existing.role = UserRole.SUPER_ADMIN
            db.commit()
        _ensure_all_regions(db, existing)
        return

    admin = User(
        username=settings.bootstrap_admin_username,
        email=settings.bootstrap_admin_email,
        full_name="Chumber Admin",
        hashed_password=hash_password(settings.bootstrap_admin_password),
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )
    user_repo.add(admin)
    db.flush()
    CartRepository(db).add(Cart(user_id=admin.id))
    db.commit()
    _ensure_all_regions(db, admin)


def _ensure_all_regions(db: Session, user: User) -> None:
    """A Super Admin is global, so it holds a wallet in every region. Adding a
    missing one never touches an existing balance."""
    have = {m.region for m in user.memberships}
    for region in Region:
        if region not in have:
            db.add(UserRegion(user_id=user.id, region=region, balance=0))
    if len(have) < len(list(Region)):
        db.commit()
