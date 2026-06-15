from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.customers.models import Order
from app.modules.customers.repository import CustomerAddressRepository, OrderRepository
from app.modules.shipping.models import Shipment, ShippingMethod
from app.modules.shipping.repository import ShipmentRepository, ShippingMethodRepository
from app.modules.shipping.schemas import (
    ShipmentCreate,
    ShipmentDeliver,
    ShipmentDetailResponse,
    ShipmentResponse,
    ShipmentShip,
    ShippingMethodCreate,
    ShippingMethodResponse,
    ShippingMethodUpdate,
)
from app.modules.stores.repository import StoreRepository
from app.shared.base_model import OrderStatus, ShipmentStatus, ShippingMethodType
from app.shared.schemas import PaginatedResponse


class ShippingMethodService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ShippingMethodRepository(session)
        self.store_repo = StoreRepository(session)

    async def create(
        self, tenant_id: UUID, data: ShippingMethodCreate
    ) -> ShippingMethodResponse:
        if await self.repo.get_by_code(tenant_id, data.code):
            raise ConflictError(f"Shipping method code '{data.code}' already exists")

        if data.store_id:
            store = await self.store_repo.get_by_id(data.store_id)
            if store is None or store.tenant_id != tenant_id:
                raise NotFoundError("Store", data.store_id)

        method = ShippingMethod(
            tenant_id=tenant_id,
            store_id=data.store_id,
            name=data.name,
            code=data.code,
            method_type=data.method_type.value,
            carrier_name=data.carrier_name,
            base_cost=data.base_cost,
            free_shipping_threshold=data.free_shipping_threshold,
            estimated_days_min=data.estimated_days_min,
            estimated_days_max=data.estimated_days_max,
            is_active=True,
            sort_order=data.sort_order,
        )
        method = await self.repo.create(method)
        return ShippingMethodResponse.model_validate(method)

    async def list(
        self,
        tenant_id: UUID,
        *,
        store_id: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[ShippingMethodResponse]:
        items, total = await self.repo.list_for_store(
            tenant_id, store_id, offset=(page - 1) * page_size, limit=page_size
        )
        return PaginatedResponse.create(
            [ShippingMethodResponse.model_validate(m) for m in items], total, page, page_size
        )

    async def get(self, tenant_id: UUID, method_id: UUID) -> ShippingMethodResponse:
        method = await self._get_or_raise(tenant_id, method_id)
        return ShippingMethodResponse.model_validate(method)

    async def update(
        self, tenant_id: UUID, method_id: UUID, data: ShippingMethodUpdate
    ) -> ShippingMethodResponse:
        method = await self._get_or_raise(tenant_id, method_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(method, field, value)
        method = await self.repo.update(method)
        return ShippingMethodResponse.model_validate(method)

    async def _get_or_raise(self, tenant_id: UUID, method_id: UUID) -> ShippingMethod:
        method = await self.repo.get_by_id(method_id)
        if method is None or method.tenant_id != tenant_id:
            raise NotFoundError("ShippingMethod", method_id)
        return method


class ShipmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.shipment_repo = ShipmentRepository(session)
        self.method_repo = ShippingMethodRepository(session)
        self.order_repo = OrderRepository(session)
        self.address_repo = CustomerAddressRepository(session)

    async def create(self, tenant_id: UUID, data: ShipmentCreate) -> ShipmentDetailResponse:
        order = await self.order_repo.get_with_details(tenant_id, data.order_id)
        if order is None:
            raise NotFoundError("Order", data.order_id)

        if order.status not in (
            OrderStatus.CONFIRMED.value,
            OrderStatus.PROCESSING.value,
        ):
            raise ValidationError("Shipment can only be created for confirmed or processing orders")

        existing = await self.shipment_repo.get_active_for_order(tenant_id, order.id)
        if existing:
            raise ConflictError("An active shipment already exists for this order")

        method = await self.method_repo.get_by_id(data.shipping_method_id)
        if method is None or method.tenant_id != tenant_id or not method.is_active:
            raise NotFoundError("ShippingMethod", data.shipping_method_id)

        address_id = data.shipping_address_id or order.shipping_address_id
        if method.method_type != ShippingMethodType.PICKUP.value and not address_id:
            raise ValidationError("Shipping address is required for non-pickup methods")

        if address_id:
            address = await self.address_repo.get_by_id(address_id)
            if address is None or address.tenant_id != tenant_id:
                raise NotFoundError("CustomerAddress", address_id)
            if address.customer_id != order.customer_id:
                raise ValidationError("Shipping address does not belong to order customer")

        shipping_cost = self._calculate_shipping_cost(method, order)
        shipment_number = await self._generate_shipment_number(tenant_id)

        shipment = Shipment(
            tenant_id=tenant_id,
            shipment_number=shipment_number,
            order_id=order.id,
            shipping_method_id=method.id,
            shipping_address_id=address_id,
            status=ShipmentStatus.PENDING.value,
            tracking_number=data.tracking_number,
            carrier_name=method.carrier_name,
            shipping_cost=shipping_cost,
            notes=data.notes,
        )
        shipment = await self.shipment_repo.create(shipment)

        if order.status == OrderStatus.CONFIRMED.value:
            order.status = OrderStatus.PROCESSING.value
            await self.order_repo.update(order)

        shipment = await self.shipment_repo.get_with_details(tenant_id, shipment.id)
        return self._to_detail(shipment)

    async def ship(
        self, tenant_id: UUID, shipment_id: UUID, data: ShipmentShip | None = None
    ) -> ShipmentDetailResponse:
        shipment = await self._get_or_raise(tenant_id, shipment_id)
        if shipment.status not in (
            ShipmentStatus.PENDING.value,
            ShipmentStatus.PROCESSING.value,
        ):
            raise ValidationError("Shipment cannot be shipped in current status")

        if data:
            if data.tracking_number:
                shipment.tracking_number = data.tracking_number
            if data.carrier_name:
                shipment.carrier_name = data.carrier_name
            if data.notes:
                shipment.notes = data.notes

        shipment.status = ShipmentStatus.SHIPPED.value
        shipment.shipped_at = datetime.now(UTC)
        await self.shipment_repo.update(shipment)
        await self._sync_order_status(shipment.order_id, OrderStatus.SHIPPED)

        shipment = await self.shipment_repo.get_with_details(tenant_id, shipment.id)
        return self._to_detail(shipment)

    async def mark_in_transit(self, tenant_id: UUID, shipment_id: UUID) -> ShipmentDetailResponse:
        shipment = await self._get_or_raise(tenant_id, shipment_id)
        if shipment.status != ShipmentStatus.SHIPPED.value:
            raise ValidationError("Only shipped shipments can be marked in transit")

        shipment.status = ShipmentStatus.IN_TRANSIT.value
        await self.shipment_repo.update(shipment)

        shipment = await self.shipment_repo.get_with_details(tenant_id, shipment.id)
        return self._to_detail(shipment)

    async def deliver(
        self, tenant_id: UUID, shipment_id: UUID, data: ShipmentDeliver | None = None
    ) -> ShipmentDetailResponse:
        shipment = await self._get_or_raise(tenant_id, shipment_id)
        if shipment.status not in (
            ShipmentStatus.SHIPPED.value,
            ShipmentStatus.IN_TRANSIT.value,
        ):
            raise ValidationError("Shipment cannot be delivered in current status")

        if data and data.notes:
            shipment.notes = data.notes

        shipment.status = ShipmentStatus.DELIVERED.value
        shipment.delivered_at = datetime.now(UTC)
        await self.shipment_repo.update(shipment)
        await self._sync_order_status(shipment.order_id, OrderStatus.DELIVERED)

        shipment = await self.shipment_repo.get_with_details(tenant_id, shipment.id)
        return self._to_detail(shipment)

    async def cancel(self, tenant_id: UUID, shipment_id: UUID) -> ShipmentDetailResponse:
        shipment = await self._get_or_raise(tenant_id, shipment_id)
        if shipment.status in (
            ShipmentStatus.DELIVERED.value,
            ShipmentStatus.CANCELLED.value,
        ):
            raise ValidationError("Shipment cannot be cancelled in current status")

        shipment.status = ShipmentStatus.CANCELLED.value
        shipment.cancelled_at = datetime.now(UTC)
        await self.shipment_repo.update(shipment)

        order = await self.order_repo.get_by_id(shipment.order_id)
        if order and order.status == OrderStatus.PROCESSING.value:
            order.status = OrderStatus.CONFIRMED.value
            await self.order_repo.update(order)

        shipment = await self.shipment_repo.get_with_details(tenant_id, shipment.id)
        return self._to_detail(shipment)

    async def list(
        self,
        tenant_id: UUID,
        *,
        order_id: UUID | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[ShipmentResponse]:
        items, total = await self.shipment_repo.list_for_tenant(
            tenant_id,
            order_id=order_id,
            status=status,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return PaginatedResponse.create(
            [ShipmentResponse.model_validate(s) for s in items], total, page, page_size
        )

    async def get(self, tenant_id: UUID, shipment_id: UUID) -> ShipmentDetailResponse:
        shipment = await self.shipment_repo.get_with_details(tenant_id, shipment_id)
        if shipment is None:
            raise NotFoundError("Shipment", shipment_id)
        return self._to_detail(shipment)

    @staticmethod
    def _calculate_shipping_cost(method: ShippingMethod, order: Order) -> Decimal:
        if method.method_type == ShippingMethodType.FREE.value:
            return Decimal("0")
        if (
            method.free_shipping_threshold is not None
            and order.subtotal >= method.free_shipping_threshold
        ):
            return Decimal("0")
        return Decimal(str(method.base_cost))

    async def _sync_order_status(self, order_id: UUID, status: OrderStatus) -> None:
        order = await self.order_repo.get_by_id(order_id)
        if order is None:
            return
        order.status = status.value
        await self.order_repo.update(order)

    async def _get_or_raise(self, tenant_id: UUID, shipment_id: UUID) -> Shipment:
        shipment = await self.shipment_repo.get_by_id(shipment_id)
        if shipment is None or shipment.tenant_id != tenant_id:
            raise NotFoundError("Shipment", shipment_id)
        return shipment

    async def _generate_shipment_number(self, tenant_id: UUID) -> str:
        count = await self.shipment_repo.count_for_tenant(tenant_id)
        return f"SHP-{count + 1:06d}"

    @staticmethod
    def _to_detail(shipment: Shipment) -> ShipmentDetailResponse:
        response = ShipmentDetailResponse.model_validate(shipment)
        if shipment.shipping_method:
            response.shipping_method = ShippingMethodResponse.model_validate(
                shipment.shipping_method
            )
        return response
