from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.shared.schemas import BaseSchema


# --- Cash Register ---

class CashRegisterCreate(BaseSchema):
    branch_id: UUID
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=50)


class CashRegisterUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    status: str | None = Field(default=None, max_length=20)


class CashRegisterResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    branch_id: UUID
    name: str
    code: str
    status: str
    created_at: datetime
    updated_at: datetime


# --- Cash Session ---

class CashSessionOpen(BaseSchema):
    register_id: UUID
    opening_balance: Decimal = Field(default=Decimal("0"), ge=0)


class CashSessionClose(BaseSchema):
    closing_balance: Decimal = Field(ge=0)
    notes: str | None = Field(default=None, max_length=2000)


class CashSessionResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    register_id: UUID
    branch_id: UUID
    opened_by: UUID
    closed_by: UUID | None
    status: str
    opening_balance: Decimal
    closing_balance: Decimal | None
    expected_cash: Decimal | None
    cash_difference: Decimal | None
    total_sales: Decimal
    total_refunds: Decimal
    sale_count: int
    opened_at: datetime
    closed_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


# --- Sale ---

class SaleItemCreate(BaseSchema):
    product_variant_id: UUID
    quantity: int = Field(default=1, ge=1)
    unit_price: Decimal | None = Field(default=None, ge=0)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0)


class SaleItemResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    sale_id: UUID
    product_variant_id: UUID
    product_name: str
    sku: str
    quantity: int
    unit_price: Decimal
    tax_rate: Decimal
    discount_amount: Decimal
    line_total: Decimal


class SaleCreate(BaseSchema):
    session_id: UUID
    customer_id: UUID | None = None
    items: list[SaleItemCreate] = Field(min_length=1)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0)
    notes: str | None = Field(default=None, max_length=2000)


class SaleItemAdd(BaseSchema):
    product_variant_id: UUID
    quantity: int = Field(default=1, ge=1)
    unit_price: Decimal | None = Field(default=None, ge=0)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0)


class SaleComplete(BaseSchema):
    amount_paid: Decimal | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=2000)


class SaleResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    sale_number: str
    session_id: UUID
    register_id: UUID
    branch_id: UUID
    store_id: UUID | None
    customer_id: UUID | None
    cashier_id: UUID
    status: str
    payment_status: str
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total: Decimal
    amount_paid: Decimal
    notes: str | None
    completed_at: datetime | None
    voided_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SaleDetailResponse(SaleResponse):
    items: list[SaleItemResponse] = []
