from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db, require_authenticated_user
from app.modules.pos.schemas import (
    SaleComplete,
    SaleCreate,
    SaleDetailResponse,
    SaleItemAdd,
    SaleResponse,
)
from app.modules.pos.service import SaleService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/sales", tags=["POS Sales"])


def get_service(session: AsyncSession = Depends(get_db)) -> SaleService:
    return SaleService(session)


@router.post("", response_model=SaleDetailResponse, status_code=201)
async def create_sale(
    data: SaleCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: SaleService = Depends(get_service),
) -> SaleDetailResponse:
    """Create a draft POS sale with line items."""
    return await service.create(tenant_id, data, cashier_id=user_id)


@router.post("/{sale_id}/items", response_model=SaleDetailResponse)
async def add_sale_item(
    sale_id: UUID,
    data: SaleItemAdd,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: SaleService = Depends(get_service),
) -> SaleDetailResponse:
    return await service.add_item(tenant_id, sale_id, data)


@router.post("/{sale_id}/complete", response_model=SaleDetailResponse)
async def complete_sale(
    sale_id: UUID,
    data: SaleComplete | None = None,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: SaleService = Depends(get_service),
) -> SaleDetailResponse:
    """Complete sale and deduct inventory via InventoryMovement."""
    return await service.complete(tenant_id, sale_id, data, completed_by=user_id)


@router.post("/{sale_id}/void", response_model=SaleDetailResponse)
async def void_sale(
    sale_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: SaleService = Depends(get_service),
) -> SaleDetailResponse:
    """Void a completed sale and restore stock."""
    return await service.void(tenant_id, sale_id, voided_by=user_id)


@router.get("", response_model=PaginatedResponse[SaleResponse])
async def list_sales(
    session_id: UUID | None = Query(default=None),
    register_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: SaleService = Depends(get_service),
) -> PaginatedResponse[SaleResponse]:
    return await service.list(
        tenant_id,
        session_id=session_id,
        register_id=register_id,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.get("/{sale_id}", response_model=SaleDetailResponse)
async def get_sale(
    sale_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: SaleService = Depends(get_service),
) -> SaleDetailResponse:
    return await service.get(tenant_id, sale_id)
