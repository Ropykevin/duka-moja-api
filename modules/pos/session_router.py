from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db, require_authenticated_user
from app.modules.pos.schemas import CashSessionClose, CashSessionOpen, CashSessionResponse
from app.modules.pos.service import CashSessionService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/cash-sessions", tags=["Cash Sessions"])


def get_service(session: AsyncSession = Depends(get_db)) -> CashSessionService:
    return CashSessionService(session)


@router.post("/open", response_model=CashSessionResponse, status_code=201)
async def open_session(
    data: CashSessionOpen,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: CashSessionService = Depends(get_service),
) -> CashSessionResponse:
    """Open a cashier shift on a register."""
    return await service.open(tenant_id, data, opened_by=user_id)


@router.post("/{session_id}/close", response_model=CashSessionResponse)
async def close_session(
    session_id: UUID,
    data: CashSessionClose,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: CashSessionService = Depends(get_service),
) -> CashSessionResponse:
    """Close session with cash reconciliation."""
    return await service.close(tenant_id, session_id, data, closed_by=user_id)


@router.get("/active", response_model=CashSessionResponse | None)
async def get_active_session(
    register_id: UUID = Query(...),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CashSessionService = Depends(get_service),
) -> CashSessionResponse | None:
    return await service.get_active(tenant_id, register_id)


@router.get("", response_model=PaginatedResponse[CashSessionResponse])
async def list_sessions(
    register_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CashSessionService = Depends(get_service),
) -> PaginatedResponse[CashSessionResponse]:
    return await service.list(
        tenant_id, register_id=register_id, status=status, page=page, page_size=page_size
    )


@router.get("/{session_id}", response_model=CashSessionResponse)
async def get_session(
    session_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CashSessionService = Depends(get_service),
) -> CashSessionResponse:
    return await service.get(tenant_id, session_id)
