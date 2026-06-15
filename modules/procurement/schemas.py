from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import EmailStr, Field

from app.shared.schemas import BaseSchema


# --- Supplier ---

class SupplierCreate(BaseSchema):
    name: str = Field(min_length=2, max_length=200)
    code: str = Field(min_length=2, max_length=50, pattern=r"^[A-Z0-9_-]+$")
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    contact_person: str | None = Field(default=None, max_length=150)
    address_line1: str | None = Field(default=None, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    payment_terms: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)
    is_active: bool = True


class SupplierUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    contact_person: str | None = Field(default=None, max_length=150)
    address_line1: str | None = Field(default=None, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    payment_terms: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class SupplierResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    name: str
    code: str
    email: str | None
    phone: str | None
    contact_person: str | None
    address_line1: str | None
    address_line2: str | None
    city: str | None
    state: str | None
    postal_code: str | None
    country: str | None
    payment_terms: str | None
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# --- Purchase Order ---

class PurchaseOrderItemCreate(BaseSchema):
    product_variant_id: UUID
    quantity_ordered: int = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100)


class PurchaseOrderCreate(BaseSchema):
    supplier_id: UUID
    branch_id: UUID
    order_date: date | None = None
    expected_delivery_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)
    items: list[PurchaseOrderItemCreate] = Field(min_length=1)


class PurchaseOrderItemResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    purchase_order_id: UUID
    product_variant_id: UUID
    quantity_ordered: int
    quantity_received: int
    unit_cost: Decimal
    tax_rate: Decimal
    line_total: Decimal
    quantity_remaining: int = 0


class PurchaseOrderResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    po_number: str
    supplier_id: UUID
    branch_id: UUID
    status: str
    order_date: date
    expected_delivery_date: date | None
    notes: str | None
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    created_by: UUID | None
    approved_by: UUID | None
    approved_at: datetime | None
    received_at: datetime | None
    items: list[PurchaseOrderItemResponse] = []
    supplier: SupplierResponse | None = None
    created_at: datetime
    updated_at: datetime


class ReceivePurchaseOrderItem(BaseSchema):
    item_id: UUID
    quantity: int = Field(gt=0)


class ReceivePurchaseOrderRequest(BaseSchema):
    items: list[ReceivePurchaseOrderItem] = Field(min_length=1)
