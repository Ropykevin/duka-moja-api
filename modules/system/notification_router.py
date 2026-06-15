from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db, require_authenticated_user
from app.modules.system.schemas import NotificationCreate, NotificationResponse
from app.modules.system.service import NotificationService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def get_service(session: AsyncSession = Depends(get_db)) -> NotificationService:
    return NotificationService(session)


@router.post("", response_model=NotificationResponse, status_code=201)
async def create_notification(
    data: NotificationCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: NotificationService = Depends(get_service),
) -> NotificationResponse:
    return await service.create(tenant_id, data)


@router.get("", response_model=PaginatedResponse[NotificationResponse])
async def list_notifications(
    unread_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: NotificationService = Depends(get_service),
) -> PaginatedResponse[NotificationResponse]:
    return await service.list_for_user(
        tenant_id, user_id, unread_only=unread_only, page=page, page_size=page_size
    )


@router.post("/read-all", response_model=dict)
async def mark_all_notifications_read(
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: NotificationService = Depends(get_service),
) -> dict:
    count = await service.mark_all_read(tenant_id, user_id)
    return {"marked_read": count}


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: NotificationService = Depends(get_service),
) -> NotificationResponse:
    return await service.mark_read(tenant_id, user_id, notification_id)
