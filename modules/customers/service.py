from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.catalog.repository import ProductVariantRepository
from app.modules.customers.models import (
    Cart,
    CartItem,
    Customer,
    CustomerAddress,
    LoyaltyAccount,
    Order,
    OrderItem,
)
from app.modules.customers.repository import (
    CartItemRepository,
    CartRepository,
    CustomerAddressRepository,
    CustomerRepository,
    LoyaltyAccountRepository,
    OrderRepository,
)
from app.modules.customers.schemas import (
    CartItemAdd,
    CartItemResponse,
    CartItemUpdate,
    CartResponse,
    CustomerAddressCreate,
    CustomerAddressResponse,
    CustomerCreate,
    CustomerDetailResponse,
    CustomerResponse,
    CustomerUpdate,
    LoyaltyAccountResponse,
)
from app.modules.inventory.service import InventoryService
from app.modules.stores.repository import BranchRepository, StoreSettingsRepository
from app.shared.base_model import (
    CartStatus,
    CustomerStatus,
    InventoryMovementSource,
    LoyaltyTier,
    OrderStatus,
    PaymentStatus,
)
from app.shared.schemas import PaginatedResponse


class CustomerService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.customer_repo = CustomerRepository(session)
        self.address_repo = CustomerAddressRepository(session)
        self.loyalty_repo = LoyaltyAccountRepository(session)

    async def create(self, tenant_id: UUID, data: CustomerCreate) -> CustomerDetailResponse:
        if data.email and await self.customer_repo.get_by_email(tenant_id, str(data.email)):
            raise ConflictError(f"Customer with email '{data.email}' already exists")

        customer = Customer(
            tenant_id=tenant_id,
            email=str(data.email) if data.email else None,
            phone=data.phone,
            first_name=data.first_name,
            last_name=data.last_name,
            company_name=data.company_name,
            notes=data.notes,
            status=CustomerStatus.ACTIVE.value,
        )
        customer = await self.customer_repo.create(customer)

        loyalty = LoyaltyAccount(
            tenant_id=tenant_id,
            customer_id=customer.id,
            points_balance=0,
            lifetime_points=0,
            tier=LoyaltyTier.BRONZE.value,
            enrolled_at=datetime.now(UTC),
        )
        await self.loyalty_repo.create(loyalty)

        return await self.get(tenant_id, customer.id)

    async def list(
        self, tenant_id: UUID, *, page: int = 1, page_size: int = 20
    ) -> PaginatedResponse[CustomerResponse]:
        items, total = await self.customer_repo.list_for_tenant(
            tenant_id, offset=(page - 1) * page_size, limit=page_size
        )
        return PaginatedResponse.create(
            [CustomerResponse.model_validate(c) for c in items], total, page, page_size
        )

    async def get(self, tenant_id: UUID, customer_id: UUID) -> CustomerDetailResponse:
        customer = await self.customer_repo.get_with_details(tenant_id, customer_id)
        if customer is None:
            raise NotFoundError("Customer", customer_id)
        return CustomerDetailResponse.model_validate(customer)

    async def update(
        self, tenant_id: UUID, customer_id: UUID, data: CustomerUpdate
    ) -> CustomerDetailResponse:
        customer = await self._get_or_raise(tenant_id, customer_id)
        update_data = data.model_dump(exclude_unset=True)
        if "email" in update_data and update_data["email"]:
            existing = await self.customer_repo.get_by_email(tenant_id, str(update_data["email"]))
            if existing and existing.id != customer_id:
                raise ConflictError(f"Customer with email '{update_data['email']}' already exists")
            update_data["email"] = str(update_data["email"])
        if "status" in update_data and update_data["status"]:
            update_data["status"] = update_data["status"].value
        for field, value in update_data.items():
            setattr(customer, field, value)
        await self.customer_repo.update(customer)
        return await self.get(tenant_id, customer_id)

    async def add_address(
        self, tenant_id: UUID, customer_id: UUID, data: CustomerAddressCreate
    ) -> CustomerAddressResponse:
        await self._get_or_raise(tenant_id, customer_id)
        if data.is_default_shipping:
            await self.address_repo.clear_default_flags(customer_id, shipping=True)
        if data.is_default_billing:
            await self.address_repo.clear_default_flags(customer_id, billing=True)

        address = CustomerAddress(
            tenant_id=tenant_id,
            customer_id=customer_id,
            label=data.label,
            address_line1=data.address_line1,
            address_line2=data.address_line2,
            city=data.city,
            state=data.state,
            postal_code=data.postal_code,
            country=data.country,
            phone=data.phone,
            is_default_shipping=data.is_default_shipping,
            is_default_billing=data.is_default_billing,
        )
        address = await self.address_repo.create(address)
        return CustomerAddressResponse.model_validate(address)

    async def _get_or_raise(self, tenant_id: UUID, customer_id: UUID) -> Customer:
        customer = await self.customer_repo.get_by_id(customer_id)
        if customer is None or customer.tenant_id != tenant_id:
            raise NotFoundError("Customer", customer_id)
        return customer


class CartService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.cart_repo = CartRepository(session)
        self.cart_item_repo = CartItemRepository(session)
        self.variant_repo = ProductVariantRepository(session)
        self.customer_repo = CustomerRepository(session)
        self.branch_repo = BranchRepository(session)

    async def get_or_create_cart(
        self, tenant_id: UUID, customer_id: UUID, *, branch_id: UUID | None = None
    ) -> CartResponse:
        customer = await self.customer_repo.get_by_id(customer_id)
        if customer is None or customer.tenant_id != tenant_id:
            raise NotFoundError("Customer", customer_id)

        cart = await self.cart_repo.get_active_for_customer(tenant_id, customer_id)
        if cart is None:
            cart = Cart(
                tenant_id=tenant_id,
                customer_id=customer_id,
                branch_id=branch_id,
                status=CartStatus.ACTIVE.value,
            )
            cart = await self.cart_repo.create(cart)
            cart.items = []

        return self._to_response(cart)

    async def get_cart(self, tenant_id: UUID, cart_id: UUID) -> CartResponse:
        cart = await self.cart_repo.get_with_items(tenant_id, cart_id)
        if cart is None:
            raise NotFoundError("Cart", cart_id)
        return self._to_response(cart)

    async def add_item(
        self, tenant_id: UUID, cart_id: UUID, data: CartItemAdd
    ) -> CartResponse:
        cart = await self.cart_repo.get_with_items(tenant_id, cart_id)
        if cart is None:
            raise NotFoundError("Cart", cart_id)
        if cart.status != CartStatus.ACTIVE.value:
            raise ValidationError("Cannot modify a non-active cart")

        variant = await self.variant_repo.get_by_id(data.product_variant_id)
        if variant is None or variant.tenant_id != tenant_id:
            raise NotFoundError("ProductVariant", data.product_variant_id)

        unit_price = variant.price
        line_total = unit_price * data.quantity

        existing = await self.cart_item_repo.get_by_cart_and_variant(
            cart_id, data.product_variant_id
        )
        if existing:
            existing.quantity += data.quantity
            existing.line_total = existing.unit_price * existing.quantity
            await self.cart_item_repo.update(existing)
        else:
            item = CartItem(
                tenant_id=tenant_id,
                cart_id=cart_id,
                product_variant_id=data.product_variant_id,
                quantity=data.quantity,
                unit_price=unit_price,
                line_total=line_total,
            )
            await self.cart_item_repo.create(item)

        cart = await self.cart_repo.get_with_items(tenant_id, cart_id)
        return self._to_response(cart)

    async def update_item(
        self, tenant_id: UUID, cart_id: UUID, item_id: UUID, data: CartItemUpdate
    ) -> CartResponse:
        cart = await self._get_active_cart(tenant_id, cart_id)
        item = await self.cart_item_repo.get_by_id(item_id)
        if item is None or item.cart_id != cart.id:
            raise NotFoundError("CartItem", item_id)

        item.quantity = data.quantity
        item.line_total = item.unit_price * data.quantity
        await self.cart_item_repo.update(item)

        cart = await self.cart_repo.get_with_items(tenant_id, cart_id)
        return self._to_response(cart)

    async def remove_item(
        self, tenant_id: UUID, cart_id: UUID, item_id: UUID
    ) -> CartResponse:
        cart = await self._get_active_cart(tenant_id, cart_id)
        item = await self.cart_item_repo.get_by_id(item_id)
        if item is None or item.cart_id != cart.id:
            raise NotFoundError("CartItem", item_id)
        await self.cart_item_repo.delete(item)

        cart = await self.cart_repo.get_with_items(tenant_id, cart_id)
        return self._to_response(cart)

    async def _get_active_cart(self, tenant_id: UUID, cart_id: UUID) -> Cart:
        cart = await self.cart_repo.get_with_items(tenant_id, cart_id)
        if cart is None:
            raise NotFoundError("Cart", cart_id)
        if cart.status != CartStatus.ACTIVE.value:
            raise ValidationError("Cannot modify a non-active cart")
        return cart

    @staticmethod
    def _to_response(cart: Cart) -> CartResponse:
        subtotal = sum((item.line_total for item in cart.items), Decimal("0"))
        item_count = sum(item.quantity for item in cart.items)
        response = CartResponse.model_validate(cart)
        response.subtotal = subtotal
        response.item_count = item_count
        return response


class OrderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.order_repo = OrderRepository(session)
        self.cart_repo = CartRepository(session)
        self.customer_repo = CustomerRepository(session)
        self.branch_repo = BranchRepository(session)
        self.variant_repo = ProductVariantRepository(session)
        self.settings_repo = StoreSettingsRepository(session)
        self.inventory_service = InventoryService(session)

    async def checkout(self, tenant_id: UUID, data) -> "OrderDetailResponse":
        from app.modules.customers.schemas import CheckoutRequest, OrderDetailResponse, OrderResponse

        cart = await self.cart_repo.get_with_items(tenant_id, data.cart_id)
        if cart is None:
            raise NotFoundError("Cart", data.cart_id)
        if cart.status != CartStatus.ACTIVE.value:
            raise ValidationError("Cart is not active")
        if not cart.items:
            raise ValidationError("Cart is empty")

        customer = await self.customer_repo.get_by_id(data.customer_id)
        if customer is None or customer.tenant_id != tenant_id:
            raise NotFoundError("Customer", data.customer_id)

        branch = await self.branch_repo.get_by_id(data.branch_id)
        if branch is None or branch.tenant_id != tenant_id:
            raise NotFoundError("Branch", data.branch_id)

        tax_rate = await self._get_tax_rate(tenant_id, branch.store_id)
        order_number = await self._generate_order_number(tenant_id)

        subtotal = Decimal("0")
        tax_amount = Decimal("0")
        order_items: list[OrderItem] = []

        for cart_item in cart.items:
            variant = await self.variant_repo.get_by_id(cart_item.product_variant_id)
            if variant is None:
                raise NotFoundError("ProductVariant", cart_item.product_variant_id)

            line_subtotal = cart_item.unit_price * cart_item.quantity
            line_tax = line_subtotal * tax_rate / Decimal("100")
            line_total = line_subtotal + line_tax
            subtotal += line_subtotal
            tax_amount += line_tax

            order_items.append(
                OrderItem(
                    tenant_id=tenant_id,
                    product_variant_id=variant.id,
                    product_name=variant.name,
                    sku=variant.sku,
                    quantity=cart_item.quantity,
                    unit_price=cart_item.unit_price,
                    tax_rate=tax_rate,
                    line_total=line_total,
                )
            )

        total = subtotal + tax_amount + data.shipping_amount - data.discount_amount

        order = Order(
            tenant_id=tenant_id,
            order_number=order_number,
            customer_id=data.customer_id,
            branch_id=data.branch_id,
            store_id=branch.store_id,
            cart_id=cart.id,
            status=OrderStatus.PENDING.value,
            payment_status=PaymentStatus.PENDING.value,
            subtotal=subtotal,
            tax_amount=tax_amount,
            shipping_amount=data.shipping_amount,
            discount_amount=data.discount_amount,
            total=total,
            shipping_address_id=data.shipping_address_id,
            billing_address_id=data.billing_address_id,
            notes=data.notes,
        )
        order = await self.order_repo.create(order)

        for item in order_items:
            item.order_id = order.id
            self.session.add(item)

        cart.status = CartStatus.CONVERTED.value
        await self.cart_repo.update(cart)

        await self.session.flush()
        order = await self.order_repo.get_with_details(tenant_id, order.id)
        return OrderDetailResponse.model_validate(order)

    async def list(
        self,
        tenant_id: UUID,
        *,
        customer_id: UUID | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse:
        from app.modules.customers.schemas import OrderResponse

        items, total = await self.order_repo.list_for_tenant(
            tenant_id,
            customer_id=customer_id,
            status=status,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return PaginatedResponse.create(
            [OrderResponse.model_validate(o) for o in items], total, page, page_size
        )

    async def get(self, tenant_id: UUID, order_id: UUID):
        from app.modules.customers.schemas import OrderDetailResponse

        order = await self.order_repo.get_with_details(tenant_id, order_id)
        if order is None:
            raise NotFoundError("Order", order_id)
        return OrderDetailResponse.model_validate(order)

    async def confirm(
        self, tenant_id: UUID, order_id: UUID, *, confirmed_by: UUID | None = None
    ):
        from app.modules.customers.schemas import OrderDetailResponse

        order = await self.order_repo.get_with_details(tenant_id, order_id)
        if order is None:
            raise NotFoundError("Order", order_id)
        if order.status != OrderStatus.PENDING.value:
            raise ValidationError("Only pending orders can be confirmed")

        for item in order.items:
            await self.inventory_service.record_movement(
                tenant_id,
                order.branch_id,
                item.product_variant_id,
                InventoryMovementSource.ONLINE_SALE,
                -item.quantity,
                reference_type="order",
                reference_id=order.id,
                notes=f"Order {order.order_number} confirmed",
                created_by=confirmed_by,
            )

        order.status = OrderStatus.CONFIRMED.value
        order.confirmed_at = datetime.now(UTC)
        await self.order_repo.update(order)

        order = await self.order_repo.get_with_details(tenant_id, order.id)
        return OrderDetailResponse.model_validate(order)

    async def cancel(self, tenant_id: UUID, order_id: UUID):
        from app.modules.customers.schemas import OrderDetailResponse

        order = await self.order_repo.get_with_details(tenant_id, order_id)
        if order is None:
            raise NotFoundError("Order", order_id)
        if order.status not in (OrderStatus.PENDING.value, OrderStatus.CONFIRMED.value):
            raise ValidationError("Order cannot be cancelled in current status")

        if order.status == OrderStatus.CONFIRMED.value:
            for item in order.items:
                await self.inventory_service.record_movement(
                    tenant_id,
                    order.branch_id,
                    item.product_variant_id,
                    InventoryMovementSource.RETURN,
                    item.quantity,
                    reference_type="order",
                    reference_id=order.id,
                    notes=f"Order {order.order_number} cancelled — stock restored",
                )

        order.status = OrderStatus.CANCELLED.value
        await self.order_repo.update(order)
        order = await self.order_repo.get_with_details(tenant_id, order.id)
        return OrderDetailResponse.model_validate(order)

    async def _generate_order_number(self, tenant_id: UUID) -> str:
        count = await self.order_repo.count_for_tenant(tenant_id)
        return f"ORD-{count + 1:06d}"

    async def _get_tax_rate(self, tenant_id: UUID, store_id: UUID) -> Decimal:
        settings = await self.settings_repo.get_by_store_id(tenant_id, store_id)
        return Decimal(str(settings.tax_rate)) if settings else Decimal("0")
