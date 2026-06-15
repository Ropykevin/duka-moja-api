from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db
from app.modules.catalog.schemas import (
    AttributeCreate,
    AttributeResponse,
    AttributeUpdate,
    AttributeValueCreate,
    AttributeValueResponse,
)
from app.modules.catalog.service import AttributeService

router = APIRouter(prefix="/attributes", tags=["Attributes"])


def get_service(session: AsyncSession = Depends(get_db)) -> AttributeService:
    return AttributeService(session)


@router.post("", response_model=AttributeResponse, status_code=201)
async def create_attribute(
    data: AttributeCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: AttributeService = Depends(get_service),
) -> AttributeResponse:
    return await service.create(tenant_id, data)


@router.get("", response_model=list[AttributeResponse])
async def list_attributes(
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: AttributeService = Depends(get_service),
) -> list[AttributeResponse]:
    return await service.list(tenant_id)


@router.get("/{attribute_id}", response_model=AttributeResponse)
async def get_attribute(
    attribute_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: AttributeService = Depends(get_service),
) -> AttributeResponse:
    return await service.get(tenant_id, attribute_id)


@router.patch("/{attribute_id}", response_model=AttributeResponse)
async def update_attribute(
    attribute_id: UUID,
    data: AttributeUpdate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: AttributeService = Depends(get_service),
) -> AttributeResponse:
    return await service.update(tenant_id, attribute_id, data)


@router.post("/{attribute_id}/values", response_model=AttributeValueResponse, status_code=201)
async def add_attribute_value(
    attribute_id: UUID,
    data: AttributeValueCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: AttributeService = Depends(get_service),
) -> AttributeValueResponse:
    return await service.add_value(tenant_id, attribute_id, data)


@router.delete("/{attribute_id}", status_code=204)
async def delete_attribute(
    attribute_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: AttributeService = Depends(get_service),
) -> None:
    await service.delete(tenant_id, attribute_id)
