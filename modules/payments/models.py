import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import (
    PaymentProviderType,
    PaymentStatus,
    PaymentTransactionStatus,
    TenantScopedModel,
)
from app.shared.types import GUID


class PaymentProvider(TenantScopedModel):
    __tablename__ = "payment_providers"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_payment_providers_tenant_code"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    provider_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default=PaymentProviderType.CASH.value
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    supports_pos: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    supports_online: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    merchant_methods: Mapped[list["MerchantPaymentMethod"]] = relationship(
        back_populates="provider", cascade="all, delete-orphan"
    )


class MerchantPaymentMethod(TenantScopedModel):
    __tablename__ = "merchant_payment_methods"

    provider_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("payment_providers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    store_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("stores.id", ondelete="SET NULL"), nullable=True, index=True
    )
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    settings: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    provider: Mapped["PaymentProvider"] = relationship(
        back_populates="merchant_methods", lazy="selectin"
    )


class Payment(TenantScopedModel):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "payment_number", name="uq_payments_tenant_number"),
    )

    payment_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    reference_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    reference_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    store_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("stores.id", ondelete="SET NULL"), nullable=True, index=True
    )
    currency: Mapped[str] = mapped_column(String(3), default="KES", nullable=False)
    amount_due: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PaymentStatus.PENDING.value
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    transactions: Mapped[list["PaymentTransaction"]] = relationship(
        back_populates="payment", cascade="all, delete-orphan", lazy="selectin"
    )


class PaymentTransaction(TenantScopedModel):
    __tablename__ = "payment_transactions"

    payment_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    merchant_method_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("merchant_payment_methods.id", ondelete="SET NULL"), nullable=True, index=True
    )
    method_type: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PaymentTransactionStatus.PENDING.value
    )
    external_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    payment: Mapped["Payment"] = relationship(back_populates="transactions")
