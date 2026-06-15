from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db, require_authenticated_user
from app.modules.procurement.schemas import (
    SupplierCreate,
    SupplierResponse,
    SupplierUpdate,
)
from app.modules.procurement.service import SupplierService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


def get_service(session: AsyncSession = Depends(get_db)) -> SupplierService:
    return SupplierService(session)


@router.post("", response_model=SupplierResponse, status_code=201)
async def create_supplier(
    data: SupplierCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: SupplierService = Depends(get_service),
) -> SupplierResponse:
    return await service.create(tenant_id, data)


@router.get("", response_model=PaginatedResponse[SupplierResponse])
async def list_suppliers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: SupplierService = Depends(get_service),
) -> PaginatedResponse[SupplierResponse]:
    return await service.list(tenant_id, page=page, page_size=page_size)


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: SupplierService = Depends(get_service),
) -> SupplierResponse:
    return await service.get(tenant_id, supplier_id)


@router.patch("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: UUID,
    data: SupplierUpdate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: SupplierService = Depends(get_service),
) -> SupplierResponse:
    return await service.update(tenant_id, supplier_id, data)


@router.delete("/{supplier_id}", status_code=204)
async def delete_supplier(
    supplier_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: SupplierService = Depends(get_service),
) -> None:
    await service.delete(tenant_id, supplier_id)
