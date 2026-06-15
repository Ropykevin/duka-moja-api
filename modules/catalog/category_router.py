from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db
from app.modules.catalog.schemas import (
    CategoryCreate,
    CategoryResponse,
    CategoryTreeResponse,
    CategoryUpdate,
)
from app.modules.catalog.service import CategoryService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/categories", tags=["Categories"])


def get_service(session: AsyncSession = Depends(get_db)) -> CategoryService:
    return CategoryService(session)


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(
    data: CategoryCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CategoryService = Depends(get_service),
) -> CategoryResponse:
    return await service.create(tenant_id, data)


@router.get("/tree", response_model=list[CategoryTreeResponse])
async def get_category_tree(
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CategoryService = Depends(get_service),
) -> list[CategoryTreeResponse]:
    return await service.list_tree(tenant_id)


@router.get("", response_model=PaginatedResponse[CategoryResponse])
async def list_categories(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CategoryService = Depends(get_service),
) -> PaginatedResponse[CategoryResponse]:
    return await service.list_flat(tenant_id, page=page, page_size=page_size)


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CategoryService = Depends(get_service),
) -> CategoryResponse:
    return await service.get(tenant_id, category_id)


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    data: CategoryUpdate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CategoryService = Depends(get_service),
) -> CategoryResponse:
    return await service.update(tenant_id, category_id, data)


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CategoryService = Depends(get_service),
) -> None:
    await service.delete(tenant_id, category_id)
