import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import InventoryMovementSource, StockTransferStatus, TenantScopedModel
from app.shared.types import GUID


class Inventory(TenantScopedModel):
    __tablename__ = "inventory"
    __table_args__ = (
        UniqueConstraint(
            "branch_id", "product_variant_id", name="uq_inventory_branch_variant"
        ),
    )

    branch_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quantity_on_hand: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity_reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    @property
    def quantity_available(self) -> int:
        return max(0, self.quantity_on_hand - self.quantity_reserved)


class InventoryMovement(TenantScopedModel):
    __tablename__ = "inventory_movements"

    branch_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    movement_source: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_before: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)


class StockTransfer(TenantScopedModel):
    __tablename__ = "stock_transfers"
    __table_args__ = (
        UniqueConstraint("tenant_id", "transfer_number", name="uq_stock_transfers_number"),
    )

    transfer_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    from_branch_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    to_branch_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=StockTransferStatus.DRAFT.value
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["StockTransferItem"]] = relationship(
        back_populates="transfer", cascade="all, delete-orphan", lazy="selectin"
    )


class StockTransferItem(TenantScopedModel):
    __tablename__ = "stock_transfer_items"

    transfer_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("stock_transfers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity_requested: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_shipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity_received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    transfer: Mapped["StockTransfer"] = relationship(back_populates="items")
