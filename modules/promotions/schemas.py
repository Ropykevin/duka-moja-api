from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.shared.base_model import CouponAppliesTo, CouponDiscountType, CouponUsageReferenceType
from app.shared.schemas import BaseSchema


class CouponCreate(BaseSchema):
    store_id: UUID | None = None
    code: str = Field(min_length=2, max_length=50, pattern=r"^[A-Z0-9_-]+$")
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    discount_type: CouponDiscountType
    discount_value: Decimal = Field(gt=0)
    min_order_amount: Decimal | None = Field(default=None, ge=0)
    max_discount_amount: Decimal | None = Field(default=None, ge=0)
    usage_limit: int | None = Field(default=None, ge=1)
    usage_limit_per_customer: int | None = Field(default=None, ge=1)
    applies_to: CouponAppliesTo = CouponAppliesTo.ALL
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class CouponUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    discount_value: Decimal | None = Field(default=None, gt=0)
    min_order_amount: Decimal | None = Field(default=None, ge=0)
    max_discount_amount: Decimal | None = Field(default=None, ge=0)
    usage_limit: int | None = Field(default=None, ge=1)
    usage_limit_per_customer: int | None = Field(default=None, ge=1)
    applies_to: CouponAppliesTo | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_active: bool | None = None


class CouponResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    store_id: UUID | None
    code: str
    name: str
    description: str | None
    discount_type: str
    discount_value: Decimal
    min_order_amount: Decimal | None
    max_discount_amount: Decimal | None
    usage_limit: int | None
    usage_limit_per_customer: int | None
    used_count: int
    applies_to: str
    starts_at: datetime | None
    ends_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CouponValidateRequest(BaseSchema):
    code: str = Field(min_length=2, max_length=50)
    subtotal: Decimal = Field(ge=0)
    customer_id: UUID | None = None
    applies_to: CouponAppliesTo = CouponAppliesTo.ONLINE


class CouponValidateResponse(BaseSchema):
    coupon_id: UUID
    code: str
    discount_type: str
    discount_amount: Decimal
    message: str


class CouponApplyRequest(BaseSchema):
    code: str = Field(min_length=2, max_length=50)
    reference_type: CouponUsageReferenceType
    reference_id: UUID
    customer_id: UUID | None = None


class CouponApplyResponse(BaseSchema):
    coupon_id: UUID
    code: str
    discount_amount: Decimal
    reference_type: str
    reference_id: UUID
    usage_id: UUID


class CouponUsageResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    coupon_id: UUID
    customer_id: UUID | None
    reference_type: str
    reference_id: UUID
    discount_amount: Decimal
    used_at: datetime
    created_at: datetime
    updated_at: datetime
