from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.modules.tenants.models import Tenant
from app.modules.tenants.repository import TenantRepository
from app.modules.tenants.schemas import TenantResponse, TenantUpdate
from app.shared.base_service import BaseService


class TenantService(BaseService[Tenant, TenantRepository]):
    repository_class = TenantRepository

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_tenant(self, tenant_id: UUID) -> TenantResponse:
        tenant = await self.repository.get_by_id_or_raise(tenant_id)
        return TenantResponse.model_validate(tenant)

    async def update_tenant(self, tenant_id: UUID, data: TenantUpdate) -> TenantResponse:
        tenant = await self.repository.get_by_id_or_raise(tenant_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tenant, field, value)
        tenant = await self.repository.update(tenant)
        return TenantResponse.model_validate(tenant)

    async def ensure_tenant_access(self, tenant_id: UUID, user_tenant_id: UUID) -> Tenant:
        if tenant_id != user_tenant_id:
            raise ForbiddenError("Cannot access another tenant's data")
        tenant = await self.repository.get_by_id_or_raise(tenant_id)
        return tenant

    async def get_by_slug(self, slug: str) -> Tenant:
        tenant = await self.repository.get_by_slug(slug)
        if tenant is None:
            raise NotFoundError("Tenant", slug)
        return tenant
