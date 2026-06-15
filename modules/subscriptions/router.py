from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db
from app.modules.subscriptions.schemas import (
    PlanListResponse,
    SubscriptionWithFeaturesResponse,
    UpgradeSubscriptionRequest,
)
from app.modules.subscriptions.service import SubscriptionService
from app.modules.tenants.schemas import SubscriptionPlanResponse, SubscriptionResponse

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


def get_subscription_service(session: AsyncSession = Depends(get_db)) -> SubscriptionService:
    return SubscriptionService(session)


@router.get("/plans", response_model=PlanListResponse)
async def list_plans(
    service: SubscriptionService = Depends(get_subscription_service),
) -> PlanListResponse:
    """List all active subscription plans with features."""
    plans = await service.list_plans()
    return PlanListResponse(items=plans)


@router.get("/current", response_model=SubscriptionWithFeaturesResponse)
async def get_current_subscription(
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionWithFeaturesResponse:
    """Get the current tenant's active subscription."""
    return await service.get_current_subscription(tenant_id)


@router.post("/upgrade", response_model=SubscriptionResponse)
async def upgrade_subscription(
    data: UpgradeSubscriptionRequest,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    """Upgrade or change the current subscription plan."""
    return await service.upgrade_subscription(tenant_id, data)


@router.post("/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    """Cancel the current subscription."""
    return await service.cancel_subscription(tenant_id)
