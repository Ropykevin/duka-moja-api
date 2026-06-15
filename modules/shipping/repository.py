from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.modules.shipping.models import Shipment, ShippingMethod
from app.shared.base_model import ShipmentStatus
from app.shared.base_repository import TenantScopedRepository


class ShippingMethodRepository(TenantScopedRepository[ShippingMethod]):
    model = ShippingMethod

    async def get_by_code(self, tenant_id: UUID, code: str) -> ShippingMethod | None:
        stmt = select(ShippingMethod).where(
            ShippingMethod.tenant_id == tenant_id, ShippingMethod.code == code
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_store(
        self,
        tenant_id: UUID,
        store_id: UUID | None = None,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ShippingMethod], int]:
        filters = [
            ShippingMethod.tenant_id == tenant_id,
            ShippingMethod.is_active.is_(True),
        ]
        if store_id:
            filters.append(
                (ShippingMethod.store_id == store_id) | (ShippingMethod.store_id.is_(None))
            )

        count_stmt = select(func.count()).select_from(ShippingMethod).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(ShippingMethod)
            .where(*filters)
            .offset(offset)
            .limit(limit)
            .order_by(ShippingMethod.sort_order, ShippingMethod.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total


class ShipmentRepository(TenantScopedRepository[Shipment]):
    model = Shipment

    async def get_with_details(self, tenant_id: UUID, shipment_id: UUID) -> Shipment | None:
        stmt = (
            select(Shipment)
            .where(Shipment.tenant_id == tenant_id, Shipment.id == shipment_id)
            .options(selectinload(Shipment.shipping_method))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_for_order(self, tenant_id: UUID, order_id: UUID) -> Shipment | None:
        stmt = select(Shipment).where(
            Shipment.tenant_id == tenant_id,
            Shipment.order_id == order_id,
            Shipment.status.notin_(
                [ShipmentStatus.DELIVERED.value, ShipmentStatus.CANCELLED.value]
            ),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_for_tenant(self, tenant_id: UUID) -> int:
        stmt = select(func.count()).select_from(Shipment).where(Shipment.tenant_id == tenant_id)
        return (await self.session.execute(stmt)).scalar_one()

    async def list_for_tenant(
        self,
        tenant_id: UUID,
        *,
        order_id: UUID | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Shipment], int]:
        filters = [Shipment.tenant_id == tenant_id]
        if order_id:
            filters.append(Shipment.order_id == order_id)
        if status:
            filters.append(Shipment.status == status)

        count_stmt = select(func.count()).select_from(Shipment).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(Shipment)
            .where(*filters)
            .options(selectinload(Shipment.shipping_method))
            .offset(offset)
            .limit(limit)
            .order_by(Shipment.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total
