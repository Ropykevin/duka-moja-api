import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import ReturnStatus, TenantScopedModel
from app.shared.types import GUID


class Return(TenantScopedModel):
    __tablename__ = "returns"
    __table_args__ = (
        UniqueConstraint("tenant_id", "return_number", name="uq_returns_tenant_number"),
    )

    return_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    reference_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    reference_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    store_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("stores.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ReturnStatus.REQUESTED.value
    )
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    refund_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["ReturnItem"]] = relationship(
        back_populates="return_record", cascade="all, delete-orphan", lazy="selectin"
    )


class ReturnItem(TenantScopedModel):
    __tablename__ = "return_items"

    return_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("returns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_item_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity_requested: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_approved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_refund: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    return_record: Mapped["Return"] = relationship(back_populates="items")
