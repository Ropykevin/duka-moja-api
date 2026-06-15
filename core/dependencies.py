import uuid
from collections.abc import Callable
from typing import Any

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.database import get_db_session
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import TokenPayload
from app.core.tenant import extract_tenant_from_request, set_tenant_id, set_user_id

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Any:
        tenant_id = await extract_tenant_from_request(request)
        set_tenant_id(tenant_id)
        set_user_id(None)
        response = await call_next(request)
        return response


async def get_current_user_id(
    token: str | None = Depends(oauth2_scheme),
) -> uuid.UUID | None:
    if not token:
        return None
    try:
        payload = TokenPayload.from_token(token)
        if payload.token_type != "access":
            raise UnauthorizedError("Invalid token type")
        user_id = uuid.UUID(payload.sub)
        set_user_id(user_id)
        if payload.tenant_id:
            set_tenant_id(payload.tenant_id)
        return user_id
    except (ValueError, UnauthorizedError):
        raise UnauthorizedError("Could not validate credentials") from None


async def require_authenticated_user(
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> uuid.UUID:
    if user_id is None:
        raise UnauthorizedError()
    return user_id


async def get_db() -> AsyncSession:
    async for session in get_db_session():
        yield session


class DBSession:
    def __init__(self, session: AsyncSession = Depends(get_db)) -> None:
        self.session = session


def require_tenant_context() -> uuid.UUID:
    from app.core.tenant import get_tenant_id, require_tenant_id

    tenant_id = get_tenant_id()
    if tenant_id is None:
        raise ForbiddenError("Tenant context required. Provide X-Tenant-ID header or JWT.")
    return require_tenant_id()
