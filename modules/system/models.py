import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import (
    NotificationChannel,
    TenantScopedModel,
    WebhookEventStatus,
)
from app.shared.types import GUID


class Notification(TenantScopedModel):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    channel: Mapped[str] = mapped_column(
        String(20), nullable=False, default=NotificationChannel.IN_APP.value
    )
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(TenantScopedModel):
    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True, index=True)
    old_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)


class Media(TenantScopedModel):
    __tablename__ = "media"

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(20), default="local", nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True, index=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class WebhookEvent(TenantScopedModel):
    __tablename__ = "webhook_events"

    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_url: Mapped[str] = mapped_column(String(500), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=WebhookEventStatus.PENDING.value
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
