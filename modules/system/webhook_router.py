from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db
from app.modules.system.schemas import WebhookEventCreate, WebhookEventResponse
from app.modules.system.service import WebhookEventService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/webhooks/events", tags=["Webhook Events"])


def get_service(session: AsyncSession = Depends(get_db)) -> WebhookEventService:
    return WebhookEventService(session)


@router.post("", response_model=WebhookEventResponse, status_code=201)
async def emit_webhook_event(
    data: WebhookEventCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: WebhookEventService = Depends(get_service),
) -> WebhookEventResponse:
    return await service.emit(tenant_id, data)


@router.get("", response_model=PaginatedResponse[WebhookEventResponse])
async def list_webhook_events(
    event_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: WebhookEventService = Depends(get_service),
) -> PaginatedResponse[WebhookEventResponse]:
    return await service.list(
        tenant_id, event_type=event_type, status=status, page=page, page_size=page_size
    )


@router.get("/{event_id}", response_model=WebhookEventResponse)
async def get_webhook_event(
    event_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: WebhookEventService = Depends(get_service),
) -> WebhookEventResponse:
    return await service.get(tenant_id, event_id)


@router.post("/{event_id}/retry", response_model=WebhookEventResponse)
async def retry_webhook_event(
    event_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: WebhookEventService = Depends(get_service),
) -> WebhookEventResponse:
    return await service.retry(tenant_id, event_id)


@router.post("/{event_id}/delivered", response_model=WebhookEventResponse)
async def mark_webhook_delivered(
    event_id: UUID,
    response_status: int = Query(default=200),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: WebhookEventService = Depends(get_service),
) -> WebhookEventResponse:
    return await service.mark_delivered(tenant_id, event_id, response_status=response_status)
