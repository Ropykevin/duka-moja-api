from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from app.modules.customers.models import (
    Cart,
    CartItem,
    Customer,
    CustomerAddress,
    LoyaltyAccount,
    Order,
    OrderItem,
)
from app.shared.base_model import CartStatus
from app.shared.base_repository import TenantScopedRepository


class CustomerRepository(TenantScopedRepository[Customer]):
    model = Customer

    async def get_by_email(self, tenant_id: UUID, email: str) -> Customer | None:
        stmt = select(Customer).where(
            Customer.tenant_id == tenant_id, Customer.email == email
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_details(self, tenant_id: UUID, customer_id: UUID) -> Customer | None:
        stmt = (
            select(Customer)
            .where(Customer.tenant_id == tenant_id, Customer.id == customer_id)
            .options(
                selectinload(Customer.addresses),
                selectinload(Customer.loyalty_account),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class CustomerAddressRepository(TenantScopedRepository[CustomerAddress]):
    model = CustomerAddress

    async def clear_default_flags(
        self,
        customer_id: UUID,
        *,
        shipping: bool = False,
        billing: bool = False,
        exclude_id: UUID | None = None,
    ) -> None:
        if shipping:
            stmt = update(CustomerAddress).where(
                CustomerAddress.customer_id == customer_id,
                CustomerAddress.is_default_shipping.is_(True),
            )
            if exclude_id:
                stmt = stmt.where(CustomerAddress.id != exclude_id)
            await self.session.execute(stmt.values(is_default_shipping=False))
        if billing:
            stmt = update(CustomerAddress).where(
                CustomerAddress.customer_id == customer_id,
                CustomerAddress.is_default_billing.is_(True),
            )
            if exclude_id:
                stmt = stmt.where(CustomerAddress.id != exclude_id)
            await self.session.execute(stmt.values(is_default_billing=False))


class LoyaltyAccountRepository(TenantScopedRepository[LoyaltyAccount]):
    model = LoyaltyAccount

    async def get_by_customer(self, tenant_id: UUID, customer_id: UUID) -> LoyaltyAccount | None:
        stmt = select(LoyaltyAccount).where(
            LoyaltyAccount.tenant_id == tenant_id,
            LoyaltyAccount.customer_id == customer_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class CartRepository(TenantScopedRepository[Cart]):
    model = Cart

    async def get_active_for_customer(
        self, tenant_id: UUID, customer_id: UUID
    ) -> Cart | None:
        stmt = (
            select(Cart)
            .where(
                Cart.tenant_id == tenant_id,
                Cart.customer_id == customer_id,
                Cart.status == CartStatus.ACTIVE.value,
            )
            .options(selectinload(Cart.items))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_items(self, tenant_id: UUID, cart_id: UUID) -> Cart | None:
        stmt = (
            select(Cart)
            .where(Cart.tenant_id == tenant_id, Cart.id == cart_id)
            .options(selectinload(Cart.items))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class CartItemRepository(TenantScopedRepository[CartItem]):
    model = CartItem

    async def get_by_cart_and_variant(
        self, cart_id: UUID, variant_id: UUID
    ) -> CartItem | None:
        stmt = select(CartItem).where(
            CartItem.cart_id == cart_id,
            CartItem.product_variant_id == variant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class OrderRepository(TenantScopedRepository[Order]):
    model = Order

    async def get_with_details(self, tenant_id: UUID, order_id: UUID) -> Order | None:
        stmt = (
            select(Order)
            .where(Order.tenant_id == tenant_id, Order.id == order_id)
            .options(selectinload(Order.items), selectinload(Order.customer))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_for_tenant(self, tenant_id: UUID) -> int:
        stmt = select(func.count()).select_from(Order).where(Order.tenant_id == tenant_id)
        return (await self.session.execute(stmt)).scalar_one()

    async def list_for_tenant(
        self,
        tenant_id: UUID,
        *,
        customer_id: UUID | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Order], int]:
        filters = [Order.tenant_id == tenant_id]
        if customer_id:
            filters.append(Order.customer_id == customer_id)
        if status:
            filters.append(Order.status == status)

        count_stmt = select(func.count()).select_from(Order).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(Order)
            .where(*filters)
            .options(selectinload(Order.items))
            .offset(offset)
            .limit(limit)
            .order_by(Order.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total


class OrderItemRepository(TenantScopedRepository[OrderItem]):
    model = OrderItem
