import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import (
    CouponAppliesTo,
    CouponDiscountType,
    TenantScopedModel,
)
from app.shared.types import GUID


class Coupon(TenantScopedModel):
    __tablename__ = "coupons"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_coupons_tenant_code"),
    )

    store_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("stores.id", ondelete="SET NULL"), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    discount_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CouponDiscountType.PERCENTAGE.value
    )
    discount_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    min_order_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    max_discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    usage_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_limit_per_customer: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    applies_to: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CouponAppliesTo.ALL.value
    )
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    usages: Mapped[list["CouponUsage"]] = relationship(
        back_populates="coupon", cascade="all, delete-orphan"
    )


class CouponUsage(TenantScopedModel):
    __tablename__ = "coupon_usages"

    coupon_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("coupons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reference_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    reference_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    coupon: Mapped["Coupon"] = relationship(back_populates="usages", lazy="selectin")
