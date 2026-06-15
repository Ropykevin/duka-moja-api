from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.modules.payments.models import (
    MerchantPaymentMethod,
    Payment,
    PaymentProvider,
    PaymentTransaction,
)
from app.shared.base_model import PaymentStatus
from app.shared.base_repository import TenantScopedRepository


class PaymentProviderRepository(TenantScopedRepository[PaymentProvider]):
    model = PaymentProvider

    async def get_by_code(self, tenant_id: UUID, code: str) -> PaymentProvider | None:
        stmt = select(PaymentProvider).where(
            PaymentProvider.tenant_id == tenant_id, PaymentProvider.code == code
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(
        self, tenant_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[PaymentProvider], int]:
        filters = [
            PaymentProvider.tenant_id == tenant_id,
            PaymentProvider.is_active.is_(True),
        ]
        count_stmt = select(func.count()).select_from(PaymentProvider).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(PaymentProvider)
            .where(*filters)
            .offset(offset)
            .limit(limit)
            .order_by(PaymentProvider.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total


class MerchantPaymentMethodRepository(TenantScopedRepository[MerchantPaymentMethod]):
    model = MerchantPaymentMethod

    async def list_for_store(
        self,
        tenant_id: UUID,
        store_id: UUID | None = None,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[MerchantPaymentMethod], int]:
        filters = [
            MerchantPaymentMethod.tenant_id == tenant_id,
            MerchantPaymentMethod.is_active.is_(True),
        ]
        if store_id:
            filters.append(
                (MerchantPaymentMethod.store_id == store_id)
                | (MerchantPaymentMethod.store_id.is_(None))
            )

        count_stmt = select(func.count()).select_from(MerchantPaymentMethod).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(MerchantPaymentMethod)
            .where(*filters)
            .options(selectinload(MerchantPaymentMethod.provider))
            .offset(offset)
            .limit(limit)
            .order_by(MerchantPaymentMethod.sort_order, MerchantPaymentMethod.display_name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def clear_default_flags(self, tenant_id: UUID, store_id: UUID | None) -> None:
        filters = [MerchantPaymentMethod.tenant_id == tenant_id]
        if store_id:
            filters.append(MerchantPaymentMethod.store_id == store_id)
        else:
            filters.append(MerchantPaymentMethod.store_id.is_(None))

        stmt = select(MerchantPaymentMethod).where(*filters)
        result = await self.session.execute(stmt)
        for method in result.scalars().all():
            method.is_default = False


class PaymentRepository(TenantScopedRepository[Payment]):
    model = Payment

    async def get_with_details(self, tenant_id: UUID, payment_id: UUID) -> Payment | None:
        stmt = (
            select(Payment)
            .where(Payment.tenant_id == tenant_id, Payment.id == payment_id)
            .options(selectinload(Payment.transactions))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_for_reference(
        self, tenant_id: UUID, reference_type: str, reference_id: UUID
    ) -> Payment | None:
        stmt = select(Payment).where(
            Payment.tenant_id == tenant_id,
            Payment.reference_type == reference_type,
            Payment.reference_id == reference_id,
            Payment.status.in_([PaymentStatus.PENDING.value, PaymentStatus.PARTIAL.value]),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_for_tenant(self, tenant_id: UUID) -> int:
        stmt = select(func.count()).select_from(Payment).where(Payment.tenant_id == tenant_id)
        return (await self.session.execute(stmt)).scalar_one()

    async def list_for_tenant(
        self,
        tenant_id: UUID,
        *,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Payment], int]:
        filters = [Payment.tenant_id == tenant_id]
        if reference_type:
            filters.append(Payment.reference_type == reference_type)
        if reference_id:
            filters.append(Payment.reference_id == reference_id)
        if status:
            filters.append(Payment.status == status)

        count_stmt = select(func.count()).select_from(Payment).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(Payment)
            .where(*filters)
            .offset(offset)
            .limit(limit)
            .order_by(Payment.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total


class PaymentTransactionRepository(TenantScopedRepository[PaymentTransaction]):
    model = PaymentTransaction

    async def sum_completed_for_payment(self, payment_id: UUID) -> float:
        stmt = select(func.coalesce(func.sum(PaymentTransaction.amount), 0)).where(
            PaymentTransaction.payment_id == payment_id,
            PaymentTransaction.status == "completed",
        )
        return (await self.session.execute(stmt)).scalar_one()
