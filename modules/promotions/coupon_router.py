from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db
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
from app.modules.promotions.service import CouponService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/coupons", tags=["Coupons"])


def get_service(session: AsyncSession = Depends(get_db)) -> CouponService:
    return CouponService(session)


@router.post("", response_model=CouponResponse, status_code=201)
async def create_coupon(
    data: CouponCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CouponService = Depends(get_service),
) -> CouponResponse:
    return await service.create(tenant_id, data)


@router.get("", response_model=PaginatedResponse[CouponResponse])
async def list_coupons(
    store_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CouponService = Depends(get_service),
) -> PaginatedResponse[CouponResponse]:
    return await service.list(tenant_id, store_id=store_id, page=page, page_size=page_size)


@router.post("/validate", response_model=CouponValidateResponse)
async def validate_coupon(
    data: CouponValidateRequest,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CouponService = Depends(get_service),
) -> CouponValidateResponse:
    """Preview discount without applying the coupon."""
    return await service.validate(tenant_id, data)


@router.post("/apply", response_model=CouponApplyResponse)
async def apply_coupon(
    data: CouponApplyRequest,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CouponService = Depends(get_service),
) -> CouponApplyResponse:
    """Apply coupon to a pending order or draft sale."""
    return await service.apply(tenant_id, data)


@router.get("/{coupon_id}", response_model=CouponResponse)
async def get_coupon(
    coupon_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CouponService = Depends(get_service),
) -> CouponResponse:
    return await service.get(tenant_id, coupon_id)


@router.patch("/{coupon_id}", response_model=CouponResponse)
async def update_coupon(
    coupon_id: UUID,
    data: CouponUpdate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CouponService = Depends(get_service),
) -> CouponResponse:
    return await service.update(tenant_id, coupon_id, data)


@router.get("/{coupon_id}/usages", response_model=PaginatedResponse[CouponUsageResponse])
async def list_coupon_usages(
    coupon_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CouponService = Depends(get_service),
) -> PaginatedResponse[CouponUsageResponse]:
    return await service.list_usages(tenant_id, coupon_id, page=page, page_size=page_size)
