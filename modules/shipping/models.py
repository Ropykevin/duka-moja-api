import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import ShipmentStatus, ShippingMethodType, TenantScopedModel
from app.shared.types import GUID


class ShippingMethod(TenantScopedModel):
    __tablename__ = "shipping_methods"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_shipping_methods_tenant_code"),
    )

    store_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("stores.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    method_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ShippingMethodType.FLAT_RATE.value
    )
    carrier_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    base_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    free_shipping_threshold: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    estimated_days_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_days_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    shipments: Mapped[list["Shipment"]] = relationship(back_populates="shipping_method")


class Shipment(TenantScopedModel):
    __tablename__ = "shipments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "shipment_number", name="uq_shipments_tenant_number"),
    )

    shipment_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    shipping_method_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("shipping_methods.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    shipping_address_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("customer_addresses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ShipmentStatus.PENDING.value
    )
    tracking_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    carrier_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    shipping_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    shipping_method: Mapped["ShippingMethod"] = relationship(
        back_populates="shipments", lazy="selectin"
    )
