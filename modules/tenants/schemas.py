from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import EmailStr, Field

from app.shared.schemas import BaseSchema


class TenantCreate(BaseSchema):
    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    email: EmailStr
    phone: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    timezone: str = Field(default="UTC", max_length=50)


class TenantUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    timezone: str | None = Field(default=None, max_length=50)
    settings: dict | None = None


class TenantResponse(BaseSchema):
    id: UUID
    name: str
    slug: str
    email: str
    phone: str | None
    status: str
    country: str | None
    timezone: str
    settings: dict | None
    created_at: datetime
    updated_at: datetime


class FeatureResponse(BaseSchema):
    id: UUID
    code: str
    name: str
    description: str | None
    module: str


class PlanFeatureResponse(BaseSchema):
    id: UUID
    feature: FeatureResponse
    limit_value: int | None
    is_enabled: bool


class SubscriptionPlanResponse(BaseSchema):
    id: UUID
    name: str
    code: str
    description: str | None
    monthly_price: Decimal
    yearly_price: Decimal
    trial_days: int
    is_active: bool
    sort_order: int
    features: list[PlanFeatureResponse] = []


class SubscriptionResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    plan_id: UUID
    status: str
    billing_cycle: str
    started_at: datetime
    current_period_start: datetime
    current_period_end: datetime
    trial_ends_at: datetime | None
    grace_period_ends_at: datetime | None
    cancelled_at: datetime | None
    suspended_at: datetime | None
    plan: SubscriptionPlanResponse | None = None
    created_at: datetime
    updated_at: datetime
