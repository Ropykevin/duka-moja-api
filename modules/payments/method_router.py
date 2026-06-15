from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db
from app.modules.payments.schemas import (
    MerchantPaymentMethodCreate,
    MerchantPaymentMethodResponse,
    MerchantPaymentMethodUpdate,
)
from app.modules.payments.service import MerchantPaymentMethodService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/payment-methods", tags=["Payment Methods"])


def get_service(session: AsyncSession = Depends(get_db)) -> MerchantPaymentMethodService:
    return MerchantPaymentMethodService(session)


@router.post("", response_model=MerchantPaymentMethodResponse, status_code=201)
async def create_method(
    data: MerchantPaymentMethodCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: MerchantPaymentMethodService = Depends(get_service),
) -> MerchantPaymentMethodResponse:
    return await service.create(tenant_id, data)


@router.get("", response_model=PaginatedResponse[MerchantPaymentMethodResponse])
async def list_methods(
    store_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: MerchantPaymentMethodService = Depends(get_service),
) -> PaginatedResponse[MerchantPaymentMethodResponse]:
    return await service.list(tenant_id, store_id=store_id, page=page, page_size=page_size)


@router.get("/{method_id}", response_model=MerchantPaymentMethodResponse)
async def get_method(
    method_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: MerchantPaymentMethodService = Depends(get_service),
) -> MerchantPaymentMethodResponse:
    return await service.get(tenant_id, method_id)


@router.patch("/{method_id}", response_model=MerchantPaymentMethodResponse)
async def update_method(
    method_id: UUID,
    data: MerchantPaymentMethodUpdate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: MerchantPaymentMethodService = Depends(get_service),
) -> MerchantPaymentMethodResponse:
    return await service.update(tenant_id, method_id, data)
