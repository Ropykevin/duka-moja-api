from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db, require_authenticated_user
from app.modules.system.schemas import AuditLogCreate, AuditLogResponse
from app.modules.system.service import AuditLogService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


def get_service(session: AsyncSession = Depends(get_db)) -> AuditLogService:
    return AuditLogService(session)


@router.post("", response_model=AuditLogResponse, status_code=201)
async def record_audit_log(
    data: AuditLogCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: AuditLogService = Depends(get_service),
) -> AuditLogResponse:
    return await service.record(tenant_id, data, user_id=user_id)


@router.get("", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs(
    entity_type: str | None = Query(default=None),
    entity_id: UUID | None = Query(default=None),
    user_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: AuditLogService = Depends(get_service),
) -> PaginatedResponse[AuditLogResponse]:
    return await service.list(
        tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        page=page,
        page_size=page_size,
    )


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: AuditLogService = Depends(get_service),
) -> AuditLogResponse:
    return await service.get(tenant_id, log_id)
