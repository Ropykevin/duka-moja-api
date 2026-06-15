from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db
from app.modules.customers.schemas import CartItemAdd, CartItemUpdate, CartResponse
from app.modules.customers.service import CartService

router = APIRouter(prefix="/cart", tags=["Cart"])


def get_service(session: AsyncSession = Depends(get_db)) -> CartService:
    return CartService(session)


@router.get("", response_model=CartResponse)
async def get_or_create_cart(
    customer_id: UUID = Query(...),
    branch_id: UUID | None = Query(default=None),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CartService = Depends(get_service),
) -> CartResponse:
    return await service.get_or_create_cart(tenant_id, customer_id, branch_id=branch_id)


@router.get("/{cart_id}", response_model=CartResponse)
async def get_cart(
    cart_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CartService = Depends(get_service),
) -> CartResponse:
    return await service.get_cart(tenant_id, cart_id)


@router.post("/{cart_id}/items", response_model=CartResponse)
async def add_cart_item(
    cart_id: UUID,
    data: CartItemAdd,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CartService = Depends(get_service),
) -> CartResponse:
    return await service.add_item(tenant_id, cart_id, data)


@router.patch("/{cart_id}/items/{item_id}", response_model=CartResponse)
async def update_cart_item(
    cart_id: UUID,
    item_id: UUID,
    data: CartItemUpdate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CartService = Depends(get_service),
) -> CartResponse:
    return await service.update_item(tenant_id, cart_id, item_id, data)


@router.delete("/{cart_id}/items/{item_id}", response_model=CartResponse)
async def remove_cart_item(
    cart_id: UUID,
    item_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: CartService = Depends(get_service),
) -> CartResponse:
    return await service.remove_item(tenant_id, cart_id, item_id)
