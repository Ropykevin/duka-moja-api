from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.shared.base_model import PaymentProviderType, PaymentReferenceType
from app.shared.schemas import BaseSchema


# --- Payment Provider ---

class PaymentProviderCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9_-]+$")
    provider_type: PaymentProviderType
    description: str | None = Field(default=None, max_length=2000)
    supports_pos: bool = True
    supports_online: bool = False


class PaymentProviderUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    supports_pos: bool | None = None
    supports_online: bool | None = None
    is_active: bool | None = None


class PaymentProviderResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    name: str
    code: str
    provider_type: str
    description: str | None
    supports_pos: bool
    supports_online: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


# --- Merchant Payment Method ---

class MerchantPaymentMethodCreate(BaseSchema):
    provider_id: UUID
    store_id: UUID | None = None
    display_name: str = Field(min_length=1, max_length=100)
    settings: dict | None = None
    is_default: bool = False
    sort_order: int = 0


class MerchantPaymentMethodUpdate(BaseSchema):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    settings: dict | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    sort_order: int | None = None


class MerchantPaymentMethodResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    provider_id: UUID
    store_id: UUID | None
    display_name: str
    settings: dict | None
    is_active: bool
    is_default: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


# --- Payment ---

class PaymentTransactionCreate(BaseSchema):
    merchant_method_id: UUID | None = None
    method_type: str = Field(min_length=1, max_length=30)
    amount: Decimal = Field(gt=0)
    external_reference: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)
    complete: bool = True


class PaymentCreate(BaseSchema):
    reference_type: PaymentReferenceType
    reference_id: UUID
    notes: str | None = Field(default=None, max_length=2000)


class PaymentProcessRequest(BaseSchema):
    transactions: list[PaymentTransactionCreate] = Field(min_length=1)


class PaymentTransactionResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    payment_id: UUID
    merchant_method_id: UUID | None
    method_type: str
    amount: Decimal
    status: str
    external_reference: str | None
    notes: str | None
    processed_at: datetime | None
    processed_by: UUID | None
    created_at: datetime
    updated_at: datetime


class PaymentResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    payment_number: str
    reference_type: str
    reference_id: UUID
    customer_id: UUID | None
    store_id: UUID | None
    currency: str
    amount_due: Decimal
    amount_paid: Decimal
    status: str
    notes: str | None
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PaymentDetailResponse(PaymentResponse):
    transactions: list[PaymentTransactionResponse] = []
