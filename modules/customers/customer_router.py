from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db
from app.modules.customers.schemas import (
    CustomerAddressCreate,
    CustomerAddressResponse,
    CustomerCreate,
    CustomerDetailResponse,
    CustomerResponse,
    CustomerUpdate,
)
from app.modules.customers.service import CustomerService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/customers", tags=["Customers"])


def get_service(session: AsyncSession = Depends(get_db)) -> CustomerService:
    return CustomerService(session)


@router.post("", response_model=CustomerDetailResponse, status_code=201)
async def create_customer(
    data: CustomerCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CustomerService = Depends(get_service),
) -> CustomerDetailResponse:
    return await service.create(tenant_id, data)


@router.get("", response_model=PaginatedResponse[CustomerResponse])
async def list_customers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CustomerService = Depends(get_service),
) -> PaginatedResponse[CustomerResponse]:
    return await service.list(tenant_id, page=page, page_size=page_size)


@router.get("/{customer_id}", response_model=CustomerDetailResponse)
async def get_customer(
    customer_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CustomerService = Depends(get_service),
) -> CustomerDetailResponse:
    return await service.get(tenant_id, customer_id)


@router.patch("/{customer_id}", response_model=CustomerDetailResponse)
async def update_customer(
    customer_id: UUID,
    data: CustomerUpdate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CustomerService = Depends(get_service),
) -> CustomerDetailResponse:
    return await service.update(tenant_id, customer_id, data)


@router.post("/{customer_id}/addresses", response_model=CustomerAddressResponse, status_code=201)
async def add_customer_address(
    customer_id: UUID,
    data: CustomerAddressCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CustomerService = Depends(get_service),
) -> CustomerAddressResponse:
    return await service.add_address(tenant_id, customer_id, data)
