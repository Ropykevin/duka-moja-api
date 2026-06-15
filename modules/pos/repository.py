from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.modules.pos.models import CashRegister, CashSession, Sale, SaleItem
from app.shared.base_model import CashSessionStatus, SaleStatus
from app.shared.base_repository import TenantScopedRepository


class CashRegisterRepository(TenantScopedRepository[CashRegister]):
    model = CashRegister

    async def get_by_code(self, tenant_id: UUID, code: str) -> CashRegister | None:
        stmt = select(CashRegister).where(
            CashRegister.tenant_id == tenant_id, CashRegister.code == code
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_branch(
        self, tenant_id: UUID, branch_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[CashRegister], int]:
        filters = [
            CashRegister.tenant_id == tenant_id,
            CashRegister.branch_id == branch_id,
        ]
        count_stmt = select(func.count()).select_from(CashRegister).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(CashRegister)
            .where(*filters)
            .offset(offset)
            .limit(limit)
            .order_by(CashRegister.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total


class CashSessionRepository(TenantScopedRepository[CashSession]):
    model = CashSession

    async def get_open_for_register(
        self, tenant_id: UUID, register_id: UUID
    ) -> CashSession | None:
        stmt = select(CashSession).where(
            CashSession.tenant_id == tenant_id,
            CashSession.register_id == register_id,
            CashSession.status == CashSessionStatus.OPEN.value,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_tenant(
        self,
        tenant_id: UUID,
        *,
        register_id: UUID | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[CashSession], int]:
        filters = [CashSession.tenant_id == tenant_id]
        if register_id:
            filters.append(CashSession.register_id == register_id)
        if status:
            filters.append(CashSession.status == status)

        count_stmt = select(func.count()).select_from(CashSession).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(CashSession)
            .where(*filters)
            .offset(offset)
            .limit(limit)
            .order_by(CashSession.opened_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total


class SaleRepository(TenantScopedRepository[Sale]):
    model = Sale

    async def get_with_details(self, tenant_id: UUID, sale_id: UUID) -> Sale | None:
        stmt = (
            select(Sale)
            .where(Sale.tenant_id == tenant_id, Sale.id == sale_id)
            .options(selectinload(Sale.items))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_for_tenant(self, tenant_id: UUID) -> int:
        stmt = select(func.count()).select_from(Sale).where(Sale.tenant_id == tenant_id)
        return (await self.session.execute(stmt)).scalar_one()

    async def count_draft_for_session(self, tenant_id: UUID, session_id: UUID) -> int:
        stmt = select(func.count()).select_from(Sale).where(
            Sale.tenant_id == tenant_id,
            Sale.session_id == session_id,
            Sale.status == SaleStatus.DRAFT.value,
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def list_for_tenant(
        self,
        tenant_id: UUID,
        *,
        session_id: UUID | None = None,
        register_id: UUID | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Sale], int]:
        filters = [Sale.tenant_id == tenant_id]
        if session_id:
            filters.append(Sale.session_id == session_id)
        if register_id:
            filters.append(Sale.register_id == register_id)
        if status:
            filters.append(Sale.status == status)

        count_stmt = select(func.count()).select_from(Sale).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(Sale)
            .where(*filters)
            .offset(offset)
            .limit(limit)
            .order_by(Sale.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total)


class SaleItemRepository(TenantScopedRepository[SaleItem]):
    model = SaleItem

    async def get_by_sale_and_variant(
        self, sale_id: UUID, product_variant_id: UUID
    ) -> SaleItem | None:
        stmt = select(SaleItem).where(
            SaleItem.sale_id == sale_id,
            SaleItem.product_variant_id == product_variant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
