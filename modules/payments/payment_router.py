from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_tenant_id, get_db, require_authenticated_user
from app.modules.payments.schemas import (
    PaymentCreate,
    PaymentDetailResponse,
    PaymentProcessRequest,
    PaymentResponse,
    PaymentTransactionCreate,
)
from app.modules.payments.service import PaymentService
from app.shared.schemas import PaginatedResponse

router = APIRouter(prefix="/payments", tags=["Payments"])


def get_service(session: AsyncSession = Depends(get_db)) -> PaymentService:
    return PaymentService(session)


@router.post("", response_model=PaymentDetailResponse, status_code=201)
async def create_payment(
    data: PaymentCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: PaymentService = Depends(get_service),
) -> PaymentDetailResponse:
    """Create a payment record for a sale or order."""
    return await service.create(tenant_id, data)


@router.post("/{payment_id}/transactions", response_model=PaymentDetailResponse)
async def add_transaction(
    payment_id: UUID,
    data: PaymentTransactionCreate,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: PaymentService = Depends(get_service),
) -> PaymentDetailResponse:
    """Add a single payment transaction (supports split payments)."""
    return await service.add_transaction(tenant_id, payment_id, data, processed_by=user_id)


@router.post("/{payment_id}/process", response_model=PaymentDetailResponse)
async def process_payment(
    payment_id: UUID,
    data: PaymentProcessRequest,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: PaymentService = Depends(get_service),
) -> PaymentDetailResponse:
    """Process multiple transactions in one request (split payment)."""
    return await service.process(tenant_id, payment_id, data, processed_by=user_id)


@router.post("/{payment_id}/refund", response_model=PaymentDetailResponse)
async def refund_payment(
    payment_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    user_id: UUID = Depends(require_authenticated_user),
    service: PaymentService = Depends(get_service),
) -> PaymentDetailResponse:
    return await service.refund(tenant_id, payment_id, refunded_by=user_id)


@router.get("", response_model=PaginatedResponse[PaymentResponse])
async def list_payments(
    reference_type: str | None = Query(default=None),
    reference_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: PaymentService = Depends(get_service),
) -> PaginatedResponse[PaymentResponse]:
    return await service.list(
        tenant_id,
        reference_type=reference_type,
        reference_id=reference_id,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.get("/{payment_id}", response_model=PaymentDetailResponse)
async def get_payment(
    payment_id: UUID,
    tenant_id: UUID = Depends(get_current_user_tenant_id),
    service: PaymentService = Depends(get_service),
) -> PaymentDetailResponse:
    return await service.get(tenant_id, payment_id)
