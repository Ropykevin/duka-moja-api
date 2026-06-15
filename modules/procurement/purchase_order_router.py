from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db, require_authenticated_user
from app.modules.procurement.schemas import (
    PurchaseOrderCreate,
    PurchaseOrderResponse,
    ReceivePurchaseOrderRequest,
)
from app.modules.procurement.service import PurchaseOrderService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/purchase-orders", tags=["Purchase Orders"])


def get_service(session: AsyncSession = Depends(get_db)) -> PurchaseOrderService:
    return PurchaseOrderService(session)


@router.post("", response_model=PurchaseOrderResponse, status_code=201)
async def create_purchase_order(
    data: PurchaseOrderCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: PurchaseOrderService = Depends(get_service),
) -> PurchaseOrderResponse:
    return await service.create(tenant_id, data, created_by=user_id)


@router.get("", response_model=PaginatedResponse[PurchaseOrderResponse])
async def list_purchase_orders(
    supplier_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: PurchaseOrderService = Depends(get_service),
) -> PaginatedResponse[PurchaseOrderResponse]:
    return await service.list(
        tenant_id, supplier_id=supplier_id, status=status, page=page, page_size=page_size
    )


@router.get("/{po_id}", response_model=PurchaseOrderResponse)
async def get_purchase_order(
    po_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: PurchaseOrderService = Depends(get_service),
) -> PurchaseOrderResponse:
    return await service.get(tenant_id, po_id)


@router.post("/{po_id}/submit", response_model=PurchaseOrderResponse)
async def submit_purchase_order(
    po_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: PurchaseOrderService = Depends(get_service),
) -> PurchaseOrderResponse:
    return await service.submit(tenant_id, po_id)


@router.post("/{po_id}/approve", response_model=PurchaseOrderResponse)
async def approve_purchase_order(
    po_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: PurchaseOrderService = Depends(get_service),
) -> PurchaseOrderResponse:
    return await service.approve(tenant_id, po_id, approved_by=user_id)


@router.post("/{po_id}/receive", response_model=PurchaseOrderResponse)
async def receive_purchase_order(
    po_id: UUID,
    data: ReceivePurchaseOrderRequest,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: PurchaseOrderService = Depends(get_service),
) -> PurchaseOrderResponse:
    """Receive goods — creates InventoryMovement records and updates stock."""
    return await service.receive(tenant_id, po_id, data, received_by=user_id)


@router.post("/{po_id}/cancel", response_model=PurchaseOrderResponse)
async def cancel_purchase_order(
    po_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: PurchaseOrderService = Depends(get_service),
) -> PurchaseOrderResponse:
    return await service.cancel(tenant_id, po_id)
