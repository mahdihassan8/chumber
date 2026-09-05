import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    balance: float
    avatar_url: str | None
    created_at: datetime


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=8, max_length=100)
    role: UserRole = UserRole.CUSTOMER


class UserUpdateByAdmin(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    email: EmailStr | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserUpdateProfile(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    username: str | None = Field(default=None, min_length=3, max_length=50)


class AvatarSelectRequest(BaseModel):
    avatar_url: str


class AddBalanceRequest(BaseModel):
    # Amount in IQD. allow_inf_nan=False matters: JSON technically allows
    # number literals like 1e400 that overflow a double to +inf, and Python's
    # json module accepts the literal tokens Infinity/NaN outright. Without
    # this, either would sail past `gt=0` (inf > 0 is True) and get added
    # straight onto a user's balance. le=10_000_000 is a sane per-recharge cap
    # for this app, well under what the DB column (NUMERIC(12,2)) can actually
    # hold, so a fat-fingered or malicious huge amount fails clean validation
    # instead of a DB-level numeric overflow error. multiple_of=250 keeps every
    # balance change a whole number of Beans (250 IQD = 1 Bean), so a customer
    # never sees their balance rounded to something they weren't given; 250 is
    # an integer and therefore exactly representable in binary floating point,
    # so there's no precision-tolerance edge case to worry about.
    amount: float = Field(gt=0, le=10_000_000, allow_inf_nan=False, multiple_of=250)
    description: str | None = Field(default=None, max_length=500)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=100)


class AdminResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=100)


class MessageResponse(BaseModel):
    message: str
