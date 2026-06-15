from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TenantScopeError
from app.shared.base_model import BaseModel, TenantScopedModel
from app.shared.base_repository import BaseRepository, TenantScopedRepository

ModelT = TypeVar("ModelT", bound=BaseModel)
TenantModelT = TypeVar("TenantModelT", bound=TenantScopedModel)
RepoT = TypeVar("RepoT", bound=BaseRepository)


class BaseService(Generic[ModelT, RepoT]):
    repository_class: type[RepoT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = self.repository_class(session)

    async def get_by_id(self, entity_id: UUID) -> ModelT:
        return await self.repository.get_by_id_or_raise(entity_id)


class TenantScopedService(Generic[TenantModelT, RepoT]):
    repository_class: type[RepoT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository: TenantScopedRepository[TenantModelT] = self.repository_class(session)

    async def get_by_id(self, entity_id: UUID, tenant_id: UUID) -> TenantModelT:
        entity = await self.repository.get_by_id_or_raise(entity_id)
        if entity.tenant_id != tenant_id:
            raise TenantScopeError()
        return entity

    async def list(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[TenantModelT], int]:
        offset = (page - 1) * page_size
        return await self.repository.list_for_tenant(
            tenant_id, offset=offset, limit=page_size
        )
