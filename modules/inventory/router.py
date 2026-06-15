from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db, require_authenticated_user
from app.modules.inventory.schemas import (
    InventoryMovementResponse,
    InventoryResponse,
    ReceiveStockCreate,
    StockAdjustmentCreate,
    StockTransferCreate,
    StockTransferReceiveRequest,
    StockTransferResponse,
    StockTransferShipRequest,
)
from app.modules.inventory.service import InventoryService, StockTransferService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/inventory", tags=["Inventory"])


def get_inventory_service(session: AsyncSession = Depends(get_db)) -> InventoryService:
    return InventoryService(session)


def get_transfer_service(session: AsyncSession = Depends(get_db)) -> StockTransferService:
    return StockTransferService(session)


@router.get("", response_model=PaginatedResponse[InventoryResponse])
async def list_inventory(
    branch_id: UUID = Query(..., description="Branch to list stock for"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: InventoryService = Depends(get_inventory_service),
) -> PaginatedResponse[InventoryResponse]:
    """List stock levels for a branch."""
    return await service.list_stock(tenant_id, branch_id, page=page, page_size=page_size)


@router.get("/stock", response_model=InventoryResponse)
async def get_stock_level(
    branch_id: UUID = Query(...),
    product_variant_id: UUID = Query(...),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: InventoryService = Depends(get_inventory_service),
) -> InventoryResponse:
    """Get stock level for a specific variant at a branch."""
    return await service.get_stock(tenant_id, branch_id, product_variant_id)


@router.get("/movements", response_model=PaginatedResponse[InventoryMovementResponse])
async def list_movements(
    branch_id: UUID | None = Query(default=None),
    product_variant_id: UUID | None = Query(default=None),
    movement_source: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: InventoryService = Depends(get_inventory_service),
) -> PaginatedResponse[InventoryMovementResponse]:
    """List inventory movement history (audit trail)."""
    return await service.list_movements(
        tenant_id,
        branch_id=branch_id,
        product_variant_id=product_variant_id,
        movement_source=movement_source,
        page=page,
        page_size=page_size,
    )


@router.post("/adjustments", response_model=InventoryMovementResponse, status_code=201)
async def adjust_stock(
    data: StockAdjustmentCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: InventoryService = Depends(get_inventory_service),
) -> InventoryMovementResponse:
    """Manual stock adjustment. Creates an InventoryMovement record."""
    return await service.adjust_stock(tenant_id, data, created_by=user_id)


@router.post("/receive", response_model=InventoryMovementResponse, status_code=201)
async def receive_stock(
    data: ReceiveStockCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: InventoryService = Depends(get_inventory_service),
) -> InventoryMovementResponse:
    """Receive inbound stock (e.g. from purchase order)."""
    return await service.receive_stock(tenant_id, data, created_by=user_id)


# --- Stock Transfers ---

@router.post("/transfers", response_model=StockTransferResponse, status_code=201)
async def create_transfer(
    data: StockTransferCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: StockTransferService = Depends(get_transfer_service),
) -> StockTransferResponse:
    """Create a draft stock transfer between branches."""
    return await service.create(tenant_id, data, requested_by=user_id)


@router.get("/transfers", response_model=PaginatedResponse[StockTransferResponse])
async def list_transfers(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: StockTransferService = Depends(get_transfer_service),
) -> PaginatedResponse[StockTransferResponse]:
    """List stock transfers."""
    return await service.list(tenant_id, status=status, page=page, page_size=page_size)


@router.get("/transfers/{transfer_id}", response_model=StockTransferResponse)
async def get_transfer(
    transfer_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: StockTransferService = Depends(get_transfer_service),
) -> StockTransferResponse:
    """Get stock transfer details."""
    return await service.get(tenant_id, transfer_id)


@router.post("/transfers/{transfer_id}/submit", response_model=StockTransferResponse)
async def submit_transfer(
    transfer_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: StockTransferService = Depends(get_transfer_service),
) -> StockTransferResponse:
    """Submit transfer for approval."""
    return await service.submit(tenant_id, transfer_id)


@router.post("/transfers/{transfer_id}/approve", response_model=StockTransferResponse)
async def approve_transfer(
    transfer_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: StockTransferService = Depends(get_transfer_service),
) -> StockTransferResponse:
    """Approve a pending transfer."""
    return await service.approve(tenant_id, transfer_id, approved_by=user_id)


@router.post("/transfers/{transfer_id}/ship", response_model=StockTransferResponse)
async def ship_transfer(
    transfer_id: UUID,
    data: StockTransferShipRequest | None = None,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: StockTransferService = Depends(get_transfer_service),
) -> StockTransferResponse:
    """Ship transfer — deducts stock from source branch via InventoryMovement."""
    return await service.ship(tenant_id, transfer_id, data, created_by=user_id)


@router.post("/transfers/{transfer_id}/receive", response_model=StockTransferResponse)
async def receive_transfer(
    transfer_id: UUID,
    data: StockTransferReceiveRequest | None = None,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: StockTransferService = Depends(get_transfer_service),
) -> StockTransferResponse:
    """Receive transfer — adds stock to destination branch via InventoryMovement."""
    return await service.receive(tenant_id, transfer_id, data, created_by=user_id)


@router.post("/transfers/{transfer_id}/cancel", response_model=StockTransferResponse)
async def cancel_transfer(
    transfer_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: StockTransferService = Depends(get_transfer_service),
) -> StockTransferResponse:
    """Cancel a draft, pending, or approved transfer."""
    return await service.cancel(tenant_id, transfer_id)
