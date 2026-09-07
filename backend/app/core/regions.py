"""Region isolation rules, in one place.

Two concepts that must never be confused:

- **Allowed regions** — which regions an account may use at all. Stored as
  UserRegion rows. A user has one or two; an Admin exactly one; a Super Admin
  both (it is global, so it is a member of everything).
- **Current region** — the one region a given request is operating in. Supplied
  by the client via the `X-Region` header and *always* validated against the
  allowed set here, so a forged header buys nothing.

Every region-scoped read and write derives its scope from `current_region`, and
every by-id fetch goes through `assert_can_access`, which raises 404 rather than
403 so that probing ids cannot reveal that a resource exists in the other
region.
"""

from fastapi import Depends, Header, HTTPException, status

from app.core.deps import get_current_user
from app.models.user import Region, User, UserRole


def is_super_admin(actor: User) -> bool:
    return actor.role == UserRole.SUPER_ADMIN


def allowed_regions(actor: User) -> list[Region]:
    """A Super Admin is global — it can act in either region regardless of the
    membership rows it happens to hold."""
    if is_super_admin(actor):
        return [Region.BAGHDAD, Region.NAJAF]
    return actor.regions


def can_use(actor: User, region: Region) -> bool:
    return region in allowed_regions(actor)


def resolve_current_region(actor: User, requested: str | None) -> Region:
    """The region this request operates in.

    Falls back to the account's only region when nothing is requested, which is
    what keeps single-region clients working without sending a header at all. A
    requested region the account does not hold is rejected outright rather than
    silently downgraded — a caller asking for Baghdad must never quietly get
    Najaf data back.
    """
    permitted = allowed_regions(actor)
    if not permitted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has no region assigned yet — ask a Super Admin to assign one",
        )

    if requested is None or requested == "":
        return permitted[0]

    try:
        region = Region(requested.strip().lower())
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown region '{requested}'")

    if region not in permitted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to that region")
    return region


def get_current_region(
    current_user: User = Depends(get_current_user),
    x_region: str | None = Header(default=None, alias="X-Region"),
) -> Region:
    """FastAPI dependency: the validated current region for this request."""
    return resolve_current_region(current_user, x_region)


def can_access(actor: User, resource_region: Region | None, current: Region) -> bool:
    """A resource is reachable only from inside its own region, and only if the
    actor may use that region at all. Note this is deliberately stricter than
    "actor is allowed the resource's region": a dual-region user viewing Najaf
    must not reach Baghdad rows in the same breath, or the two datasets would
    bleed together on one screen."""
    # A Super Admin is global: it reaches either region's rows regardless of
    # which region the request nominated, and is the only role that can see a
    # region-less legacy row.
    if is_super_admin(actor):
        return True
    if resource_region is None:
        return False
    return resource_region == current and can_use(actor, resource_region)


def assert_can_access(actor: User, resource_region: Region | None, current: Region, *, what: str = "Resource") -> None:
    if not can_access(actor, resource_region, current):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{what} not found")


def region_for_new_resource(actor: User, current: Region) -> Region:
    """Where a newly created resource lands: always the caller's current region,
    never a region named in the request body. A Najaf admin cannot create
    Baghdad stock by sending {"region": "baghdad"}."""
    if not can_use(actor, current):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to that region")
    return current


def resolve_admin_scope(actor: User, requested: str | None) -> Region | None:
    """Which slice of data an admin dashboard shows. None means "every region",
    which only a Super Admin can ask for — a regional admin is always pinned to
    their own region no matter what header they send."""
    if is_super_admin(actor):
        if requested is None or requested.strip().lower() in ("", "all"):
            return None
        return resolve_current_region(actor, requested)
    return resolve_current_region(actor, requested)


def get_admin_scope(
    current_user: User = Depends(get_current_user),
    x_region: str | None = Header(default=None, alias="X-Region"),
) -> Region | None:
    return resolve_admin_scope(current_user, x_region)
