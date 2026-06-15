from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db
from app.modules.stores.schemas import (
    StoreCreate,
    StoreDetailResponse,
    StoreResponse,
    StoreSettingsResponse,
    StoreSettingsUpdate,
    StoreUpdate,
)
from app.modules.stores.service import StoreService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/stores", tags=["Stores"])


def get_store_service(session: AsyncSession = Depends(get_db)) -> StoreService:
    return StoreService(session)


@router.post("", response_model=StoreDetailResponse, status_code=201)
async def create_store(
    data: StoreCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: StoreService = Depends(get_store_service),
) -> StoreDetailResponse:
    """Create a new store with default settings and HQ branch."""
    return await service.create_store(tenant_id, data)


@router.get("", response_model=PaginatedResponse[StoreResponse])
async def list_stores(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: StoreService = Depends(get_store_service),
) -> PaginatedResponse[StoreResponse]:
    """List all stores for the current tenant."""
    return await service.list_stores(tenant_id, page=page, page_size=page_size)


@router.get("/{store_id}", response_model=StoreDetailResponse)
async def get_store(
    store_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: StoreService = Depends(get_store_service),
) -> StoreDetailResponse:
    """Get store details including settings and branch count."""
    return await service.get_store(tenant_id, store_id)


@router.patch("/{store_id}", response_model=StoreResponse)
async def update_store(
    store_id: UUID,
    data: StoreUpdate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: StoreService = Depends(get_store_service),
) -> StoreResponse:
    """Update store information."""
    return await service.update_store(tenant_id, store_id, data)


@router.delete("/{store_id}", status_code=204)
async def delete_store(
    store_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: StoreService = Depends(get_store_service),
) -> None:
    """Soft-delete a store by marking it as closed."""
    await service.delete_store(tenant_id, store_id)


@router.get("/{store_id}/settings", response_model=StoreSettingsResponse)
async def get_store_settings(
    store_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: StoreService = Depends(get_store_service),
) -> StoreSettingsResponse:
    """Get store-specific settings."""
    return await service.get_settings(tenant_id, store_id)


@router.patch("/{store_id}/settings", response_model=StoreSettingsResponse)
async def update_store_settings(
    store_id: UUID,
    data: StoreSettingsUpdate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: StoreService = Depends(get_store_service),
) -> StoreSettingsResponse:
    """Update store-specific settings."""
    return await service.update_settings(tenant_id, store_id, data)
