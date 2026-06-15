from uuid import UUID

from pydantic import Field

from app.modules.tenants.schemas import SubscriptionPlanResponse, SubscriptionResponse
from app.shared.base_model import BillingCycle
from app.shared.schemas import BaseSchema


class UpgradeSubscriptionRequest(BaseSchema):
    plan_code: str = Field(min_length=1, max_length=50)
    billing_cycle: BillingCycle = BillingCycle.MONTHLY


class CancelSubscriptionRequest(BaseSchema):
    reason: str | None = Field(default=None, max_length=500)


class SubscriptionWithFeaturesResponse(SubscriptionResponse):
    enabled_features: list[str] = []


class PlanListResponse(BaseSchema):
    items: list[SubscriptionPlanResponse]
