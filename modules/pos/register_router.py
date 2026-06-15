from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db, require_authenticated_user
from app.modules.pos.schemas import CashRegisterCreate, CashRegisterResponse, CashRegisterUpdate
from app.modules.pos.service import CashRegisterService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/cash-registers", tags=["Cash Registers"])


def get_service(session: AsyncSession = Depends(get_db)) -> CashRegisterService:
    return CashRegisterService(session)


@router.post("", response_model=CashRegisterResponse, status_code=201)
async def create_register(
    data: CashRegisterCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CashRegisterService = Depends(get_service),
) -> CashRegisterResponse:
    return await service.create(tenant_id, data)


@router.get("", response_model=PaginatedResponse[CashRegisterResponse])
async def list_registers(
    branch_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CashRegisterService = Depends(get_service),
) -> PaginatedResponse[CashRegisterResponse]:
    return await service.list(tenant_id, branch_id=branch_id, page=page, page_size=page_size)


@router.get("/{register_id}", response_model=CashRegisterResponse)
async def get_register(
    register_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CashRegisterService = Depends(get_service),
) -> CashRegisterResponse:
    return await service.get(tenant_id, register_id)


@router.patch("/{register_id}", response_model=CashRegisterResponse)
async def update_register(
    register_id: UUID,
    data: CashRegisterUpdate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CashRegisterService = Depends(get_service),
) -> CashRegisterResponse:
    return await service.update(tenant_id, register_id, data)
