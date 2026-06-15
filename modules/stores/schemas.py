from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import EmailStr, Field

from app.shared.base_model import BranchStatus, StoreStatus
from app.shared.schemas import BaseSchema


class StoreCreate(BaseSchema):
    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(default=None, max_length=2000)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    currency: str = Field(default="KES", min_length=3, max_length=3)
    timezone: str = Field(default="UTC", max_length=50)
    logo_url: str | None = Field(default=None, max_length=500)
    address_line1: str | None = Field(default=None, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    is_default: bool = False


class StoreUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    status: StoreStatus | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    timezone: str | None = Field(default=None, max_length=50)
    logo_url: str | None = Field(default=None, max_length=500)
    address_line1: str | None = Field(default=None, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    is_default: bool | None = None


class StoreResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    description: str | None
    email: str | None
    phone: str | None
    status: str
    is_default: bool
    currency: str
    timezone: str
    logo_url: str | None
    address_line1: str | None
    address_line2: str | None
    city: str | None
    state: str | None
    postal_code: str | None
    country: str | None
    created_at: datetime
    updated_at: datetime


class BranchCreate(BaseSchema):
    store_id: UUID
    name: str = Field(min_length=2, max_length=200)
    code: str = Field(min_length=2, max_length=50, pattern=r"^[A-Z0-9_-]+$")
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    is_headquarters: bool = False
    address_line1: str | None = Field(default=None, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)


class BranchUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    status: BranchStatus | None = None
    is_headquarters: bool | None = None
    address_line1: str | None = Field(default=None, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)


class BranchResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    store_id: UUID
    name: str
    code: str
    email: str | None
    phone: str | None
    status: str
    is_headquarters: bool
    address_line1: str | None
    address_line2: str | None
    city: str | None
    state: str | None
    postal_code: str | None
    country: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    created_at: datetime
    updated_at: datetime


class StoreSettingsUpdate(BaseSchema):
    tax_rate: Decimal | None = Field(default=None, ge=0, le=100)
    tax_inclusive: bool | None = None
    default_currency: str | None = Field(default=None, min_length=3, max_length=3)
    receipt_header: str | None = Field(default=None, max_length=2000)
    receipt_footer: str | None = Field(default=None, max_length=2000)
    allow_negative_stock: bool | None = None
    low_stock_threshold: int | None = Field(default=None, ge=0)
    date_format: str | None = Field(default=None, max_length=30)
    time_format: str | None = Field(default=None, max_length=30)
    pos_settings: dict | None = None
    ecommerce_settings: dict | None = None
    inventory_settings: dict | None = None
    notification_settings: dict | None = None
    business_hours: dict | None = None


class StoreSettingsResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    store_id: UUID
    tax_rate: Decimal
    tax_inclusive: bool
    default_currency: str
    receipt_header: str | None
    receipt_footer: str | None
    allow_negative_stock: bool
    low_stock_threshold: int
    date_format: str
    time_format: str
    pos_settings: dict | None
    ecommerce_settings: dict | None
    inventory_settings: dict | None
    notification_settings: dict | None
    business_hours: dict | None
    created_at: datetime
    updated_at: datetime


class StoreDetailResponse(StoreResponse):
    settings: StoreSettingsResponse | None = None
    branch_count: int = 0
