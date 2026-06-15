from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db, require_authenticated_user
from app.modules.customers.schemas import CheckoutRequest, OrderDetailResponse, OrderResponse
from app.modules.customers.service import OrderService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/orders", tags=["Orders"])


def get_service(session: AsyncSession = Depends(get_db)) -> OrderService:
    return OrderService(session)


@router.post("/checkout", response_model=OrderDetailResponse, status_code=201)
async def checkout(
    data: CheckoutRequest,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: OrderService = Depends(get_service),
) -> OrderDetailResponse:
    """Convert cart to a pending order."""
    return await service.checkout(tenant_id, data)


@router.get("", response_model=PaginatedResponse[OrderResponse])
async def list_orders(
    customer_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: OrderService = Depends(get_service),
) -> PaginatedResponse[OrderResponse]:
    return await service.list(
        tenant_id, customer_id=customer_id, status=status, page=page, page_size=page_size
    )


@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_order(
    order_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: OrderService = Depends(get_service),
) -> OrderDetailResponse:
    return await service.get(tenant_id, order_id)


@router.post("/{order_id}/confirm", response_model=OrderDetailResponse)
async def confirm_order(
    order_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: OrderService = Depends(get_service),
) -> OrderDetailResponse:
    """Confirm order and deduct inventory via InventoryMovement."""
    return await service.confirm(tenant_id, order_id, confirmed_by=user_id)


@router.post("/{order_id}/cancel", response_model=OrderDetailResponse)
async def cancel_order(
    order_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: OrderService = Depends(get_service),
) -> OrderDetailResponse:
    """Cancel order. Restores stock if already confirmed."""
    return await service.cancel(tenant_id, order_id)
