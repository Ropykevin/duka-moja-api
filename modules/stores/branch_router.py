from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db
from app.modules.stores.schemas import BranchCreate, BranchResponse, BranchUpdate
from app.modules.stores.service import BranchService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/branches", tags=["Branches"])


def get_branch_service(session: AsyncSession = Depends(get_db)) -> BranchService:
    return BranchService(session)


@router.post("", response_model=BranchResponse, status_code=201)
async def create_branch(
    data: BranchCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: BranchService = Depends(get_branch_service),
) -> BranchResponse:
    """Create a new branch under a store."""
    return await service.create_branch(tenant_id, data)


@router.get("", response_model=PaginatedResponse[BranchResponse])
async def list_branches(
    store_id: UUID = Query(..., description="Filter branches by store"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: BranchService = Depends(get_branch_service),
) -> PaginatedResponse[BranchResponse]:
    """List branches for a specific store."""
    return await service.list_branches(
        tenant_id, store_id, page=page, page_size=page_size
    )


@router.get("/{branch_id}", response_model=BranchResponse)
async def get_branch(
    branch_id: UUID,
    store_id: UUID = Query(..., description="Store the branch belongs to"),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: BranchService = Depends(get_branch_service),
) -> BranchResponse:
    """Get a single branch."""
    return await service.get_branch(tenant_id, store_id, branch_id)


@router.patch("/{branch_id}", response_model=BranchResponse)
async def update_branch(
    branch_id: UUID,
    data: BranchUpdate,
    store_id: UUID = Query(..., description="Store the branch belongs to"),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: BranchService = Depends(get_branch_service),
) -> BranchResponse:
    """Update branch information."""
    return await service.update_branch(tenant_id, store_id, branch_id, data)


@router.delete("/{branch_id}", status_code=204)
async def delete_branch(
    branch_id: UUID,
    store_id: UUID = Query(..., description="Store the branch belongs to"),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: BranchService = Depends(get_branch_service),
) -> None:
    """Deactivate a branch."""
    await service.delete_branch(tenant_id, store_id, branch_id)
