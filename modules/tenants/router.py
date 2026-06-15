from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db
from app.modules.tenants.schemas import TenantResponse, TenantUpdate
from app.modules.tenants.service import TenantService

router = APIRouter(prefix="/tenants", tags=["Tenants"])


def get_tenant_service(session: AsyncSession = Depends(get_db)) -> TenantService:
    return TenantService(session)


@router.get("/me", response_model=TenantResponse)
async def get_my_tenant(
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: TenantService = Depends(get_tenant_service),
) -> TenantResponse:
    """Get the current user's tenant."""
    return await service.get_tenant(tenant_id)


@router.patch("/me", response_model=TenantResponse)
async def update_my_tenant(
    data: TenantUpdate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: TenantService = Depends(get_tenant_service),
) -> TenantResponse:
    """Update the current user's tenant settings."""
    return await service.update_tenant(tenant_id, data)
