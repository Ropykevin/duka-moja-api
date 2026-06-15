from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    *,
    tenant_id: UUID | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "type": "access",
    }
    if tenant_id:
        payload["tenant_id"] = str(tenant_id)
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str, *, tenant_id: UUID | None = None) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "type": "refresh",
    }
    if tenant_id:
        payload["tenant_id"] = str(tenant_id)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


class TokenPayload:
    def __init__(self, data: dict[str, Any]) -> None:
        self.sub: str = data.get("sub", "")
        self.tenant_id: UUID | None = None
        if tid := data.get("tenant_id"):
            self.tenant_id = UUID(tid) if isinstance(tid, str) else tid
        self.token_type: str = data.get("type", "access")
        self.exp: datetime | None = None
        if exp := data.get("exp"):
            self.exp = datetime.fromtimestamp(exp, tz=UTC)

    @classmethod
    def from_token(cls, token: str) -> "TokenPayload":
        try:
            data = decode_token(token)
            return cls(data)
        except JWTError as exc:
            raise ValueError("Invalid token") from exc
