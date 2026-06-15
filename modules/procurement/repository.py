from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.modules.procurement.models import PurchaseOrder, PurchaseOrderItem, Supplier
from app.shared.base_repository import TenantScopedRepository


class SupplierRepository(TenantScopedRepository[Supplier]):
    model = Supplier

    async def get_by_code(self, tenant_id: UUID, code: str) -> Supplier | None:
        stmt = select(Supplier).where(
            Supplier.tenant_id == tenant_id, Supplier.code == code
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(
        self, tenant_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[Supplier], int]:
        count_stmt = select(func.count()).select_from(Supplier).where(
            Supplier.tenant_id == tenant_id, Supplier.is_active.is_(True)
        )
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(Supplier)
            .where(Supplier.tenant_id == tenant_id, Supplier.is_active.is_(True))
            .offset(offset)
            .limit(limit)
            .order_by(Supplier.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total


class PurchaseOrderRepository(TenantScopedRepository[PurchaseOrder]):
    model = PurchaseOrder

    async def get_with_details(self, tenant_id: UUID, po_id: UUID) -> PurchaseOrder | None:
        stmt = (
            select(PurchaseOrder)
            .where(PurchaseOrder.tenant_id == tenant_id, PurchaseOrder.id == po_id)
            .options(
                selectinload(PurchaseOrder.items),
                selectinload(PurchaseOrder.supplier),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_for_tenant(self, tenant_id: UUID) -> int:
        stmt = select(func.count()).select_from(PurchaseOrder).where(
            PurchaseOrder.tenant_id == tenant_id
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def list_for_tenant(
        self,
        tenant_id: UUID,
        *,
        supplier_id: UUID | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[PurchaseOrder], int]:
        filters = [PurchaseOrder.tenant_id == tenant_id]
        if supplier_id:
            filters.append(PurchaseOrder.supplier_id == supplier_id)
        if status:
            filters.append(PurchaseOrder.status == status)

        count_stmt = select(func.count()).select_from(PurchaseOrder).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(PurchaseOrder)
            .where(*filters)
            .options(selectinload(PurchaseOrder.items), selectinload(PurchaseOrder.supplier))
            .offset(offset)
            .limit(limit)
            .order_by(PurchaseOrder.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total


class PurchaseOrderItemRepository(TenantScopedRepository[PurchaseOrderItem]):
    model = PurchaseOrderItem
