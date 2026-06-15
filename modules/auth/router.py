from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_authenticated_user
from app.modules.auth.schemas import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_auth_service(session: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(session)


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    data: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> RegisterResponse:
    """Register a new merchant tenant with owner account and trial subscription."""
    return await service.register(data)


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """OAuth2-compatible login. Use username=email, password=password, and tenant_slug in scope."""
    tenant_slug = None
    if form_data.scopes:
        tenant_slug = form_data.scopes[0]
    data = LoginRequest(
        email=form_data.username,
        password=form_data.password,
        tenant_slug=tenant_slug,
    )
    return await service.login(data)


@router.post("/login/json", response_model=TokenResponse)
async def login_json(
    data: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """JSON-based login endpoint."""
    return await service.login(data)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshTokenRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Refresh an access token using a valid refresh token."""
    return await service.refresh_token(data.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: UUID = Depends(require_authenticated_user),
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """Get the currently authenticated user."""
    user = await service.get_current_user(user_id)
    return UserResponse.model_validate(user)
