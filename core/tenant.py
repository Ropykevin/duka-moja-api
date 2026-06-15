from collections.abc import AsyncGenerator
from contextvars import ContextVar
from uuid import UUID

from fastapi import Request

_tenant_id_ctx: ContextVar[UUID | None] = ContextVar("tenant_id", default=None)
_user_id_ctx: ContextVar[UUID | None] = ContextVar("user_id", default=None)


def set_tenant_id(tenant_id: UUID | None) -> None:
    _tenant_id_ctx.set(tenant_id)


def get_tenant_id() -> UUID | None:
    return _tenant_id_ctx.get()


def set_user_id(user_id: UUID | None) -> None:
    _user_id_ctx.set(user_id)


def get_user_id() -> UUID | None:
    return _user_id_ctx.get()


def require_tenant_id() -> UUID:
    tenant_id = get_tenant_id()
    if tenant_id is None:
        raise RuntimeError("Tenant context is not set")
    return tenant_id


async def extract_tenant_from_request(request: Request) -> UUID | None:
    from app.core.config import get_settings

    settings = get_settings()
    header_value = request.headers.get(settings.tenant_header)
    if not header_value:
        return None
    try:
        return UUID(header_value)
    except ValueError:
        return None
