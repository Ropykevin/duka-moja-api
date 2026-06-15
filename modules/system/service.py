from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.system.models import AuditLog, Media, Notification, WebhookEvent
from app.modules.system.repository import (
    AuditLogRepository,
    MediaRepository,
    NotificationRepository,
    WebhookEventRepository,
)
from app.modules.system.schemas import (
    AuditLogCreate,
    AuditLogResponse,
    MediaCreate,
    MediaResponse,
    NotificationCreate,
    NotificationResponse,
    WebhookEventCreate,
    WebhookEventResponse,
)
from app.shared.base_model import WebhookEventStatus
from app.shared.schemas import PaginatedResponse


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = NotificationRepository(session)

    async def create(
        self, tenant_id: UUID, data: NotificationCreate
    ) -> NotificationResponse:
        notification = Notification(
            tenant_id=tenant_id,
            user_id=data.user_id,
            channel=data.channel.value,
            notification_type=data.notification_type,
            title=data.title,
            body=data.body,
            reference_type=data.reference_type,
            reference_id=data.reference_id,
            is_read=False,
        )
        notification = await self.repo.create(notification)
        return NotificationResponse.model_validate(notification)

    async def list_for_user(
        self,
        tenant_id: UUID,
        user_id: UUID,
        *,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[NotificationResponse]:
        items, total = await self.repo.list_for_user(
            tenant_id,
            user_id,
            unread_only=unread_only,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return PaginatedResponse.create(
            [NotificationResponse.model_validate(n) for n in items], total, page, page_size
        )

    async def mark_read(
        self, tenant_id: UUID, user_id: UUID, notification_id: UUID
    ) -> NotificationResponse:
        notification = await self.repo.get_by_id(notification_id)
        if (
            notification is None
            or notification.tenant_id != tenant_id
            or notification.user_id != user_id
        ):
            raise NotFoundError("Notification", notification_id)

        notification.is_read = True
        notification.read_at = datetime.now(UTC)
        notification = await self.repo.update(notification)
        return NotificationResponse.model_validate(notification)

    async def mark_all_read(self, tenant_id: UUID, user_id: UUID) -> int:
        return await self.repo.mark_all_read(tenant_id, user_id)


class AuditLogService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AuditLogRepository(session)

    async def record(
        self,
        tenant_id: UUID,
        data: AuditLogCreate,
        *,
        user_id: UUID | None = None,
    ) -> AuditLogResponse:
        entry = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=data.action.value,
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            old_values=data.old_values,
            new_values=data.new_values,
            ip_address=data.ip_address,
            user_agent=data.user_agent,
            metadata_=data.metadata,
        )
        entry = await self.repo.create(entry)
        return AuditLogResponse.model_validate(entry)

    async def list(
        self,
        tenant_id: UUID,
        *,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        user_id: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[AuditLogResponse]:
        items, total = await self.repo.list_for_tenant(
            tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return PaginatedResponse.create(
            [AuditLogResponse.model_validate(a) for a in items], total, page, page_size
        )

    async def get(self, tenant_id: UUID, log_id: UUID) -> AuditLogResponse:
        entry = await self.repo.get_by_id(log_id)
        if entry is None or entry.tenant_id != tenant_id:
            raise NotFoundError("AuditLog", log_id)
        return AuditLogResponse.model_validate(entry)


class MediaService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = MediaRepository(session)

    async def create(
        self,
        tenant_id: UUID,
        data: MediaCreate,
        *,
        uploaded_by: UUID | None = None,
    ) -> MediaResponse:
        media = Media(
            tenant_id=tenant_id,
            filename=data.filename,
            original_filename=data.original_filename,
            mime_type=data.mime_type,
            file_size=data.file_size,
            url=data.url,
            storage_backend=data.storage_backend,
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            uploaded_by=uploaded_by,
        )
        media = await self.repo.create(media)
        return MediaResponse.model_validate(media)

    async def list_for_entity(
        self,
        tenant_id: UUID,
        entity_type: str,
        entity_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[MediaResponse]:
        items, total = await self.repo.list_for_entity(
            tenant_id,
            entity_type,
            entity_id,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return PaginatedResponse.create(
            [MediaResponse.model_validate(m) for m in items], total, page, page_size
        )

    async def get(self, tenant_id: UUID, media_id: UUID) -> MediaResponse:
        media = await self.repo.get_by_id(media_id)
        if media is None or media.tenant_id != tenant_id:
            raise NotFoundError("Media", media_id)
        return MediaResponse.model_validate(media)


class WebhookEventService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = WebhookEventRepository(session)

    async def emit(
        self, tenant_id: UUID, data: WebhookEventCreate
    ) -> WebhookEventResponse:
        event = WebhookEvent(
            tenant_id=tenant_id,
            event_type=data.event_type,
            target_url=data.target_url,
            payload=data.payload,
            status=WebhookEventStatus.PENDING.value,
            attempts=0,
        )
        event = await self.repo.create(event)
        return WebhookEventResponse.model_validate(event)

    async def list(
        self,
        tenant_id: UUID,
        *,
        event_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[WebhookEventResponse]:
        items, total = await self.repo.list_for_tenant(
            tenant_id,
            event_type=event_type,
            status=status,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return PaginatedResponse.create(
            [WebhookEventResponse.model_validate(e) for e in items], total, page, page_size
        )

    async def get(self, tenant_id: UUID, event_id: UUID) -> WebhookEventResponse:
        event = await self.repo.get_by_id(event_id)
        if event is None or event.tenant_id != tenant_id:
            raise NotFoundError("WebhookEvent", event_id)
        return WebhookEventResponse.model_validate(event)

    async def mark_delivered(
        self,
        tenant_id: UUID,
        event_id: UUID,
        *,
        response_status: int = 200,
    ) -> WebhookEventResponse:
        event = await self._get_or_raise(tenant_id, event_id)
        event.status = WebhookEventStatus.DELIVERED.value
        event.delivered_at = datetime.now(UTC)
        event.response_status = response_status
        event.attempts += 1
        event.last_attempt_at = datetime.now(UTC)
        event = await self.repo.update(event)
        return WebhookEventResponse.model_validate(event)

    async def mark_failed(
        self,
        tenant_id: UUID,
        event_id: UUID,
        *,
        error_message: str,
        response_status: int | None = None,
    ) -> WebhookEventResponse:
        event = await self._get_or_raise(tenant_id, event_id)
        event.status = WebhookEventStatus.FAILED.value
        event.error_message = error_message
        event.response_status = response_status
        event.attempts += 1
        event.last_attempt_at = datetime.now(UTC)
        event = await self.repo.update(event)
        return WebhookEventResponse.model_validate(event)

    async def retry(self, tenant_id: UUID, event_id: UUID) -> WebhookEventResponse:
        event = await self._get_or_raise(tenant_id, event_id)
        if event.status == WebhookEventStatus.DELIVERED.value:
            raise ValidationError("Delivered webhooks cannot be retried")
        event.status = WebhookEventStatus.PENDING.value
        event.error_message = None
        event = await self.repo.update(event)
        return WebhookEventResponse.model_validate(event)

    async def _get_or_raise(self, tenant_id: UUID, event_id: UUID) -> WebhookEvent:
        event = await self.repo.get_by_id(event_id)
        if event is None or event.tenant_id != tenant_id:
            raise NotFoundError("WebhookEvent", event_id)
        return event
