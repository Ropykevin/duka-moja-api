from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db
from app.modules.catalog.schemas import (
    ProductCreate,
    ProductDetailResponse,
    ProductImageCreate,
    ProductImageResponse,
    ProductResponse,
    ProductUpdate,
    ProductVariantCreate,
    ProductVariantResponse,
    ProductVariantUpdate,
)
from app.modules.catalog.service import ProductService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/products", tags=["Products"])


def get_service(session: AsyncSession = Depends(get_db)) -> ProductService:
    return ProductService(session)


@router.post("", response_model=ProductDetailResponse, status_code=201)
async def create_product(
    data: ProductCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: ProductService = Depends(get_service),
) -> ProductDetailResponse:
    return await service.create(tenant_id, data)


@router.get("", response_model=PaginatedResponse[ProductResponse])
async def list_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category_id: UUID | None = Query(default=None),
    brand_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: ProductService = Depends(get_service),
) -> PaginatedResponse[ProductResponse]:
    return await service.list(
        tenant_id,
        page=page,
        page_size=page_size,
        category_id=category_id,
        brand_id=brand_id,
        status=status,
        search=search,
    )


@router.get("/{product_id}", response_model=ProductDetailResponse)
async def get_product(
    product_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: ProductService = Depends(get_service),
) -> ProductDetailResponse:
    return await service.get(tenant_id, product_id)


@router.patch("/{product_id}", response_model=ProductDetailResponse)
async def update_product(
    product_id: UUID,
    data: ProductUpdate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: ProductService = Depends(get_service),
) -> ProductDetailResponse:
    return await service.update(tenant_id, product_id, data)


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: ProductService = Depends(get_service),
) -> None:
    await service.delete(tenant_id, product_id)


@router.post("/{product_id}/variants", response_model=ProductVariantResponse, status_code=201)
async def add_variant(
    product_id: UUID,
    data: ProductVariantCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: ProductService = Depends(get_service),
) -> ProductVariantResponse:
    return await service.add_variant(tenant_id, product_id, data)


@router.patch(
    "/{product_id}/variants/{variant_id}",
    response_model=ProductVariantResponse,
)
async def update_variant(
    product_id: UUID,
    variant_id: UUID,
    data: ProductVariantUpdate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: ProductService = Depends(get_service),
) -> ProductVariantResponse:
    return await service.update_variant(tenant_id, product_id, variant_id, data)


@router.post("/{product_id}/images", response_model=ProductImageResponse, status_code=201)
async def add_image(
    product_id: UUID,
    data: ProductImageCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: ProductService = Depends(get_service),
) -> ProductImageResponse:
    return await service.add_image(tenant_id, product_id, data)
