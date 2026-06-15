from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_authenticated_user
from app.modules.auth.repository import UserRepository
from app.modules.tenants.schemas import TenantResponse, TenantUpdate
from app.modules.tenants.service import TenantService

router = APIRouter(prefix="/tenants", tags=["Tenants"])


def get_tenant_service(session: AsyncSession = Depends(get_db)) -> TenantService:
    return TenantService(session)


async def get_current_user_tenant_id(
    user_id: UUID = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_db),
) -> UUID:
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id_or_raise(user_id)
    return user.tenant_id


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
