from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.customers.models import Order
from app.modules.customers.repository import OrderRepository
from app.modules.pos.models import Sale
from app.modules.pos.repository import SaleRepository
from app.modules.promotions.models import Coupon, CouponUsage
from app.modules.promotions.repository import CouponRepository, CouponUsageRepository
from app.modules.promotions.schemas import (
    CouponApplyRequest,
    CouponApplyResponse,
    CouponCreate,
    CouponResponse,
    CouponUpdate,
    CouponUsageResponse,
    CouponValidateRequest,
    CouponValidateResponse,
)
from app.modules.stores.repository import StoreRepository
from app.shared.base_model import (
    CouponAppliesTo,
    CouponDiscountType,
    CouponUsageReferenceType,
    OrderStatus,
    SaleStatus,
)
from app.shared.schemas import PaginatedResponse


class CouponService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.coupon_repo = CouponRepository(session)
        self.usage_repo = CouponUsageRepository(session)
        self.order_repo = OrderRepository(session)
        self.sale_repo = SaleRepository(session)
        self.store_repo = StoreRepository(session)

    async def create(self, tenant_id: UUID, data: CouponCreate) -> CouponResponse:
        code = data.code.upper()
        if await self.coupon_repo.get_by_code(tenant_id, code):
            raise ConflictError(f"Coupon code '{code}' already exists")

        if data.store_id:
            store = await self.store_repo.get_by_id(data.store_id)
            if store is None or store.tenant_id != tenant_id:
                raise NotFoundError("Store", data.store_id)

        if data.ends_at and data.starts_at and data.ends_at <= data.starts_at:
            raise ValidationError("ends_at must be after starts_at")

        if data.discount_type == CouponDiscountType.PERCENTAGE and data.discount_value > 100:
            raise ValidationError("Percentage discount cannot exceed 100")

        coupon = Coupon(
            tenant_id=tenant_id,
            store_id=data.store_id,
            code=code,
            name=data.name,
            description=data.description,
            discount_type=data.discount_type.value,
            discount_value=data.discount_value,
            min_order_amount=data.min_order_amount,
            max_discount_amount=data.max_discount_amount,
            usage_limit=data.usage_limit,
            usage_limit_per_customer=data.usage_limit_per_customer,
            applies_to=data.applies_to.value,
            starts_at=data.starts_at,
            ends_at=data.ends_at,
            is_active=True,
        )
        coupon = await self.coupon_repo.create(coupon)
        return CouponResponse.model_validate(coupon)

    async def list(
        self,
        tenant_id: UUID,
        *,
        store_id: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[CouponResponse]:
        items, total = await self.coupon_repo.list_active(
            tenant_id, store_id=store_id, offset=(page - 1) * page_size, limit=page_size
        )
        return PaginatedResponse.create(
            [CouponResponse.model_validate(c) for c in items], total, page, page_size
        )

    async def get(self, tenant_id: UUID, coupon_id: UUID) -> CouponResponse:
        coupon = await self._get_or_raise(tenant_id, coupon_id)
        return CouponResponse.model_validate(coupon)

    async def update(
        self, tenant_id: UUID, coupon_id: UUID, data: CouponUpdate
    ) -> CouponResponse:
        coupon = await self._get_or_raise(tenant_id, coupon_id)
        update_data = data.model_dump(exclude_unset=True)
        if "applies_to" in update_data and update_data["applies_to"]:
            update_data["applies_to"] = update_data["applies_to"].value
        if "discount_value" in update_data and coupon.discount_type == CouponDiscountType.PERCENTAGE.value:
            if update_data["discount_value"] > 100:
                raise ValidationError("Percentage discount cannot exceed 100")
        for field, value in update_data.items():
            setattr(coupon, field, value)
        coupon = await self.coupon_repo.update(coupon)
        return CouponResponse.model_validate(coupon)

    async def validate(
        self, tenant_id: UUID, data: CouponValidateRequest
    ) -> CouponValidateResponse:
        coupon = await self._get_valid_coupon(
            tenant_id,
            data.code,
            subtotal=data.subtotal,
            customer_id=data.customer_id,
            applies_to=data.applies_to.value,
        )
        discount = self._calculate_discount(coupon, data.subtotal)
        return CouponValidateResponse(
            coupon_id=coupon.id,
            code=coupon.code,
            discount_type=coupon.discount_type,
            discount_amount=discount,
            message="Coupon is valid",
        )

    async def apply(
        self, tenant_id: UUID, data: CouponApplyRequest
    ) -> CouponApplyResponse:
        ref_type = data.reference_type.value
        payable = await self._resolve_payable(tenant_id, ref_type, data.reference_id)

        existing = await self.usage_repo.get_for_reference(
            tenant_id, ref_type, data.reference_id
        )
        if existing:
            raise ConflictError("A coupon has already been applied to this reference")

        customer_id = data.customer_id or payable["customer_id"]
        coupon = await self._get_valid_coupon(
            tenant_id,
            data.code,
            subtotal=payable["subtotal"],
            customer_id=customer_id,
            applies_to=payable["applies_to"],
        )
        discount = self._calculate_discount(coupon, payable["subtotal"])

        usage = CouponUsage(
            tenant_id=tenant_id,
            coupon_id=coupon.id,
            customer_id=customer_id,
            reference_type=ref_type,
            reference_id=data.reference_id,
            discount_amount=discount,
            used_at=datetime.now(UTC),
        )
        usage = await self.usage_repo.create(usage)

        coupon.used_count += 1
        await self.coupon_repo.update(coupon)

        await self._apply_discount_to_payable(payable["entity"], ref_type, discount)

        return CouponApplyResponse(
            coupon_id=coupon.id,
            code=coupon.code,
            discount_amount=discount,
            reference_type=ref_type,
            reference_id=data.reference_id,
            usage_id=usage.id,
        )

    async def list_usages(
        self,
        tenant_id: UUID,
        coupon_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[CouponUsageResponse]:
        await self._get_or_raise(tenant_id, coupon_id)
        items, total = await self.usage_repo.list_for_coupon(
            tenant_id, coupon_id, offset=(page - 1) * page_size, limit=page_size
        )
        return PaginatedResponse.create(
            [CouponUsageResponse.model_validate(u) for u in items], total, page, page_size
        )

    async def _get_valid_coupon(
        self,
        tenant_id: UUID,
        code: str,
        *,
        subtotal: Decimal,
        customer_id: UUID | None,
        applies_to: str,
    ) -> Coupon:
        coupon = await self.coupon_repo.get_by_code(tenant_id, code.upper())
        if coupon is None or not coupon.is_active:
            raise NotFoundError("Coupon", code)

        now = datetime.now(UTC)
        if coupon.starts_at and now < coupon.starts_at:
            raise ValidationError("Coupon is not yet active")
        if coupon.ends_at and now > coupon.ends_at:
            raise ValidationError("Coupon has expired")

        if coupon.applies_to != CouponAppliesTo.ALL.value and coupon.applies_to != applies_to:
            raise ValidationError(f"Coupon is not valid for {applies_to} orders")

        if coupon.min_order_amount is not None and subtotal < coupon.min_order_amount:
            raise ValidationError(
                f"Minimum order amount of {coupon.min_order_amount} not met"
            )

        if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
            raise ValidationError("Coupon usage limit reached")

        if customer_id and coupon.usage_limit_per_customer is not None:
            customer_uses = await self.usage_repo.count_for_customer(coupon.id, customer_id)
            if customer_uses >= coupon.usage_limit_per_customer:
                raise ValidationError("Customer usage limit reached for this coupon")

        return coupon

    @staticmethod
    def _calculate_discount(coupon: Coupon, subtotal: Decimal) -> Decimal:
        if coupon.discount_type == CouponDiscountType.PERCENTAGE.value:
            discount = subtotal * coupon.discount_value / Decimal("100")
            if coupon.max_discount_amount is not None:
                discount = min(discount, coupon.max_discount_amount)
        else:
            discount = coupon.discount_value

        return min(discount, subtotal).quantize(Decimal("0.01"))

    async def _resolve_payable(
        self, tenant_id: UUID, reference_type: str, reference_id: UUID
    ) -> dict:
        if reference_type == CouponUsageReferenceType.ORDER.value:
            order = await self.order_repo.get_by_id(reference_id)
            if order is None or order.tenant_id != tenant_id:
                raise NotFoundError("Order", reference_id)
            if order.status != OrderStatus.PENDING.value:
                raise ValidationError("Coupons can only be applied to pending orders")
            return {
                "entity": order,
                "subtotal": order.subtotal,
                "customer_id": order.customer_id,
                "applies_to": CouponAppliesTo.ONLINE.value,
            }

        if reference_type == CouponUsageReferenceType.SALE.value:
            sale = await self.sale_repo.get_by_id(reference_id)
            if sale is None or sale.tenant_id != tenant_id:
                raise NotFoundError("Sale", reference_id)
            if sale.status != SaleStatus.DRAFT.value:
                raise ValidationError("Coupons can only be applied to draft sales")
            return {
                "entity": sale,
                "subtotal": sale.subtotal,
                "customer_id": sale.customer_id,
                "applies_to": CouponAppliesTo.POS.value,
            }

        raise ValidationError(f"Unsupported reference type: {reference_type}")

    async def _apply_discount_to_payable(
        self, entity: Order | Sale, reference_type: str, discount: Decimal
    ) -> None:
        entity.discount_amount = discount
        if reference_type == CouponUsageReferenceType.ORDER.value:
            entity.total = entity.subtotal + entity.tax_amount + entity.shipping_amount - discount
            await self.order_repo.update(entity)
        else:
            entity.total = entity.subtotal + entity.tax_amount - discount
            await self.sale_repo.update(entity)

    async def _get_or_raise(self, tenant_id: UUID, coupon_id: UUID) -> Coupon:
        coupon = await self.coupon_repo.get_by_id(coupon_id)
        if coupon is None or coupon.tenant_id != tenant_id:
            raise NotFoundError("Coupon", coupon_id)
        return coupon
