from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.shared.base_model import ReturnReferenceType
from app.shared.schemas import BaseSchema


class ReturnItemCreate(BaseSchema):
    source_item_id: UUID
    quantity: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=255)


class ReturnItemApprove(BaseSchema):
    item_id: UUID
    quantity_approved: int = Field(ge=0)


class ReturnItemResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    return_id: UUID
    source_item_id: UUID
    product_variant_id: UUID
    product_name: str
    sku: str
    quantity_requested: int
    quantity_approved: int
    unit_price: Decimal
    line_refund: Decimal
    reason: str | None


class ReturnCreate(BaseSchema):
    reference_type: ReturnReferenceType
    reference_id: UUID
    items: list[ReturnItemCreate] = Field(min_length=1)
    reason: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)


class ReturnApproveRequest(BaseSchema):
    items: list[ReturnItemApprove] | None = None
    notes: str | None = Field(default=None, max_length=2000)


class ReturnResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    return_number: str
    reference_type: str
    reference_id: UUID
    customer_id: UUID | None
    branch_id: UUID
    store_id: UUID | None
    status: str
    reason: str | None
    notes: str | None
    refund_amount: Decimal
    requested_by: UUID | None
    approved_by: UUID | None
    requested_at: datetime
    approved_at: datetime | None
    received_at: datetime | None
    refunded_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ReturnDetailResponse(ReturnResponse):
    items: list[ReturnItemResponse] = []
