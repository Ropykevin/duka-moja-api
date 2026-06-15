from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db
from app.modules.shipping.schemas import (
    ShippingMethodCreate,
    ShippingMethodResponse,
    ShippingMethodUpdate,
)
from app.modules.shipping.service import ShippingMethodService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/shipping-methods", tags=["Shipping Methods"])


def get_service(session: AsyncSession = Depends(get_db)) -> ShippingMethodService:
    return ShippingMethodService(session)


@router.post("", response_model=ShippingMethodResponse, status_code=201)
async def create_method(
    data: ShippingMethodCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: ShippingMethodService = Depends(get_service),
) -> ShippingMethodResponse:
    return await service.create(tenant_id, data)


@router.get("", response_model=PaginatedResponse[ShippingMethodResponse])
async def list_methods(
    store_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: ShippingMethodService = Depends(get_service),
) -> PaginatedResponse[ShippingMethodResponse]:
    return await service.list(tenant_id, store_id=store_id, page=page, page_size=page_size)


@router.get("/{method_id}", response_model=ShippingMethodResponse)
async def get_method(
    method_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: ShippingMethodService = Depends(get_service),
) -> ShippingMethodResponse:
    return await service.get(tenant_id, method_id)


@router.patch("/{method_id}", response_model=ShippingMethodResponse)
async def update_method(
    method_id: UUID,
    data: ShippingMethodUpdate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: ShippingMethodService = Depends(get_service),
) -> ShippingMethodResponse:
    return await service.update(tenant_id, method_id, data)
