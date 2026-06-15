from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db
from app.modules.catalog.schemas import BrandCreate, BrandResponse, BrandUpdate
from app.modules.catalog.service import BrandService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/brands", tags=["Brands"])


def get_service(session: AsyncSession = Depends(get_db)) -> BrandService:
    return BrandService(session)


@router.post("", response_model=BrandResponse, status_code=201)
async def create_brand(
    data: BrandCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: BrandService = Depends(get_service),
) -> BrandResponse:
    return await service.create(tenant_id, data)


@router.get("", response_model=PaginatedResponse[BrandResponse])
async def list_brands(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: BrandService = Depends(get_service),
) -> PaginatedResponse[BrandResponse]:
    return await service.list(tenant_id, page=page, page_size=page_size)


@router.get("/{brand_id}", response_model=BrandResponse)
async def get_brand(
    brand_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: BrandService = Depends(get_service),
) -> BrandResponse:
    return await service.get(tenant_id, brand_id)


@router.patch("/{brand_id}", response_model=BrandResponse)
async def update_brand(
    brand_id: UUID,
    data: BrandUpdate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: BrandService = Depends(get_service),
) -> BrandResponse:
    return await service.update(tenant_id, brand_id, data)


@router.delete("/{brand_id}", status_code=204)
async def delete_brand(
    brand_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: BrandService = Depends(get_service),
) -> None:
    await service.delete(tenant_id, brand_id)
