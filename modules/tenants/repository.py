from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modules.tenants.models import (
    Feature,
    PlanFeature,
    Subscription,
    SubscriptionPlan,
    Tenant,
)
from app.shared.base_repository import BaseRepository


class TenantRepository(BaseRepository[Tenant]):
    model = Tenant

    async def get_by_slug(self, slug: str) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class SubscriptionPlanRepository(BaseRepository[SubscriptionPlan]):
    model = SubscriptionPlan

    async def get_by_code(self, code: str) -> SubscriptionPlan | None:
        stmt = (
            select(SubscriptionPlan)
            .where(SubscriptionPlan.code == code)
            .options(
                selectinload(SubscriptionPlan.features).selectinload(PlanFeature.feature)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(self) -> list[SubscriptionPlan]:
        stmt = (
            select(SubscriptionPlan)
            .where(SubscriptionPlan.is_active.is_(True))
            .options(
                selectinload(SubscriptionPlan.features).selectinload(PlanFeature.feature)
            )
            .order_by(SubscriptionPlan.sort_order)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class FeatureRepository(BaseRepository[Feature]):
    model = Feature

    async def get_by_code(self, code: str) -> Feature | None:
        stmt = select(Feature).where(Feature.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class SubscriptionRepository(BaseRepository[Subscription]):
    model = Subscription

    async def get_active_for_tenant(self, tenant_id: UUID) -> Subscription | None:
        active_statuses = ("trial", "active", "past_due", "grace_period")
        stmt = (
            select(Subscription)
            .where(
                Subscription.tenant_id == tenant_id,
                Subscription.status.in_(active_statuses),
            )
            .options(
                selectinload(Subscription.plan)
                .selectinload(SubscriptionPlan.features)
                .selectinload(PlanFeature.feature)
            )
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_tenant(self, tenant_id: UUID) -> list[Subscription]:
        stmt = (
            select(Subscription)
            .where(Subscription.tenant_id == tenant_id)
            .options(selectinload(Subscription.plan))
            .order_by(Subscription.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
