from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db, require_authenticated_user
from app.modules.system.schemas import MediaCreate, MediaResponse
from app.modules.system.service import MediaService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/media", tags=["Media"])


def get_service(session: AsyncSession = Depends(get_db)) -> MediaService:
    return MediaService(session)


@router.post("", response_model=MediaResponse, status_code=201)
async def register_media(
    data: MediaCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: MediaService = Depends(get_service),
) -> MediaResponse:
    """Register uploaded file metadata (storage upload handled separately)."""
    return await service.create(tenant_id, data, uploaded_by=user_id)


@router.get("", response_model=PaginatedResponse[MediaResponse])
async def list_media(
    entity_type: str = Query(...),
    entity_id: UUID = Query(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: MediaService = Depends(get_service),
) -> PaginatedResponse[MediaResponse]:
    return await service.list_for_entity(
        tenant_id, entity_type, entity_id, page=page, page_size=page_size
    )


@router.get("/{media_id}", response_model=MediaResponse)
async def get_media(
    media_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: MediaService = Depends(get_service),
) -> MediaResponse:
    return await service.get(tenant_id, media_id)
