from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from app.modules.stores.models import Branch, Store, StoreSettings
from app.shared.base_repository import TenantScopedRepository


class StoreRepository(TenantScopedRepository[Store]):
    model = Store

    async def get_by_slug(self, tenant_id: UUID, slug: str) -> Store | None:
        stmt = select(Store).where(Store.tenant_id == tenant_id, Store.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_default(self, tenant_id: UUID) -> Store | None:
        stmt = select(Store).where(Store.tenant_id == tenant_id, Store.is_default.is_(True))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_details(self, tenant_id: UUID, store_id: UUID) -> Store | None:
        stmt = (
            select(Store)
            .where(Store.tenant_id == tenant_id, Store.id == store_id)
            .options(
                selectinload(Store.settings),
                selectinload(Store.branches),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_for_tenant(self, tenant_id: UUID) -> int:
        stmt = select(func.count()).select_from(Store).where(Store.tenant_id == tenant_id)
        return (await self.session.execute(stmt)).scalar_one()

    async def clear_default_flag(self, tenant_id: UUID, exclude_id: UUID | None = None) -> None:
        stmt = update(Store).where(Store.tenant_id == tenant_id, Store.is_default.is_(True))
        if exclude_id:
            stmt = stmt.where(Store.id != exclude_id)
        await self.session.execute(stmt.values(is_default=False))


class BranchRepository(TenantScopedRepository[Branch]):
    model = Branch

    async def get_by_code(self, tenant_id: UUID, store_id: UUID, code: str) -> Branch | None:
        stmt = select(Branch).where(
            Branch.tenant_id == tenant_id,
            Branch.store_id == store_id,
            Branch.code == code,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_store(
        self,
        tenant_id: UUID,
        store_id: UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[Branch], int]:
        count_stmt = select(func.count()).select_from(Branch).where(
            Branch.tenant_id == tenant_id,
            Branch.store_id == store_id,
        )
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(Branch)
            .where(Branch.tenant_id == tenant_id, Branch.store_id == store_id)
            .offset(offset)
            .limit(limit)
            .order_by(Branch.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def count_for_store(self, tenant_id: UUID, store_id: UUID) -> int:
        stmt = select(func.count()).select_from(Branch).where(
            Branch.tenant_id == tenant_id,
            Branch.store_id == store_id,
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def count_for_tenant(self, tenant_id: UUID) -> int:
        stmt = select(func.count()).select_from(Branch).where(Branch.tenant_id == tenant_id)
        return (await self.session.execute(stmt)).scalar_one()

    async def clear_headquarters_flag(
        self, tenant_id: UUID, store_id: UUID, exclude_id: UUID | None = None
    ) -> None:
        stmt = update(Branch).where(
            Branch.tenant_id == tenant_id,
            Branch.store_id == store_id,
            Branch.is_headquarters.is_(True),
        )
        if exclude_id:
            stmt = stmt.where(Branch.id != exclude_id)
        await self.session.execute(stmt.values(is_headquarters=False))


class StoreSettingsRepository(TenantScopedRepository[StoreSettings]):
    model = StoreSettings

    async def get_by_store_id(self, tenant_id: UUID, store_id: UUID) -> StoreSettings | None:
        stmt = select(StoreSettings).where(
            StoreSettings.tenant_id == tenant_id,
            StoreSettings.store_id == store_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
