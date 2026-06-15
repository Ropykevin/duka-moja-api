from uuid import UUID

from sqlalchemy import func, select, update

from app.modules.system.models import AuditLog, Media, Notification, WebhookEvent
from app.shared.base_model import WebhookEventStatus
from app.shared.base_repository import TenantScopedRepository


class NotificationRepository(TenantScopedRepository[Notification]):
    model = Notification

    async def list_for_user(
        self,
        tenant_id: UUID,
        user_id: UUID,
        *,
        unread_only: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Notification], int]:
        filters = [Notification.tenant_id == tenant_id, Notification.user_id == user_id]
        if unread_only:
            filters.append(Notification.is_read.is_(False))

        count_stmt = select(func.count()).select_from(Notification).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(Notification)
            .where(*filters)
            .offset(offset)
            .limit(limit)
            .order_by(Notification.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def mark_all_read(self, tenant_id: UUID, user_id: UUID) -> int:
        from datetime import UTC, datetime

        stmt = (
            update(Notification)
            .where(
                Notification.tenant_id == tenant_id,
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True, read_at=datetime.now(UTC))
        )
        result = await self.session.execute(stmt)
        return result.rowcount


class AuditLogRepository(TenantScopedRepository[AuditLog]):
    model = AuditLog

    async def list_for_tenant(
        self,
        tenant_id: UUID,
        *,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        user_id: UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[AuditLog], int]:
        filters = [AuditLog.tenant_id == tenant_id]
        if entity_type:
            filters.append(AuditLog.entity_type == entity_type)
        if entity_id:
            filters.append(AuditLog.entity_id == entity_id)
        if user_id:
            filters.append(AuditLog.user_id == user_id)

        count_stmt = select(func.count()).select_from(AuditLog).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(AuditLog)
            .where(*filters)
            .offset(offset)
            .limit(limit)
            .order_by(AuditLog.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total


class MediaRepository(TenantScopedRepository[Media]):
    model = Media

    async def list_for_entity(
        self,
        tenant_id: UUID,
        entity_type: str,
        entity_id: UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Media], int]:
        filters = [
            Media.tenant_id == tenant_id,
            Media.entity_type == entity_type,
            Media.entity_id == entity_id,
        ]
        count_stmt = select(func.count()).select_from(Media).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(Media)
            .where(*filters)
            .offset(offset)
            .limit(limit)
            .order_by(Media.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total


class WebhookEventRepository(TenantScopedRepository[WebhookEvent]):
    model = WebhookEvent

    async def list_pending(
        self, tenant_id: UUID, *, limit: int = 50
    ) -> list[WebhookEvent]:
        stmt = (
            select(WebhookEvent)
            .where(
                WebhookEvent.tenant_id == tenant_id,
                WebhookEvent.status == WebhookEventStatus.PENDING.value,
            )
            .order_by(WebhookEvent.created_at)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_tenant(
        self,
        tenant_id: UUID,
        *,
        event_type: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[WebhookEvent], int]:
        filters = [WebhookEvent.tenant_id == tenant_id]
        if event_type:
            filters.append(WebhookEvent.event_type == event_type)
        if status:
            filters.append(WebhookEvent.status == status)

        count_stmt = select(func.count()).select_from(WebhookEvent).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(WebhookEvent)
            .where(*filters)
            .offset(offset)
            .limit(limit)
            .order_by(WebhookEvent.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total
