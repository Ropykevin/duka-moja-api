from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from app.shared.schemas import BaseSchema


class UserCreate(BaseSchema):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)


class UserResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    email: str
    first_name: str
    last_name: str
    phone: str | None
    status: str
    is_superuser: bool
    is_tenant_owner: bool
    email_verified_at: datetime | None
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RoleResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    is_system: bool


class PermissionResponse(BaseSchema):
    id: UUID
    code: str
    name: str
    description: str | None
    module: str


class RegisterRequest(BaseSchema):
    tenant_name: str = Field(min_length=2, max_length=200)
    tenant_slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    tenant_email: EmailStr
    tenant_phone: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    timezone: str = Field(default="UTC", max_length=50)
    owner: UserCreate


class LoginRequest(BaseSchema):
    email: EmailStr
    password: str
    tenant_slug: str | None = None


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseSchema):
    refresh_token: str


class RegisterResponse(BaseSchema):
    tenant_id: UUID
    user: UserResponse
    tokens: TokenResponse
