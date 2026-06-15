from uuid import UUID

from sqlalchemy import func, select

from app.modules.promotions.models import Coupon, CouponUsage
from app.shared.base_repository import TenantScopedRepository


class CouponRepository(TenantScopedRepository[Coupon]):
    model = Coupon

    async def get_by_code(self, tenant_id: UUID, code: str) -> Coupon | None:
        stmt = select(Coupon).where(
            Coupon.tenant_id == tenant_id, Coupon.code == code.upper()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(
        self,
        tenant_id: UUID,
        *,
        store_id: UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Coupon], int]:
        filters = [Coupon.tenant_id == tenant_id, Coupon.is_active.is_(True)]
        if store_id:
            filters.append((Coupon.store_id == store_id) | (Coupon.store_id.is_(None)))

        count_stmt = select(func.count()).select_from(Coupon).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(Coupon)
            .where(*filters)
            .offset(offset)
            .limit(limit)
            .order_by(Coupon.code)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total


class CouponUsageRepository(TenantScopedRepository[CouponUsage]):
    model = CouponUsage

    async def count_for_coupon(self, coupon_id: UUID) -> int:
        stmt = select(func.count()).select_from(CouponUsage).where(
            CouponUsage.coupon_id == coupon_id
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def count_for_customer(self, coupon_id: UUID, customer_id: UUID) -> int:
        stmt = select(func.count()).select_from(CouponUsage).where(
            CouponUsage.coupon_id == coupon_id,
            CouponUsage.customer_id == customer_id,
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def get_for_reference(
        self, tenant_id: UUID, reference_type: str, reference_id: UUID
    ) -> CouponUsage | None:
        stmt = select(CouponUsage).where(
            CouponUsage.tenant_id == tenant_id,
            CouponUsage.reference_type == reference_type,
            CouponUsage.reference_id == reference_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_coupon(
        self, tenant_id: UUID, coupon_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> tuple[list[CouponUsage], int]:
        filters = [CouponUsage.tenant_id == tenant_id, CouponUsage.coupon_id == coupon_id]
        count_stmt = select(func.count()).select_from(CouponUsage).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(CouponUsage)
            .where(*filters)
            .offset(offset)
            .limit(limit)
            .order_by(CouponUsage.used_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total
