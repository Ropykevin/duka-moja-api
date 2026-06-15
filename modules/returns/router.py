from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db, require_authenticated_user
from app.modules.returns.schemas import (
    ReturnApproveRequest,
    ReturnCreate,
    ReturnDetailResponse,
    ReturnResponse,
)
from app.modules.returns.service import ReturnService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/returns", tags=["Returns"])


def get_service(session: AsyncSession = Depends(get_db)) -> ReturnService:
    return ReturnService(session)


@router.post("", response_model=ReturnDetailResponse, status_code=201)
async def create_return(
    data: ReturnCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: ReturnService = Depends(get_service),
) -> ReturnDetailResponse:
    return await service.create(tenant_id, data, requested_by=user_id)


@router.post("/{return_id}/approve", response_model=ReturnDetailResponse)
async def approve_return(
    return_id: UUID,
    data: ReturnApproveRequest | None = None,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: ReturnService = Depends(get_service),
) -> ReturnDetailResponse:
    return await service.approve(tenant_id, return_id, data, approved_by=user_id)


@router.post("/{return_id}/receive", response_model=ReturnDetailResponse)
async def receive_return(
    return_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: ReturnService = Depends(get_service),
) -> ReturnDetailResponse:
    """Receive returned goods and restore inventory via InventoryMovement."""
    return await service.receive(tenant_id, return_id, received_by=user_id)


@router.post("/{return_id}/refund", response_model=ReturnDetailResponse)
async def mark_return_refunded(
    return_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: ReturnService = Depends(get_service),
) -> ReturnDetailResponse:
    return await service.mark_refunded(tenant_id, return_id)


@router.post("/{return_id}/reject", response_model=ReturnDetailResponse)
async def reject_return(
    return_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: ReturnService = Depends(get_service),
) -> ReturnDetailResponse:
    return await service.reject(tenant_id, return_id)


@router.post("/{return_id}/cancel", response_model=ReturnDetailResponse)
async def cancel_return(
    return_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: ReturnService = Depends(get_service),
) -> ReturnDetailResponse:
    return await service.cancel(tenant_id, return_id)


@router.get("", response_model=PaginatedResponse[ReturnResponse])
async def list_returns(
    reference_type: str | None = Query(default=None),
    reference_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: ReturnService = Depends(get_service),
) -> PaginatedResponse[ReturnResponse]:
    return await service.list(
        tenant_id,
        reference_type=reference_type,
        reference_id=reference_id,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.get("/{return_id}", response_model=ReturnDetailResponse)
async def get_return(
    return_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: ReturnService = Depends(get_service),
) -> ReturnDetailResponse:
    return await service.get(tenant_id, return_id)
