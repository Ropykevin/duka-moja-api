from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.shared.base_model import AuditAction, NotificationChannel
from app.shared.schemas import BaseSchema


# --- Notification ---

class NotificationCreate(BaseSchema):
    user_id: UUID | None = None
    channel: NotificationChannel = NotificationChannel.IN_APP
    notification_type: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)
    reference_type: str | None = Field(default=None, max_length=50)
    reference_id: UUID | None = None


class NotificationResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    user_id: UUID | None
    channel: str
    notification_type: str
    title: str
    body: str
    reference_type: str | None
    reference_id: UUID | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime
    updated_at: datetime


# --- Audit Log ---

class AuditLogCreate(BaseSchema):
    action: AuditAction
    entity_type: str = Field(min_length=1, max_length=50)
    entity_id: UUID | None = None
    old_values: dict | None = None
    new_values: dict | None = None
    ip_address: str | None = Field(default=None, max_length=45)
    user_agent: str | None = Field(default=None, max_length=500)
    metadata: dict | None = None


class AuditLogResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    user_id: UUID | None
    action: str
    entity_type: str
    entity_id: UUID | None
    old_values: dict | None
    new_values: dict | None
    ip_address: str | None
    user_agent: str | None
    metadata: dict | None = Field(validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime


# --- Media ---

class MediaCreate(BaseSchema):
    filename: str = Field(min_length=1, max_length=255)
    original_filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=100)
    file_size: int = Field(ge=0)
    url: str = Field(min_length=1, max_length=500)
    storage_backend: str = Field(default="local", max_length=20)
    entity_type: str | None = Field(default=None, max_length=50)
    entity_id: UUID | None = None


class MediaResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    filename: str
    original_filename: str
    mime_type: str
    file_size: int
    url: str
    storage_backend: str
    entity_type: str | None
    entity_id: UUID | None
    uploaded_by: UUID | None
    created_at: datetime
    updated_at: datetime


# --- Webhook Event ---

class WebhookEventCreate(BaseSchema):
    event_type: str = Field(min_length=1, max_length=100)
    target_url: str = Field(min_length=1, max_length=500)
    payload: dict


class WebhookEventResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    event_type: str
    target_url: str
    payload: dict
    status: str
    attempts: int
    last_attempt_at: datetime | None
    delivered_at: datetime | None
    response_status: int | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
