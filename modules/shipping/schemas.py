from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.shared.base_model import ShippingMethodType
from app.shared.schemas import BaseSchema


# --- Shipping Method ---

class ShippingMethodCreate(BaseSchema):
    store_id: UUID | None = None
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9_-]+$")
    method_type: ShippingMethodType = ShippingMethodType.FLAT_RATE
    carrier_name: str | None = Field(default=None, max_length=100)
    base_cost: Decimal = Field(default=Decimal("0"), ge=0)
    free_shipping_threshold: Decimal | None = Field(default=None, ge=0)
    estimated_days_min: int | None = Field(default=None, ge=0)
    estimated_days_max: int | None = Field(default=None, ge=0)
    sort_order: int = 0


class ShippingMethodUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    carrier_name: str | None = Field(default=None, max_length=100)
    base_cost: Decimal | None = Field(default=None, ge=0)
    free_shipping_threshold: Decimal | None = Field(default=None, ge=0)
    estimated_days_min: int | None = Field(default=None, ge=0)
    estimated_days_max: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    sort_order: int | None = None


class ShippingMethodResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    store_id: UUID | None
    name: str
    code: str
    method_type: str
    carrier_name: str | None
    base_cost: Decimal
    free_shipping_threshold: Decimal | None
    estimated_days_min: int | None
    estimated_days_max: int | None
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


# --- Shipment ---

class ShipmentCreate(BaseSchema):
    order_id: UUID
    shipping_method_id: UUID
    shipping_address_id: UUID | None = None
    tracking_number: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)


class ShipmentShip(BaseSchema):
    tracking_number: str | None = Field(default=None, max_length=100)
    carrier_name: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)


class ShipmentDeliver(BaseSchema):
    notes: str | None = Field(default=None, max_length=2000)


class ShipmentResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    shipment_number: str
    order_id: UUID
    shipping_method_id: UUID
    shipping_address_id: UUID | None
    status: str
    tracking_number: str | None
    carrier_name: str | None
    shipping_cost: Decimal
    notes: str | None
    shipped_at: datetime | None
    delivered_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ShipmentDetailResponse(ShipmentResponse):
    shipping_method: ShippingMethodResponse | None = None
