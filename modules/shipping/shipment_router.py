from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db
from app.modules.shipping.schemas import (
    ShipmentCreate,
    ShipmentDeliver,
    ShipmentDetailResponse,
    ShipmentResponse,
    ShipmentShip,
)
from app.modules.shipping.service import ShipmentService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/shipments", tags=["Shipments"])


def get_service(session: AsyncSession = Depends(get_db)) -> ShipmentService:
    return ShipmentService(session)


@router.post("", response_model=ShipmentDetailResponse, status_code=201)
async def create_shipment(
    data: ShipmentCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: ShipmentService = Depends(get_service),
) -> ShipmentDetailResponse:
    """Create a shipment for a confirmed order."""
    return await service.create(tenant_id, data)


@router.post("/{shipment_id}/ship", response_model=ShipmentDetailResponse)
async def ship_shipment(
    shipment_id: UUID,
    data: ShipmentShip | None = None,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: ShipmentService = Depends(get_service),
) -> ShipmentDetailResponse:
    """Mark shipment as shipped and update order status."""
    return await service.ship(tenant_id, shipment_id, data)


@router.post("/{shipment_id}/in-transit", response_model=ShipmentDetailResponse)
async def mark_in_transit(
    shipment_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: ShipmentService = Depends(get_service),
) -> ShipmentDetailResponse:
    return await service.mark_in_transit(tenant_id, shipment_id)


@router.post("/{shipment_id}/deliver", response_model=ShipmentDetailResponse)
async def deliver_shipment(
    shipment_id: UUID,
    data: ShipmentDeliver | None = None,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: ShipmentService = Depends(get_service),
) -> ShipmentDetailResponse:
    """Mark shipment delivered and update order status."""
    return await service.deliver(tenant_id, shipment_id, data)


@router.post("/{shipment_id}/cancel", response_model=ShipmentDetailResponse)
async def cancel_shipment(
    shipment_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: ShipmentService = Depends(get_service),
) -> ShipmentDetailResponse:
    return await service.cancel(tenant_id, shipment_id)


@router.get("", response_model=PaginatedResponse[ShipmentResponse])
async def list_shipments(
    order_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: ShipmentService = Depends(get_service),
) -> PaginatedResponse[ShipmentResponse]:
    return await service.list(
        tenant_id, order_id=order_id, status=status, page=page, page_size=page_size
    )


@router.get("/{shipment_id}", response_model=ShipmentDetailResponse)
async def get_shipment(
    shipment_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: ShipmentService = Depends(get_service),
) -> ShipmentDetailResponse:
    return await service.get(tenant_id, shipment_id)
