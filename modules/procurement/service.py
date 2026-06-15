from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.catalog.repository import ProductVariantRepository
from app.modules.inventory.service import InventoryService
from app.modules.procurement.models import PurchaseOrder, PurchaseOrderItem, Supplier
from app.modules.procurement.repository import (
    PurchaseOrderRepository,
    SupplierRepository,
)
from app.modules.procurement.schemas import (
    PurchaseOrderCreate,
    PurchaseOrderItemResponse,
    PurchaseOrderResponse,
    ReceivePurchaseOrderRequest,
    SupplierCreate,
    SupplierResponse,
    SupplierUpdate,
)
from app.modules.stores.repository import BranchRepository
from app.shared.base_model import InventoryMovementSource, PurchaseOrderStatus
from app.shared.schemas import PaginatedResponse


class SupplierService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = SupplierRepository(session)

    async def create(self, tenant_id: UUID, data: SupplierCreate) -> SupplierResponse:
        if await self.repo.get_by_code(tenant_id, data.code):
            raise ConflictError(f"Supplier code '{data.code}' already exists")

        supplier = Supplier(
            tenant_id=tenant_id,
            name=data.name,
            code=data.code,
            email=str(data.email) if data.email else None,
            phone=data.phone,
            contact_person=data.contact_person,
            address_line1=data.address_line1,
            address_line2=data.address_line2,
            city=data.city,
            state=data.state,
            postal_code=data.postal_code,
            country=data.country,
            payment_terms=data.payment_terms,
            notes=data.notes,
            is_active=data.is_active,
        )
        supplier = await self.repo.create(supplier)
        return SupplierResponse.model_validate(supplier)

    async def list(
        self, tenant_id: UUID, *, page: int = 1, page_size: int = 20
    ) -> PaginatedResponse[SupplierResponse]:
        items, total = await self.repo.list_active(
            tenant_id, offset=(page - 1) * page_size, limit=page_size
        )
        return PaginatedResponse.create(
            [SupplierResponse.model_validate(s) for s in items], total, page, page_size
        )

    async def get(self, tenant_id: UUID, supplier_id: UUID) -> SupplierResponse:
        supplier = await self._get_or_raise(tenant_id, supplier_id)
        return SupplierResponse.model_validate(supplier)

    async def update(
        self, tenant_id: UUID, supplier_id: UUID, data: SupplierUpdate
    ) -> SupplierResponse:
        supplier = await self._get_or_raise(tenant_id, supplier_id)
        update_data = data.model_dump(exclude_unset=True)
        if "email" in update_data and update_data["email"] is not None:
            update_data["email"] = str(update_data["email"])
        for field, value in update_data.items():
            setattr(supplier, field, value)
        supplier = await self.repo.update(supplier)
        return SupplierResponse.model_validate(supplier)

    async def delete(self, tenant_id: UUID, supplier_id: UUID) -> None:
        supplier = await self._get_or_raise(tenant_id, supplier_id)
        supplier.is_active = False
        await self.repo.update(supplier)

    async def _get_or_raise(self, tenant_id: UUID, supplier_id: UUID) -> Supplier:
        supplier = await self.repo.get_by_id(supplier_id)
        if supplier is None or supplier.tenant_id != tenant_id:
            raise NotFoundError("Supplier", supplier_id)
        return supplier


class PurchaseOrderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.po_repo = PurchaseOrderRepository(session)
        self.supplier_repo = SupplierRepository(session)
        self.branch_repo = BranchRepository(session)
        self.variant_repo = ProductVariantRepository(session)
        self.inventory_service = InventoryService(session)

    async def create(
        self,
        tenant_id: UUID,
        data: PurchaseOrderCreate,
        *,
        created_by: UUID | None = None,
    ) -> PurchaseOrderResponse:
        supplier = await self.supplier_repo.get_by_id(data.supplier_id)
        if supplier is None or supplier.tenant_id != tenant_id or not supplier.is_active:
            raise NotFoundError("Supplier", data.supplier_id)

        branch = await self.branch_repo.get_by_id(data.branch_id)
        if branch is None or branch.tenant_id != tenant_id:
            raise NotFoundError("Branch", data.branch_id)

        for item in data.items:
            variant = await self.variant_repo.get_by_id(item.product_variant_id)
            if variant is None or variant.tenant_id != tenant_id:
                raise NotFoundError("ProductVariant", item.product_variant_id)

        po_number = await self._generate_po_number(tenant_id)
        subtotal, tax_amount, total = self._calculate_totals(data.items)

        po = PurchaseOrder(
            tenant_id=tenant_id,
            po_number=po_number,
            supplier_id=data.supplier_id,
            branch_id=data.branch_id,
            status=PurchaseOrderStatus.DRAFT.value,
            order_date=data.order_date or date.today(),
            expected_delivery_date=data.expected_delivery_date,
            notes=data.notes,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total=total,
            created_by=created_by,
        )
        po = await self.po_repo.create(po)

        for item_data in data.items:
            line_subtotal = item_data.unit_cost * item_data.quantity_ordered
            line_tax = line_subtotal * item_data.tax_rate / Decimal("100")
            line_total = line_subtotal + line_tax
            po_item = PurchaseOrderItem(
                tenant_id=tenant_id,
                purchase_order_id=po.id,
                product_variant_id=item_data.product_variant_id,
                quantity_ordered=item_data.quantity_ordered,
                unit_cost=item_data.unit_cost,
                tax_rate=item_data.tax_rate,
                line_total=line_total,
            )
            self.session.add(po_item)

        await self.session.flush()
        po = await self.po_repo.get_with_details(tenant_id, po.id)
        return self._to_response(po)

    async def list(
        self,
        tenant_id: UUID,
        *,
        supplier_id: UUID | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[PurchaseOrderResponse]:
        items, total = await self.po_repo.list_for_tenant(
            tenant_id,
            supplier_id=supplier_id,
            status=status,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return PaginatedResponse.create(
            [self._to_response(po) for po in items], total, page, page_size
        )

    async def get(self, tenant_id: UUID, po_id: UUID) -> PurchaseOrderResponse:
        po = await self._get_or_raise(tenant_id, po_id)
        return self._to_response(po)

    async def submit(self, tenant_id: UUID, po_id: UUID) -> PurchaseOrderResponse:
        po = await self._get_or_raise(tenant_id, po_id)
        if po.status != PurchaseOrderStatus.DRAFT.value:
            raise ValidationError("Only draft purchase orders can be submitted")
        po.status = PurchaseOrderStatus.SUBMITTED.value
        po = await self.po_repo.update(po)
        return self._to_response(po)

    async def approve(
        self, tenant_id: UUID, po_id: UUID, *, approved_by: UUID | None = None
    ) -> PurchaseOrderResponse:
        po = await self._get_or_raise(tenant_id, po_id)
        if po.status != PurchaseOrderStatus.SUBMITTED.value:
            raise ValidationError("Only submitted purchase orders can be approved")
        po.status = PurchaseOrderStatus.APPROVED.value
        po.approved_by = approved_by
        po.approved_at = datetime.now(UTC)
        po = await self.po_repo.update(po)
        return self._to_response(po)

    async def receive(
        self,
        tenant_id: UUID,
        po_id: UUID,
        data: ReceivePurchaseOrderRequest,
        *,
        received_by: UUID | None = None,
    ) -> PurchaseOrderResponse:
        po = await self._get_or_raise(tenant_id, po_id)
        if po.status not in (
            PurchaseOrderStatus.APPROVED.value,
            PurchaseOrderStatus.PARTIAL_RECEIVED.value,
        ):
            raise ValidationError("Only approved purchase orders can be received")

        item_map = {item.id: item for item in po.items}

        for receive_item in data.items:
            po_item = item_map.get(receive_item.item_id)
            if po_item is None:
                raise NotFoundError("PurchaseOrderItem", receive_item.item_id)

            remaining = po_item.quantity_ordered - po_item.quantity_received
            if receive_item.quantity > remaining:
                raise ValidationError(
                    f"Cannot receive {receive_item.quantity} units. "
                    f"Only {remaining} remaining for item {po_item.id}"
                )

            await self.inventory_service.record_movement(
                tenant_id,
                po.branch_id,
                po_item.product_variant_id,
                InventoryMovementSource.PURCHASE,
                receive_item.quantity,
                reference_type="purchase_order",
                reference_id=po.id,
                notes=f"PO {po.po_number} goods received",
                created_by=received_by,
            )

            po_item.quantity_received += receive_item.quantity

        all_received = all(
            item.quantity_received >= item.quantity_ordered for item in po.items
        )
        any_received = any(item.quantity_received > 0 for item in po.items)

        if all_received:
            po.status = PurchaseOrderStatus.RECEIVED.value
            po.received_at = datetime.now(UTC)
        elif any_received:
            po.status = PurchaseOrderStatus.PARTIAL_RECEIVED.value

        po = await self.po_repo.update(po)
        po = await self.po_repo.get_with_details(tenant_id, po.id)
        return self._to_response(po)

    async def cancel(self, tenant_id: UUID, po_id: UUID) -> PurchaseOrderResponse:
        po = await self._get_or_raise(tenant_id, po_id)
        if po.status in (
            PurchaseOrderStatus.RECEIVED.value,
            PurchaseOrderStatus.CANCELLED.value,
        ):
            raise ValidationError("Purchase order cannot be cancelled in current status")
        if po.status == PurchaseOrderStatus.PARTIAL_RECEIVED.value:
            raise ValidationError("Partially received purchase orders cannot be cancelled")
        po.status = PurchaseOrderStatus.CANCELLED.value
        po = await self.po_repo.update(po)
        return self._to_response(po)

    async def _get_or_raise(self, tenant_id: UUID, po_id: UUID) -> PurchaseOrder:
        po = await self.po_repo.get_with_details(tenant_id, po_id)
        if po is None:
            raise NotFoundError("PurchaseOrder", po_id)
        return po

    async def _generate_po_number(self, tenant_id: UUID) -> str:
        count = await self.po_repo.count_for_tenant(tenant_id)
        return f"PO-{count + 1:06d}"

    @staticmethod
    def _calculate_totals(items) -> tuple[Decimal, Decimal, Decimal]:
        subtotal = Decimal("0")
        tax_amount = Decimal("0")
        for item in items:
            line_subtotal = item.unit_cost * item.quantity_ordered
            line_tax = line_subtotal * item.tax_rate / Decimal("100")
            subtotal += line_subtotal
            tax_amount += line_tax
        return subtotal, tax_amount, subtotal + tax_amount

    @staticmethod
    def _to_response(po: PurchaseOrder) -> PurchaseOrderResponse:
        items = [
            PurchaseOrderItemResponse.model_validate(item).model_copy(
                update={
                    "quantity_remaining": item.quantity_ordered - item.quantity_received
                }
            )
            for item in po.items
        ]
        response = PurchaseOrderResponse.model_validate(po)
        response.items = items
        return response
