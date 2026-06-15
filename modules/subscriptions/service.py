from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.subscriptions.schemas import (
    SubscriptionWithFeaturesResponse,
    UpgradeSubscriptionRequest,
)
from app.modules.tenants.models import Subscription, SubscriptionPlan
from app.modules.tenants.repository import SubscriptionPlanRepository, SubscriptionRepository
from app.modules.tenants.schemas import SubscriptionPlanResponse, SubscriptionResponse
from app.shared.base_model import BillingCycle, SubscriptionStatus


class SubscriptionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.subscription_repo = SubscriptionRepository(session)
        self.plan_repo = SubscriptionPlanRepository(session)
        self.settings = get_settings()

    async def list_plans(self) -> list[SubscriptionPlanResponse]:
        plans = await self.plan_repo.list_active()
        return [SubscriptionPlanResponse.model_validate(p) for p in plans]

    async def get_current_subscription(
        self, tenant_id: UUID
    ) -> SubscriptionWithFeaturesResponse:
        subscription = await self.subscription_repo.get_active_for_tenant(tenant_id)
        if subscription is None:
            raise NotFoundError("Subscription", f"tenant:{tenant_id}")

        enabled_features = self._extract_enabled_features(subscription.plan)
        response = SubscriptionWithFeaturesResponse.model_validate(subscription)
        response.enabled_features = enabled_features
        return response

    async def create_trial_subscription(
        self, tenant_id: UUID, plan_id: UUID
    ) -> Subscription:
        plan = await self.plan_repo.get_by_id_or_raise(plan_id)
        now = datetime.now(UTC)
        trial_days = plan.trial_days or self.settings.trial_period_days
        period_end = now + timedelta(days=trial_days)

        subscription = Subscription(
            tenant_id=tenant_id,
            plan_id=plan.id,
            status=SubscriptionStatus.TRIAL.value,
            billing_cycle=BillingCycle.MONTHLY.value,
            started_at=now,
            current_period_start=now,
            current_period_end=period_end,
            trial_ends_at=period_end,
        )
        return await self.subscription_repo.create(subscription)

    async def upgrade_subscription(
        self, tenant_id: UUID, data: UpgradeSubscriptionRequest
    ) -> SubscriptionResponse:
        current = await self.subscription_repo.get_active_for_tenant(tenant_id)
        if current is None:
            raise NotFoundError("Subscription", f"tenant:{tenant_id}")

        new_plan = await self.plan_repo.get_by_code(data.plan_code)
        if new_plan is None:
            raise NotFoundError("SubscriptionPlan", data.plan_code)

        if not new_plan.is_active:
            raise ValidationError(f"Plan '{data.plan_code}' is not available")

        if current.plan_id == new_plan.id and current.billing_cycle == data.billing_cycle.value:
            raise ConflictError("Already subscribed to this plan and billing cycle")

        now = datetime.now(UTC)
        period_days = 365 if data.billing_cycle == BillingCycle.YEARLY else 30

        current.plan_id = new_plan.id
        current.billing_cycle = data.billing_cycle.value
        current.status = SubscriptionStatus.ACTIVE.value
        current.current_period_start = now
        current.current_period_end = now + timedelta(days=period_days)
        current.trial_ends_at = None
        current.grace_period_ends_at = None
        current.cancelled_at = None
        current.suspended_at = None

        updated = await self.subscription_repo.update(current)
        return SubscriptionResponse.model_validate(updated)

    async def cancel_subscription(self, tenant_id: UUID) -> SubscriptionResponse:
        subscription = await self.subscription_repo.get_active_for_tenant(tenant_id)
        if subscription is None:
            raise NotFoundError("Subscription", f"tenant:{tenant_id}")

        now = datetime.now(UTC)
        subscription.status = SubscriptionStatus.CANCELLED.value
        subscription.cancelled_at = now
        updated = await self.subscription_repo.update(subscription)
        return SubscriptionResponse.model_validate(updated)

    async def tenant_has_feature(self, tenant_id: UUID, feature_code: str) -> bool:
        subscription = await self.subscription_repo.get_active_for_tenant(tenant_id)
        if subscription is None:
            return False
        features = self._extract_enabled_features(subscription.plan)
        return feature_code in features

    def _extract_enabled_features(self, plan: SubscriptionPlan) -> list[str]:
        if plan is None:
            return []
        return [
            pf.feature.code
            for pf in plan.features
            if pf.is_enabled and pf.feature is not None
        ]
