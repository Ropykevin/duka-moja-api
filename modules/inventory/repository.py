from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.inventory.models import (
    Inventory,
    InventoryMovement,
    StockTransfer,
    StockTransferItem,
)
from app.shared.base_repository import TenantScopedRepository


class InventoryRepository(TenantScopedRepository[Inventory]):
    model = Inventory

    async def get_for_branch_variant(
        self, tenant_id: UUID, branch_id: UUID, product_variant_id: UUID
    ) -> Inventory | None:
        stmt = select(Inventory).where(
            Inventory.tenant_id == tenant_id,
            Inventory.branch_id == branch_id,
            Inventory.product_variant_id == product_variant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_branch(
        self,
        tenant_id: UUID,
        branch_id: UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Inventory], int]:
        count_stmt = select(func.count()).select_from(Inventory).where(
            Inventory.tenant_id == tenant_id,
            Inventory.branch_id == branch_id,
        )
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(Inventory)
            .where(Inventory.tenant_id == tenant_id, Inventory.branch_id == branch_id)
            .offset(offset)
            .limit(limit)
            .order_by(Inventory.updated_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_or_create(
        self, tenant_id: UUID, branch_id: UUID, product_variant_id: UUID
    ) -> Inventory:
        inventory = await self.get_for_branch_variant(
            tenant_id, branch_id, product_variant_id
        )
        if inventory is None:
            inventory = Inventory(
                tenant_id=tenant_id,
                branch_id=branch_id,
                product_variant_id=product_variant_id,
                quantity_on_hand=0,
                quantity_reserved=0,
            )
            inventory = await self.create(inventory)
        return inventory


class InventoryMovementRepository(TenantScopedRepository[InventoryMovement]):
    model = InventoryMovement

    async def list_for_branch(
        self,
        tenant_id: UUID,
        branch_id: UUID | None = None,
        product_variant_id: UUID | None = None,
        movement_source: str | None = None,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[InventoryMovement], int]:
        filters = [InventoryMovement.tenant_id == tenant_id]
        if branch_id:
            filters.append(InventoryMovement.branch_id == branch_id)
        if product_variant_id:
            filters.append(InventoryMovement.product_variant_id == product_variant_id)
        if movement_source:
            filters.append(InventoryMovement.movement_source == movement_source)

        count_stmt = select(func.count()).select_from(InventoryMovement).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(InventoryMovement)
            .where(*filters)
            .offset(offset)
            .limit(limit)
            .order_by(InventoryMovement.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total


class StockTransferRepository(TenantScopedRepository[StockTransfer]):
    model = StockTransfer

    async def get_with_items(self, tenant_id: UUID, transfer_id: UUID) -> StockTransfer | None:
        stmt = (
            select(StockTransfer)
            .where(StockTransfer.tenant_id == tenant_id, StockTransfer.id == transfer_id)
            .options(selectinload(StockTransfer.items))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_for_tenant(self, tenant_id: UUID) -> int:
        stmt = select(func.count()).select_from(StockTransfer).where(
            StockTransfer.tenant_id == tenant_id
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def list_for_tenant(
        self,
        tenant_id: UUID,
        *,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[StockTransfer], int]:
        filters = [StockTransfer.tenant_id == tenant_id]
        if status:
            filters.append(StockTransfer.status == status)

        count_stmt = select(func.count()).select_from(StockTransfer).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(StockTransfer)
            .where(*filters)
            .options(selectinload(StockTransfer.items))
            .offset(offset)
            .limit(limit)
            .order_by(StockTransfer.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total


class StockTransferItemRepository(TenantScopedRepository[StockTransferItem]):
    model = StockTransferItem
