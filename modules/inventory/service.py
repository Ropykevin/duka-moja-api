from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.catalog.repository import ProductVariantRepository
from app.modules.inventory.models import Inventory, InventoryMovement, StockTransfer, StockTransferItem
from app.modules.inventory.repository import (
    InventoryMovementRepository,
    InventoryRepository,
    StockTransferRepository,
)
from app.modules.inventory.schemas import (
    InventoryMovementResponse,
    InventoryResponse,
    ReceiveStockCreate,
    StockAdjustmentCreate,
    StockTransferCreate,
    StockTransferReceiveRequest,
    StockTransferResponse,
    StockTransferShipRequest,
)
from app.modules.stores.repository import BranchRepository, StoreSettingsRepository
from app.shared.base_model import InventoryMovementSource, StockTransferStatus
from app.shared.schemas import PaginatedResponse


class InventoryService:
    """All stock changes MUST go through record_movement — never update Inventory directly."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.inventory_repo = InventoryRepository(session)
        self.movement_repo = InventoryMovementRepository(session)
        self.variant_repo = ProductVariantRepository(session)
        self.branch_repo = BranchRepository(session)
        self.settings_repo = StoreSettingsRepository(session)

    async def get_stock(
        self, tenant_id: UUID, branch_id: UUID, product_variant_id: UUID
    ) -> InventoryResponse:
        await self._validate_branch(tenant_id, branch_id)
        await self._validate_variant(tenant_id, product_variant_id)
        inventory = await self.inventory_repo.get_or_create(
            tenant_id, branch_id, product_variant_id
        )
        return self._to_inventory_response(inventory)

    async def list_stock(
        self,
        tenant_id: UUID,
        branch_id: UUID,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[InventoryResponse]:
        await self._validate_branch(tenant_id, branch_id)
        items, total = await self.inventory_repo.list_for_branch(
            tenant_id, branch_id, offset=(page - 1) * page_size, limit=page_size
        )
        return PaginatedResponse.create(
            [self._to_inventory_response(i) for i in items], total, page, page_size
        )

    async def list_movements(
        self,
        tenant_id: UUID,
        *,
        branch_id: UUID | None = None,
        product_variant_id: UUID | None = None,
        movement_source: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[InventoryMovementResponse]:
        items, total = await self.movement_repo.list_for_branch(
            tenant_id,
            branch_id=branch_id,
            product_variant_id=product_variant_id,
            movement_source=movement_source,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return PaginatedResponse.create(
            [InventoryMovementResponse.model_validate(m) for m in items],
            total,
            page,
            page_size,
        )

    async def adjust_stock(
        self,
        tenant_id: UUID,
        data: StockAdjustmentCreate,
        *,
        created_by: UUID | None = None,
    ) -> InventoryMovementResponse:
        return await self.record_movement(
            tenant_id,
            data.branch_id,
            data.product_variant_id,
            InventoryMovementSource.ADJUSTMENT,
            data.quantity,
            notes=data.notes,
            created_by=created_by,
            reference_type="adjustment",
        )

    async def receive_stock(
        self,
        tenant_id: UUID,
        data: ReceiveStockCreate,
        *,
        created_by: UUID | None = None,
    ) -> InventoryMovementResponse:
        return await self.record_movement(
            tenant_id,
            data.branch_id,
            data.product_variant_id,
            InventoryMovementSource.PURCHASE,
            data.quantity,
            notes=data.notes,
            created_by=created_by,
            reference_type=data.reference_type,
            reference_id=data.reference_id,
        )

    async def record_movement(
        self,
        tenant_id: UUID,
        branch_id: UUID,
        product_variant_id: UUID,
        source: InventoryMovementSource,
        quantity: int,
        *,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
        notes: str | None = None,
        created_by: UUID | None = None,
        allow_negative: bool | None = None,
    ) -> InventoryMovementResponse:
        if quantity == 0:
            raise ValidationError("Movement quantity cannot be zero")

        await self._validate_branch(tenant_id, branch_id)
        await self._validate_variant(tenant_id, product_variant_id)

        if allow_negative is None:
            allow_negative = await self._allow_negative_stock(tenant_id, branch_id)

        inventory = await self.inventory_repo.get_or_create(
            tenant_id, branch_id, product_variant_id
        )

        quantity_before = inventory.quantity_on_hand
        quantity_after = quantity_before + quantity

        if quantity < 0 and quantity_after < 0 and not allow_negative:
            raise ValidationError(
                f"Insufficient stock. Available: {quantity_before}, requested: {abs(quantity)}"
            )

        movement = InventoryMovement(
            tenant_id=tenant_id,
            branch_id=branch_id,
            product_variant_id=product_variant_id,
            movement_source=source.value,
            quantity=quantity,
            quantity_before=quantity_before,
            quantity_after=quantity_after,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
            created_by=created_by,
        )
        movement = await self.movement_repo.create(movement)

        inventory.quantity_on_hand = quantity_after
        await self.inventory_repo.update(inventory)

        return InventoryMovementResponse.model_validate(movement)

    async def _validate_branch(self, tenant_id: UUID, branch_id: UUID) -> None:
        branch = await self.branch_repo.get_by_id(branch_id)
        if branch is None or branch.tenant_id != tenant_id:
            raise NotFoundError("Branch", branch_id)

    async def _validate_variant(self, tenant_id: UUID, product_variant_id: UUID):
        variant = await self.variant_repo.get_by_id(product_variant_id)
        if variant is None or variant.tenant_id != tenant_id:
            raise NotFoundError("ProductVariant", product_variant_id)
        return variant

    async def _allow_negative_stock(self, tenant_id: UUID, branch_id: UUID) -> bool:
        branch = await self.branch_repo.get_by_id(branch_id)
        if branch is None:
            return False
        settings = await self.settings_repo.get_by_store_id(tenant_id, branch.store_id)
        return settings.allow_negative_stock if settings else False

    @staticmethod
    def _to_inventory_response(inventory: Inventory) -> InventoryResponse:
        return InventoryResponse(
            id=inventory.id,
            tenant_id=inventory.tenant_id,
            branch_id=inventory.branch_id,
            product_variant_id=inventory.product_variant_id,
            quantity_on_hand=inventory.quantity_on_hand,
            quantity_reserved=inventory.quantity_reserved,
            quantity_available=inventory.quantity_available,
            created_at=inventory.created_at,
            updated_at=inventory.updated_at,
        )


class StockTransferService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.transfer_repo = StockTransferRepository(session)
        self.branch_repo = BranchRepository(session)
        self.variant_repo = ProductVariantRepository(session)
        self.inventory_service = InventoryService(session)

    async def create(
        self,
        tenant_id: UUID,
        data: StockTransferCreate,
        *,
        requested_by: UUID | None = None,
    ) -> StockTransferResponse:
        if data.from_branch_id == data.to_branch_id:
            raise ValidationError("Source and destination branches must be different")

        await self.inventory_service._validate_branch(tenant_id, data.from_branch_id)
        await self.inventory_service._validate_branch(tenant_id, data.to_branch_id)

        for item in data.items:
            await self.inventory_service._validate_variant(tenant_id, item.product_variant_id)

        transfer_number = await self._generate_transfer_number(tenant_id)

        transfer = StockTransfer(
            tenant_id=tenant_id,
            transfer_number=transfer_number,
            from_branch_id=data.from_branch_id,
            to_branch_id=data.to_branch_id,
            status=StockTransferStatus.DRAFT.value,
            notes=data.notes,
            requested_by=requested_by,
        )
        transfer = await self.transfer_repo.create(transfer)

        for item_data in data.items:
            item = StockTransferItem(
                tenant_id=tenant_id,
                transfer_id=transfer.id,
                product_variant_id=item_data.product_variant_id,
                quantity_requested=item_data.quantity_requested,
            )
            self.session.add(item)

        await self.session.flush()
        transfer = await self.transfer_repo.get_with_items(tenant_id, transfer.id)
        return StockTransferResponse.model_validate(transfer)

    async def list(
        self,
        tenant_id: UUID,
        *,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[StockTransferResponse]:
        items, total = await self.transfer_repo.list_for_tenant(
            tenant_id, status=status, offset=(page - 1) * page_size, limit=page_size
        )
        return PaginatedResponse.create(
            [StockTransferResponse.model_validate(t) for t in items], total, page, page_size
        )

    async def get(self, tenant_id: UUID, transfer_id: UUID) -> StockTransferResponse:
        transfer = await self._get_or_raise(tenant_id, transfer_id)
        return StockTransferResponse.model_validate(transfer)

    async def submit(self, tenant_id: UUID, transfer_id: UUID) -> StockTransferResponse:
        transfer = await self._get_or_raise(tenant_id, transfer_id)
        if transfer.status != StockTransferStatus.DRAFT.value:
            raise ValidationError("Only draft transfers can be submitted")
        transfer.status = StockTransferStatus.PENDING_APPROVAL.value
        transfer = await self.transfer_repo.update(transfer)
        return StockTransferResponse.model_validate(transfer)

    async def approve(
        self,
        tenant_id: UUID,
        transfer_id: UUID,
        *,
        approved_by: UUID | None = None,
    ) -> StockTransferResponse:
        transfer = await self._get_or_raise(tenant_id, transfer_id)
        if transfer.status != StockTransferStatus.PENDING_APPROVAL.value:
            raise ValidationError("Only pending transfers can be approved")
        transfer.status = StockTransferStatus.APPROVED.value
        transfer.approved_by = approved_by
        transfer.approved_at = datetime.now(UTC)
        transfer = await self.transfer_repo.update(transfer)
        return StockTransferResponse.model_validate(transfer)

    async def ship(
        self,
        tenant_id: UUID,
        transfer_id: UUID,
        data: StockTransferShipRequest | None = None,
        *,
        created_by: UUID | None = None,
    ) -> StockTransferResponse:
        transfer = await self._get_or_raise(tenant_id, transfer_id)
        if transfer.status != StockTransferStatus.APPROVED.value:
            raise ValidationError("Only approved transfers can be shipped")

        ship_map = {}
        if data and data.items:
            ship_map = {item.item_id: item.quantity_shipped for item in data.items}

        for item in transfer.items:
            qty = ship_map.get(item.id, item.quantity_requested)
            if qty > item.quantity_requested:
                raise ValidationError(
                    f"Shipped quantity exceeds requested for item {item.id}"
                )
            item.quantity_shipped = qty

            await self.inventory_service.record_movement(
                tenant_id,
                transfer.from_branch_id,
                item.product_variant_id,
                InventoryMovementSource.TRANSFER_OUT,
                -qty,
                reference_type="stock_transfer",
                reference_id=transfer.id,
                notes=f"Transfer {transfer.transfer_number} shipped",
                created_by=created_by,
            )

        transfer.status = StockTransferStatus.IN_TRANSIT.value
        transfer.shipped_at = datetime.now(UTC)
        transfer = await self.transfer_repo.update(transfer)
        transfer = await self.transfer_repo.get_with_items(tenant_id, transfer.id)
        return StockTransferResponse.model_validate(transfer)

    async def receive(
        self,
        tenant_id: UUID,
        transfer_id: UUID,
        data: StockTransferReceiveRequest | None = None,
        *,
        created_by: UUID | None = None,
    ) -> StockTransferResponse:
        transfer = await self._get_or_raise(tenant_id, transfer_id)
        if transfer.status != StockTransferStatus.IN_TRANSIT.value:
            raise ValidationError("Only in-transit transfers can be received")

        receive_map = {}
        if data and data.items:
            receive_map = {item.item_id: item.quantity_received for item in data.items}

        for item in transfer.items:
            qty = receive_map.get(item.id, item.quantity_shipped)
            if qty > item.quantity_shipped:
                raise ValidationError(
                    f"Received quantity exceeds shipped for item {item.id}"
                )
            item.quantity_received = qty

            await self.inventory_service.record_movement(
                tenant_id,
                transfer.to_branch_id,
                item.product_variant_id,
                InventoryMovementSource.TRANSFER_IN,
                qty,
                reference_type="stock_transfer",
                reference_id=transfer.id,
                notes=f"Transfer {transfer.transfer_number} received",
                created_by=created_by,
            )

        transfer.status = StockTransferStatus.RECEIVED.value
        transfer.received_at = datetime.now(UTC)
        transfer = await self.transfer_repo.update(transfer)
        transfer = await self.transfer_repo.get_with_items(tenant_id, transfer.id)
        return StockTransferResponse.model_validate(transfer)

    async def cancel(self, tenant_id: UUID, transfer_id: UUID) -> StockTransferResponse:
        transfer = await self._get_or_raise(tenant_id, transfer_id)
        if transfer.status in (
            StockTransferStatus.RECEIVED.value,
            StockTransferStatus.CANCELLED.value,
        ):
            raise ValidationError("Transfer cannot be cancelled in current status")
        if transfer.status == StockTransferStatus.IN_TRANSIT.value:
            raise ValidationError("In-transit transfers must be received, not cancelled")
        transfer.status = StockTransferStatus.CANCELLED.value
        transfer = await self.transfer_repo.update(transfer)
        return StockTransferResponse.model_validate(transfer)

    async def _get_or_raise(self, tenant_id: UUID, transfer_id: UUID) -> StockTransfer:
        transfer = await self.transfer_repo.get_with_items(tenant_id, transfer_id)
        if transfer is None:
            raise NotFoundError("StockTransfer", transfer_id)
        return transfer

    async def _generate_transfer_number(self, tenant_id: UUID) -> str:
        count = await self.transfer_repo.count_for_tenant(tenant_id)
        return f"ST-{count + 1:06d}"
