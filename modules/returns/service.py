from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.customers.repository import OrderRepository
from app.modules.inventory.service import InventoryService
from app.modules.pos.repository import SaleRepository
from app.modules.returns.models import Return, ReturnItem
from app.modules.returns.repository import ReturnItemRepository, ReturnRepository
from app.modules.returns.schemas import (
    ReturnApproveRequest,
    ReturnCreate,
    ReturnDetailResponse,
    ReturnItemCreate,
    ReturnResponse,
)
from app.shared.base_model import (
    InventoryMovementSource,
    OrderStatus,
    PaymentStatus,
    ReturnReferenceType,
    ReturnStatus,
    SaleStatus,
)
from app.shared.schemas import PaginatedResponse


class ReturnService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.return_repo = ReturnRepository(session)
        self.item_repo = ReturnItemRepository(session)
        self.order_repo = OrderRepository(session)
        self.sale_repo = SaleRepository(session)
        self.inventory_service = InventoryService(session)

    async def create(
        self,
        tenant_id: UUID,
        data: ReturnCreate,
        *,
        requested_by: UUID | None = None,
    ) -> ReturnDetailResponse:
        ref_type = data.reference_type.value
        source = await self._resolve_source(tenant_id, ref_type, data.reference_id)

        for item_data in data.items:
            await self._validate_return_quantity(
                tenant_id, ref_type, data.reference_id, item_data, source
            )

        return_number = await self._generate_return_number(tenant_id)
        record = Return(
            tenant_id=tenant_id,
            return_number=return_number,
            reference_type=ref_type,
            reference_id=data.reference_id,
            customer_id=source["customer_id"],
            branch_id=source["branch_id"],
            store_id=source["store_id"],
            status=ReturnStatus.REQUESTED.value,
            reason=data.reason,
            notes=data.notes,
            requested_by=requested_by,
            requested_at=datetime.now(UTC),
        )
        record = await self.return_repo.create(record)

        for item_data in data.items:
            item = self._build_return_item(tenant_id, record.id, source, item_data)
            await self.item_repo.create(item)

        record = await self.return_repo.get_with_details(tenant_id, record.id)
        return ReturnDetailResponse.model_validate(record)

    async def approve(
        self,
        tenant_id: UUID,
        return_id: UUID,
        data: ReturnApproveRequest | None = None,
        *,
        approved_by: UUID | None = None,
    ) -> ReturnDetailResponse:
        record = await self._get_or_raise(tenant_id, return_id)
        if record.status != ReturnStatus.REQUESTED.value:
            raise ValidationError("Only requested returns can be approved")

        approve_map = {}
        if data and data.items:
            approve_map = {item.item_id: item.quantity_approved for item in data.items}

        refund_total = Decimal("0")
        for item in record.items:
            qty = approve_map.get(item.id, item.quantity_requested)
            if qty > item.quantity_requested:
                raise ValidationError(
                    f"Approved quantity exceeds requested for item {item.id}"
                )
            item.quantity_approved = qty
            item.line_refund = item.unit_price * qty
            refund_total += item.line_refund
            await self.item_repo.update(item)

        if refund_total <= 0:
            raise ValidationError("At least one item must be approved with quantity > 0")

        record.status = ReturnStatus.APPROVED.value
        record.refund_amount = refund_total
        record.approved_by = approved_by
        record.approved_at = datetime.now(UTC)
        if data and data.notes:
            record.notes = data.notes
        await self.return_repo.update(record)

        record = await self.return_repo.get_with_details(tenant_id, record.id)
        return ReturnDetailResponse.model_validate(record)

    async def receive(
        self,
        tenant_id: UUID,
        return_id: UUID,
        *,
        received_by: UUID | None = None,
    ) -> ReturnDetailResponse:
        record = await self._get_or_raise(tenant_id, return_id)
        if record.status != ReturnStatus.APPROVED.value:
            raise ValidationError("Only approved returns can be received")

        for item in record.items:
            if item.quantity_approved <= 0:
                continue
            await self.inventory_service.record_movement(
                tenant_id,
                record.branch_id,
                item.product_variant_id,
                InventoryMovementSource.RETURN,
                item.quantity_approved,
                reference_type="return",
                reference_id=record.id,
                notes=f"Return {record.return_number} received",
                created_by=received_by,
            )

        record.status = ReturnStatus.RECEIVED.value
        record.received_at = datetime.now(UTC)
        await self.return_repo.update(record)

        record = await self.return_repo.get_with_details(tenant_id, record.id)
        return ReturnDetailResponse.model_validate(record)

    async def mark_refunded(
        self, tenant_id: UUID, return_id: UUID
    ) -> ReturnDetailResponse:
        record = await self._get_or_raise(tenant_id, return_id)
        if record.status != ReturnStatus.RECEIVED.value:
            raise ValidationError("Only received returns can be marked refunded")

        record.status = ReturnStatus.REFUNDED.value
        record.refunded_at = datetime.now(UTC)
        await self.return_repo.update(record)
        await self._sync_payable_refund(record)

        record = await self.return_repo.get_with_details(tenant_id, record.id)
        return ReturnDetailResponse.model_validate(record)

    async def reject(
        self, tenant_id: UUID, return_id: UUID, *, notes: str | None = None
    ) -> ReturnDetailResponse:
        record = await self._get_or_raise(tenant_id, return_id)
        if record.status != ReturnStatus.REQUESTED.value:
            raise ValidationError("Only requested returns can be rejected")

        record.status = ReturnStatus.REJECTED.value
        if notes:
            record.notes = notes
        await self.return_repo.update(record)

        record = await self.return_repo.get_with_details(tenant_id, record.id)
        return ReturnDetailResponse.model_validate(record)

    async def cancel(self, tenant_id: UUID, return_id: UUID) -> ReturnDetailResponse:
        record = await self._get_or_raise(tenant_id, return_id)
        if record.status not in (
            ReturnStatus.REQUESTED.value,
            ReturnStatus.APPROVED.value,
        ):
            raise ValidationError("Return cannot be cancelled in current status")

        record.status = ReturnStatus.CANCELLED.value
        await self.return_repo.update(record)

        record = await self.return_repo.get_with_details(tenant_id, record.id)
        return ReturnDetailResponse.model_validate(record)

    async def list(
        self,
        tenant_id: UUID,
        *,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[ReturnResponse]:
        items, total = await self.return_repo.list_for_tenant(
            tenant_id,
            reference_type=reference_type,
            reference_id=reference_id,
            status=status,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return PaginatedResponse.create(
            [ReturnResponse.model_validate(r) for r in items], total, page, page_size
        )

    async def get(self, tenant_id: UUID, return_id: UUID) -> ReturnDetailResponse:
        record = await self.return_repo.get_with_details(tenant_id, return_id)
        if record is None:
            raise NotFoundError("Return", return_id)
        return ReturnDetailResponse.model_validate(record)

    async def _resolve_source(
        self, tenant_id: UUID, reference_type: str, reference_id: UUID
    ) -> dict:
        if reference_type == ReturnReferenceType.ORDER.value:
            order = await self.order_repo.get_with_details(tenant_id, reference_id)
            if order is None:
                raise NotFoundError("Order", reference_id)
            if order.status not in (
                OrderStatus.CONFIRMED.value,
                OrderStatus.PROCESSING.value,
                OrderStatus.SHIPPED.value,
                OrderStatus.DELIVERED.value,
            ):
                raise ValidationError("Order is not eligible for returns")
            return {
                "entity": order,
                "items": {item.id: item for item in order.items},
                "customer_id": order.customer_id,
                "branch_id": order.branch_id,
                "store_id": order.store_id,
            }

        if reference_type == ReturnReferenceType.SALE.value:
            sale = await self.sale_repo.get_with_details(tenant_id, reference_id)
            if sale is None:
                raise NotFoundError("Sale", reference_id)
            if sale.status != SaleStatus.COMPLETED.value:
                raise ValidationError("Only completed sales are eligible for returns")
            return {
                "entity": sale,
                "items": {item.id: item for item in sale.items},
                "customer_id": sale.customer_id,
                "branch_id": sale.branch_id,
                "store_id": sale.store_id,
            }

        raise ValidationError(f"Unsupported reference type: {reference_type}")

    def _build_return_item(
        self,
        tenant_id: UUID,
        return_id: UUID,
        source: dict,
        data: ReturnItemCreate,
    ) -> ReturnItem:
        line_item = source["items"].get(data.source_item_id)
        if line_item is None:
            raise NotFoundError("SourceItem", data.source_item_id)

        return ReturnItem(
            tenant_id=tenant_id,
            return_id=return_id,
            source_item_id=data.source_item_id,
            product_variant_id=line_item.product_variant_id,
            product_name=line_item.product_name,
            sku=line_item.sku,
            quantity_requested=data.quantity,
            unit_price=Decimal(str(line_item.unit_price)),
            reason=data.reason,
        )

    async def _validate_return_quantity(
        self,
        tenant_id: UUID,
        reference_type: str,
        reference_id: UUID,
        data: ReturnItemCreate,
        source: dict,
    ) -> None:
        line_item = source["items"].get(data.source_item_id)
        if line_item is None:
            raise NotFoundError("SourceItem", data.source_item_id)

        already_returned = await self.item_repo.sum_returned_for_source(
            tenant_id, reference_type, reference_id, data.source_item_id
        )
        max_qty = line_item.quantity - already_returned
        if data.quantity > max_qty:
            raise ValidationError(
                f"Return quantity {data.quantity} exceeds available {max_qty} for item"
            )

    async def _sync_payable_refund(self, record: Return) -> None:
        if record.reference_type == ReturnReferenceType.ORDER.value:
            order = await self.order_repo.get_by_id(record.reference_id)
            if order and order.tenant_id == record.tenant_id:
                order.status = OrderStatus.REFUNDED.value
                order.payment_status = PaymentStatus.REFUNDED.value
                await self.order_repo.update(order)
        elif record.reference_type == ReturnReferenceType.SALE.value:
            sale = await self.sale_repo.get_by_id(record.reference_id)
            if sale and sale.tenant_id == record.tenant_id:
                sale.payment_status = PaymentStatus.REFUNDED.value
                await self.sale_repo.update(sale)

    async def _get_or_raise(self, tenant_id: UUID, return_id: UUID) -> Return:
        record = await self.return_repo.get_with_details(tenant_id, return_id)
        if record is None:
            raise NotFoundError("Return", return_id)
        return record

    async def _generate_return_number(self, tenant_id: UUID) -> str:
        count = await self.return_repo.count_for_tenant(tenant_id)
        return f"RET-{count + 1:06d}"
