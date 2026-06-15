import re
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError, ValidationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.modules.auth.models import Role, User, UserRole
from app.modules.auth.repository import (
    RoleRepository,
    UserRepository,
    UserRoleRepository,
)
from app.modules.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)
from app.modules.tenants.models import Tenant
from app.modules.tenants.repository import SubscriptionPlanRepository, TenantRepository
from app.shared.base_model import TenantStatus, UserStatus
from app.modules.subscriptions.service import SubscriptionService


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.role_repo = RoleRepository(session)
        self.user_role_repo = UserRoleRepository(session)
        self.tenant_repo = TenantRepository(session)
        self.plan_repo = SubscriptionPlanRepository(session)
        self.subscription_service = SubscriptionService(session)
        self.settings = get_settings()

    async def register(self, data: RegisterRequest) -> RegisterResponse:
        existing = await self.tenant_repo.get_by_slug(data.tenant_slug)
        if existing:
            raise ConflictError(f"Tenant slug '{data.tenant_slug}' is already taken")

        tenant = Tenant(
            name=data.tenant_name,
            slug=data.tenant_slug,
            email=data.tenant_email,
            phone=data.tenant_phone,
            country=data.country,
            timezone=data.timezone,
            status=TenantStatus.ACTIVE.value,
        )
        tenant = await self.tenant_repo.create(tenant)

        owner_role = Role(
            tenant_id=tenant.id,
            name="Owner",
            description="Tenant owner with full access",
            is_system=True,
        )
        owner_role = await self.role_repo.create(owner_role)

        user = User(
            tenant_id=tenant.id,
            email=data.owner.email,
            password_hash=hash_password(data.owner.password),
            first_name=data.owner.first_name,
            last_name=data.owner.last_name,
            phone=data.owner.phone,
            status=UserStatus.ACTIVE.value,
            is_tenant_owner=True,
        )
        user = await self.user_repo.create(user)
        await self.user_role_repo.assign_role(user.id, owner_role.id, tenant.id)

        trial_plan = await self.plan_repo.get_by_code("trial")
        if trial_plan is None:
            raise NotFoundError("SubscriptionPlan", "trial")

        await self.subscription_service.create_trial_subscription(tenant.id, trial_plan.id)

        tokens = self._build_tokens(user.id, tenant.id)
        return RegisterResponse(
            tenant_id=tenant.id,
            user=UserResponse.model_validate(user),
            tokens=tokens,
        )

    async def login(self, data: LoginRequest) -> TokenResponse:
        tenant: Tenant | None = None
        if data.tenant_slug:
            tenant = await self.tenant_repo.get_by_slug(data.tenant_slug)
            if tenant is None:
                raise UnauthorizedError("Invalid credentials")
        else:
            raise ValidationError("tenant_slug is required for login")

        user = await self.user_repo.get_by_email(tenant.id, data.email)
        if user is None or not verify_password(data.password, user.password_hash):
            raise UnauthorizedError("Invalid credentials")

        if user.status != UserStatus.ACTIVE.value:
            raise UnauthorizedError("Account is not active")

        user.last_login_at = datetime.now(UTC)
        await self.user_repo.update(user)

        return self._build_tokens(user.id, tenant.id)

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        from app.core.security import TokenPayload

        try:
            payload = TokenPayload.from_token(refresh_token)
        except ValueError as exc:
            raise UnauthorizedError("Invalid refresh token") from exc

        if payload.token_type != "refresh":
            raise UnauthorizedError("Invalid token type")

        user = await self.user_repo.get_by_id_or_raise(UUID(payload.sub))
        if user.status != UserStatus.ACTIVE.value:
            raise UnauthorizedError("Account is not active")

        tenant_id = payload.tenant_id or user.tenant_id
        return self._build_tokens(user.id, tenant_id)

    async def get_current_user(self, user_id: UUID) -> User:
        user = await self.user_repo.get_by_id_with_roles(user_id)
        if user is None:
            raise NotFoundError("User", user_id)
        return user

    def _build_tokens(self, user_id: UUID, tenant_id: UUID) -> TokenResponse:
        access = create_access_token(str(user_id), tenant_id=tenant_id)
        refresh = create_refresh_token(str(user_id), tenant_id=tenant_id)
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=self.settings.jwt_access_token_expire_minutes * 60,
        )

    @staticmethod
    def generate_slug(name: str) -> str:
        slug = name.lower().strip()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = re.sub(r"-+", "-", slug).strip("-")
        return slug[:100]
