from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.modules.returns.models import Return, ReturnItem
from app.shared.base_model import ReturnStatus
from app.shared.base_repository import TenantScopedRepository


class ReturnRepository(TenantScopedRepository[Return]):
    model = Return

    async def get_with_details(self, tenant_id: UUID, return_id: UUID) -> Return | None:
        stmt = (
            select(Return)
            .where(Return.tenant_id == tenant_id, Return.id == return_id)
            .options(selectinload(Return.items))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_for_tenant(self, tenant_id: UUID) -> int:
        stmt = select(func.count()).select_from(Return).where(Return.tenant_id == tenant_id)
        return (await self.session.execute(stmt)).scalar_one()

    async def list_for_tenant(
        self,
        tenant_id: UUID,
        *,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Return], int]:
        filters = [Return.tenant_id == tenant_id]
        if reference_type:
            filters.append(Return.reference_type == reference_type)
        if reference_id:
            filters.append(Return.reference_id == reference_id)
        if status:
            filters.append(Return.status == status)

        count_stmt = select(func.count()).select_from(Return).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(Return)
            .where(*filters)
            .options(selectinload(Return.items))
            .offset(offset)
            .limit(limit)
            .order_by(Return.requested_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total


class ReturnItemRepository(TenantScopedRepository[ReturnItem]):
    model = ReturnItem

    async def sum_returned_for_source(
        self,
        tenant_id: UUID,
        reference_type: str,
        reference_id: UUID,
        source_item_id: UUID,
        *,
        exclude_return_id: UUID | None = None,
    ) -> int:
        active_statuses = [
            ReturnStatus.REQUESTED.value,
            ReturnStatus.APPROVED.value,
            ReturnStatus.RECEIVED.value,
            ReturnStatus.REFUNDED.value,
        ]
        stmt = (
            select(func.coalesce(func.sum(ReturnItem.quantity_requested), 0))
            .join(Return, ReturnItem.return_id == Return.id)
            .where(
                Return.tenant_id == tenant_id,
                Return.reference_type == reference_type,
                Return.reference_id == reference_id,
                ReturnItem.source_item_id == source_item_id,
                Return.status.in_(active_statuses),
            )
        )
        if exclude_return_id:
            stmt = stmt.where(Return.id != exclude_return_id)
        return (await self.session.execute(stmt)).scalar_one()
