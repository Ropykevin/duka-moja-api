from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.shared.base_model import InventoryMovementSource, StockTransferStatus
from app.shared.schemas import BaseSchema


# --- Inventory ---

class InventoryResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    branch_id: UUID
    product_variant_id: UUID
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int
    created_at: datetime
    updated_at: datetime


class InventoryMovementResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    branch_id: UUID
    product_variant_id: UUID
    movement_source: str
    quantity: int
    quantity_before: int
    quantity_after: int
    reference_type: str | None
    reference_id: UUID | None
    notes: str | None
    created_by: UUID | None
    created_at: datetime


class StockAdjustmentCreate(BaseSchema):
    branch_id: UUID
    product_variant_id: UUID
    quantity: int = Field(description="Positive to add stock, negative to remove")
    notes: str = Field(min_length=1, max_length=1000)


class ReceiveStockCreate(BaseSchema):
    """Inbound stock (e.g. from purchase order — PO module hooks in later phases)."""
    branch_id: UUID
    product_variant_id: UUID
    quantity: int = Field(gt=0)
    reference_type: str | None = Field(default=None, max_length=50)
    reference_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=1000)


# --- Stock Transfer ---

class StockTransferItemCreate(BaseSchema):
    product_variant_id: UUID
    quantity_requested: int = Field(gt=0)


class StockTransferCreate(BaseSchema):
    from_branch_id: UUID
    to_branch_id: UUID
    notes: str | None = Field(default=None, max_length=2000)
    items: list[StockTransferItemCreate] = Field(min_length=1)


class StockTransferItemResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    transfer_id: UUID
    product_variant_id: UUID
    quantity_requested: int
    quantity_shipped: int
    quantity_received: int


class StockTransferResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    transfer_number: str
    from_branch_id: UUID
    to_branch_id: UUID
    status: str
    notes: str | None
    requested_by: UUID | None
    approved_by: UUID | None
    approved_at: datetime | None
    shipped_at: datetime | None
    received_at: datetime | None
    items: list[StockTransferItemResponse] = []
    created_at: datetime
    updated_at: datetime


class StockTransferShipRequest(BaseSchema):
    items: list["StockTransferShipItem"] | None = None


class StockTransferShipItem(BaseSchema):
    item_id: UUID
    quantity_shipped: int = Field(gt=0)


class StockTransferReceiveRequest(BaseSchema):
    items: list["StockTransferReceiveItem"] | None = None


class StockTransferReceiveItem(BaseSchema):
    item_id: UUID
    quantity_received: int = Field(gt=0)


StockTransferShipRequest.model_rebuild()
StockTransferReceiveRequest.model_rebuild()
