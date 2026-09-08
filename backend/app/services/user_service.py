import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.regions import allowed_regions, assert_can_access, is_super_admin
from app.core.security import hash_password, verify_password
from app.models.ai import AIRestockRequest
from app.models.cart import Cart, CartItem
from app.models.chumber_requirement import ChumberRequirement
from app.models.giveaway import GiveawayWinner
from app.models.order import Order, OrderItem
from app.models.transaction import BalanceTransaction
from app.models.transfer import Transfer
from app.models.reward import WeeklyReward
from app.models.user import Region, User, UserRole
from app.models.user_region import UserRegion
from app.repositories.cart_repository import CartRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import ChangePasswordRequest, UserCreate, UserUpdateByAdmin, UserUpdateProfile


def list_users(db: Session, scope: Region | None) -> list[User]:
    return UserRepository(db).list_all(scope)


def get_user_or_404(db: Session, user_id: uuid.UUID, viewer: User | None = None, scope: Region | None = None) -> User:
    """The single choke point for by-id account access.

    A regional admin (scope = their region) can only reach accounts that are
    members of that region; anything else is reported as not found, so ids from
    the other region reveal nothing. A Super Admin viewing ALL passes scope=None
    and sees everyone."""
    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if scope is not None and scope not in user.regions and not (viewer is not None and is_super_admin(viewer)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def set_user_regions(db: Session, user: User, regions: list[Region], actor: User) -> User:
    """Replaces an account's regional memberships.

    Only a Super Admin may call this. Adding a region creates an empty wallet for
    it; removing one deletes only the membership row — the account's orders and
    ledger history for that region are left completely untouched, because
    history belongs to the region it happened in, not to the current permission.
    """
    if not is_super_admin(actor):
        raise _forbidden("Only a Super Admin can change an account's region access")
    if user.role == UserRole.SUPER_ADMIN:
        raise _forbidden("A Super Admin is global and its regions cannot be changed")
    if not regions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An account must belong to at least one region")
    if user.role == UserRole.ADMIN and len(regions) > 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An Admin must belong to exactly one region")

    wanted = set(regions)
    existing = {m.region: m for m in user.memberships}

    for region in wanted - set(existing):
        db.add(UserRegion(user_id=user.id, region=region, balance=0))
    for region in set(existing) - wanted:
        # Only the permission goes; the money and history for that region stay
        # on their own rows and reappear intact if access is granted again.
        db.delete(existing[region])

    db.commit()
    db.refresh(user)
    return user


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def _assert_can_assign_role(role: UserRole | None, actor: User) -> None:
    """Role assignment rules, enforced server-side regardless of what the UI
    offers: SUPER_ADMIN is never assignable through the API (the bootstrap seed
    is the only source of it), and only a Super Admin may hand out or take away
    ADMIN."""
    if role is None:
        return
    if role == UserRole.SUPER_ADMIN:
        raise _forbidden("The Super Admin role cannot be assigned through the API")
    if role == UserRole.ADMIN and actor.role != UserRole.SUPER_ADMIN:
        raise _forbidden("Only a Super Admin can grant the Admin role")


def _assert_can_manage_target(target: User, actor: User) -> None:
    """A Super Admin account can only be touched by a Super Admin — otherwise a
    regular Admin could deactivate, rename or reset the password of the very
    account that outranks them."""
    if target.role == UserRole.SUPER_ADMIN and actor.role != UserRole.SUPER_ADMIN:
        raise _forbidden("Only a Super Admin can modify a Super Admin account")
    if target.role == UserRole.ADMIN and actor.role != UserRole.SUPER_ADMIN and target.id != actor.id:
        raise _forbidden("Only a Super Admin can modify another Admin account")


def create_user(db: Session, payload: UserCreate, actor: User, current: Region) -> User:
    _assert_can_assign_role(payload.role, actor)
    # New accounts always land in the creator's current region. A Super Admin
    # can widen access afterwards via set_user_regions; a regional admin
    # cannot, so a Najaf admin can never seed a Baghdad account.
    region = current

    user_repo = UserRepository(db)
    if user_repo.get_by_username(payload.username) is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")
    if user_repo.get_by_email(payload.email) is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    user_repo.add(user)
    db.flush()
    db.add(UserRegion(user_id=user.id, region=region, balance=0))
    CartRepository(db).add(Cart(user_id=user.id))
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User, current_admin: User) -> None:
    if user.id == current_admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account")
    if user.role == UserRole.SUPER_ADMIN:
        raise _forbidden("The Super Admin account cannot be deleted")
    if user.role == UserRole.ADMIN and current_admin.role != UserRole.SUPER_ADMIN:
        raise _forbidden("Only a Super Admin can delete an Admin account")
    UserRepository(db).delete(user)
    db.commit()


def permanently_delete_user(db: Session, user: User, super_admin: User, confirm_username: str) -> None:
    """Erases an account and every record that belongs exclusively to it, in one
    transaction — either all of it goes or none of it does.

    Deletion order is dictated by the foreign keys (no ON DELETE CASCADE exists
    in this schema, and adding one would be wrong here — see the created_by_id
    step below, which a blanket cascade would get actively wrong by deleting
    other people's ledger rows).

    Shared/global data is deliberately left alone: products stay, and a
    giveaway the user won keeps existing — only their winner link is removed.
    """
    if user.id == super_admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account")
    if user.role == UserRole.SUPER_ADMIN:
        raise _forbidden("The Super Admin account cannot be deleted")
    # Re-checked server-side even though the dialog already asked for it: the
    # confirmation is part of the API contract, not a UI nicety.
    if confirm_username != user.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The confirmation username does not match this account's username",
        )

    try:
        # Other users' ledger rows that this account created (as the acting
        # admin) are NOT this account's data — blank the attribution and keep
        # the row, so those users' balance histories stay intact and correct.
        db.query(BalanceTransaction).filter(BalanceTransaction.created_by_id == user.id).update(
            {BalanceTransaction.created_by_id: None}, synchronize_session=False
        )
        # Same reasoning: a Chumber Required value this admin set is region
        # data, not theirs — keep the figure, just blank who last touched it.
        db.query(ChumberRequirement).filter(ChumberRequirement.updated_by_id == user.id).update(
            {ChumberRequirement.updated_by_id: None}, synchronize_session=False
        )
        # A transfer is shared history between two people, not exclusively
        # either one's data -- it must survive one side's account being
        # removed, so blank whichever end points at this account rather than
        # deleting the row (which would erase the other party's history too).
        db.query(Transfer).filter(Transfer.sender_id == user.id).update(
            {Transfer.sender_id: None}, synchronize_session=False
        )
        db.query(Transfer).filter(Transfer.recipient_id == user.id).update(
            {Transfer.recipient_id: None}, synchronize_session=False
        )

        db.query(GiveawayWinner).filter(GiveawayWinner.user_id == user.id).delete(synchronize_session=False)
        db.query(WeeklyReward).filter(WeeklyReward.user_id == user.id).delete(synchronize_session=False)
        db.query(UserRegion).filter(UserRegion.user_id == user.id).delete(synchronize_session=False)
        db.query(AIRestockRequest).filter(AIRestockRequest.admin_id == user.id).delete(synchronize_session=False)

        # Before orders: a purchase row points at the order it paid for.
        db.query(BalanceTransaction).filter(BalanceTransaction.user_id == user.id).delete(synchronize_session=False)

        order_ids = [row[0] for row in db.query(Order.id).filter(Order.user_id == user.id).all()]
        if order_ids:
            db.query(OrderItem).filter(OrderItem.order_id.in_(order_ids)).delete(synchronize_session=False)
            db.query(Order).filter(Order.id.in_(order_ids)).delete(synchronize_session=False)

        cart_ids = [row[0] for row in db.query(Cart.id).filter(Cart.user_id == user.id).all()]
        if cart_ids:
            db.query(CartItem).filter(CartItem.cart_id.in_(cart_ids)).delete(synchronize_session=False)
            db.query(Cart).filter(Cart.id.in_(cart_ids)).delete(synchronize_session=False)

        db.query(User).filter(User.id == user.id).delete(synchronize_session=False)
        db.commit()
    except Exception:
        # Any failure anywhere above leaves the account fully intact rather
        # than half-deleted with dangling orders or a broken balance.
        db.rollback()
        raise


def update_user_by_admin(db: Session, user: User, payload: UserUpdateByAdmin, actor: User) -> User:
    _assert_can_manage_target(user, actor)
    if payload.role is not None and payload.role != user.role:
        _assert_can_assign_role(payload.role, actor)
        if user.role == UserRole.SUPER_ADMIN:
            raise _forbidden("The Super Admin role cannot be changed")
    # Deactivating the Super Admin — including by the Super Admin themselves —
    # would lock the protected account out of the app, since a deactivated
    # account cannot log in. There must always be a reachable Super Admin.
    if payload.is_active is False and user.role == UserRole.SUPER_ADMIN:
        raise _forbidden("The Super Admin account cannot be deactivated")

    if payload.email is not None and payload.email != user.email:
        if UserRepository(db).get_by_email_excluding(payload.email, user.id) is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        user.email = payload.email
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active

    db.commit()
    db.refresh(user)
    return user


def update_own_profile(db: Session, user: User, payload: UserUpdateProfile) -> User:
    if payload.username is not None and payload.username != user.username:
        if UserRepository(db).get_by_username_excluding(payload.username, user.id) is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")
        user.username = payload.username
    if payload.full_name is not None:
        user.full_name = payload.full_name

    db.commit()
    db.refresh(user)
    return user


def change_own_password(db: Session, user: User, payload: ChangePasswordRequest) -> None:
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    user.hashed_password = hash_password(payload.new_password)
    # Invalidate any other outstanding sessions for this account — see the
    # token_version comment on the User model.
    user.token_version += 1
    db.commit()


def admin_reset_password(db: Session, user: User, new_password: str, actor: User) -> None:
    # Resetting a password is an account takeover, so it obeys the same
    # who-may-touch-whom rule as any other admin edit.
    _assert_can_manage_target(user, actor)
    user.hashed_password = hash_password(new_password)
    user.token_version += 1
    db.commit()
