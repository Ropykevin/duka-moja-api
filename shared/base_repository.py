from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, TenantScopeError
from app.core.tenant import get_tenant_id
from app.shared.base_model import BaseModel, TenantScopedModel

ModelT = TypeVar("ModelT", bound=BaseModel)
TenantModelT = TypeVar("TenantModelT", bound=TenantScopedModel)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, entity_id: UUID) -> ModelT | None:
        stmt = select(self.model).where(self.model.id == entity_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_or_raise(self, entity_id: UUID) -> ModelT:
        entity = await self.get_by_id(entity_id)
        if entity is None:
            raise NotFoundError(self.model.__name__, entity_id)
        return entity

    async def list_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[ModelT], int]:
        count_stmt = select(func.count()).select_from(self.model)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = select(self.model).offset(offset).limit(limit).order_by(self.model.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def create(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: ModelT) -> ModelT:
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)
        await self.session.flush()


class TenantScopedRepository(BaseRepository[TenantModelT]):
    def _apply_tenant_scope(self, stmt: Select) -> Select:
        tenant_id = get_tenant_id()
        if tenant_id is None:
            return stmt
        return stmt.where(self.model.tenant_id == tenant_id)

    def _validate_tenant_access(self, entity: TenantModelT) -> TenantModelT:
        tenant_id = get_tenant_id()
        if tenant_id is not None and entity.tenant_id != tenant_id:
            raise TenantScopeError(
                f"Access denied: {self.model.__name__} belongs to another tenant"
            )
        return entity

    async def get_by_id(self, entity_id: UUID) -> TenantModelT | None:
        stmt = self._apply_tenant_scope(select(self.model).where(self.model.id == entity_id))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_or_raise(self, entity_id: UUID) -> TenantModelT:
        entity = await self.get_by_id(entity_id)
        if entity is None:
            raise NotFoundError(self.model.__name__, entity_id)
        return entity

    async def list_for_tenant(
        self,
        tenant_id: UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[TenantModelT], int]:
        count_stmt = select(func.count()).select_from(self.model).where(
            self.model.tenant_id == tenant_id
        )
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(self.model)
            .where(self.model.tenant_id == tenant_id)
            .offset(offset)
            .limit(limit)
            .order_by(self.model.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def create_for_tenant(self, entity: TenantModelT, tenant_id: UUID) -> TenantModelT:
        entity.tenant_id = tenant_id
        return await self.create(entity)
