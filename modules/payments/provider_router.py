from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db
from app.modules.payments.schemas import (
    PaymentProviderCreate,
    PaymentProviderResponse,
    PaymentProviderUpdate,
)
from app.modules.payments.service import PaymentProviderService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/payment-providers", tags=["Payment Providers"])


def get_service(session: AsyncSession = Depends(get_db)) -> PaymentProviderService:
    return PaymentProviderService(session)


@router.post("", response_model=PaymentProviderResponse, status_code=201)
async def create_provider(
    data: PaymentProviderCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: PaymentProviderService = Depends(get_service),
) -> PaymentProviderResponse:
    return await service.create(tenant_id, data)


@router.get("", response_model=PaginatedResponse[PaymentProviderResponse])
async def list_providers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: PaymentProviderService = Depends(get_service),
) -> PaginatedResponse[PaymentProviderResponse]:
    return await service.list(tenant_id, page=page, page_size=page_size)


@router.get("/{provider_id}", response_model=PaymentProviderResponse)
async def get_provider(
    provider_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: PaymentProviderService = Depends(get_service),
) -> PaymentProviderResponse:
    return await service.get(tenant_id, provider_id)


@router.patch("/{provider_id}", response_model=PaymentProviderResponse)
async def update_provider(
    provider_id: UUID,
    data: PaymentProviderUpdate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: PaymentProviderService = Depends(get_service),
) -> PaymentProviderResponse:
    return await service.update(tenant_id, provider_id, data)
