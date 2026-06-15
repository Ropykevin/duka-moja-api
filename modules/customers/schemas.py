from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import EmailStr, Field

from app.shared.base_model import CustomerStatus, LoyaltyTier
from app.shared.schemas import BaseSchema


# --- Customer ---

class CustomerCreate(BaseSchema):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    company_name: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)


class CustomerUpdate(BaseSchema):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    company_name: str | None = Field(default=None, max_length=200)
    status: CustomerStatus | None = None
    notes: str | None = Field(default=None, max_length=2000)


class CustomerResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    email: str | None
    phone: str | None
    first_name: str
    last_name: str
    company_name: str | None
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime


class CustomerAddressCreate(BaseSchema):
    label: str = Field(default="Home", max_length=50)
    address_line1: str = Field(min_length=1, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=1, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str = Field(min_length=2, max_length=2)
    phone: str | None = Field(default=None, max_length=20)
    is_default_shipping: bool = False
    is_default_billing: bool = False


class CustomerAddressResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    label: str
    address_line1: str
    address_line2: str | None
    city: str
    state: str | None
    postal_code: str | None
    country: str
    phone: str | None
    is_default_shipping: bool
    is_default_billing: bool


class LoyaltyAccountResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    points_balance: int
    lifetime_points: int
    tier: str
    enrolled_at: datetime


class CustomerDetailResponse(CustomerResponse):
    addresses: list[CustomerAddressResponse] = []
    loyalty_account: LoyaltyAccountResponse | None = None


# --- Cart ---

class CartItemAdd(BaseSchema):
    product_variant_id: UUID
    quantity: int = Field(default=1, ge=1)


class CartItemUpdate(BaseSchema):
    quantity: int = Field(ge=1)


class CartItemResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    cart_id: UUID
    product_variant_id: UUID
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class CartResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    customer_id: UUID | None
    branch_id: UUID | None
    store_id: UUID | None
    status: str
    items: list[CartItemResponse] = []
    subtotal: Decimal = Decimal("0")
    item_count: int = 0


# --- Order ---

class CheckoutRequest(BaseSchema):
    customer_id: UUID
    branch_id: UUID
    cart_id: UUID
    shipping_address_id: UUID | None = None
    billing_address_id: UUID | None = None
    shipping_amount: Decimal = Field(default=Decimal("0"), ge=0)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0)
    notes: str | None = Field(default=None, max_length=2000)


class OrderItemResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    order_id: UUID
    product_variant_id: UUID
    product_name: str
    sku: str
    quantity: int
    unit_price: Decimal
    tax_rate: Decimal
    line_total: Decimal


class OrderResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    order_number: str
    customer_id: UUID
    branch_id: UUID
    store_id: UUID | None
    cart_id: UUID | None
    status: str
    payment_status: str
    subtotal: Decimal
    tax_amount: Decimal
    shipping_amount: Decimal
    discount_amount: Decimal
    total: Decimal
    shipping_address_id: UUID | None
    billing_address_id: UUID | None
    notes: str | None
    confirmed_at: datetime | None
    items: list[OrderItemResponse] = []
    created_at: datetime
    updated_at: datetime


class OrderDetailResponse(OrderResponse):
    customer: CustomerResponse | None = None
