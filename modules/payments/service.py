from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.customers.repository import OrderRepository
from app.modules.payments.models import (
    MerchantPaymentMethod,
    Payment,
    PaymentProvider,
    PaymentTransaction,
)
from app.modules.payments.repository import (
    MerchantPaymentMethodRepository,
    PaymentProviderRepository,
    PaymentRepository,
    PaymentTransactionRepository,
)
from app.modules.payments.schemas import (
    MerchantPaymentMethodCreate,
    MerchantPaymentMethodResponse,
    MerchantPaymentMethodUpdate,
    PaymentCreate,
    PaymentDetailResponse,
    PaymentProcessRequest,
    PaymentProviderCreate,
    PaymentProviderResponse,
    PaymentProviderUpdate,
    PaymentResponse,
    PaymentTransactionCreate,
)
from app.modules.pos.repository import SaleRepository
from app.modules.stores.repository import StoreRepository
from app.shared.base_model import (
    OrderStatus,
    PaymentReferenceType,
    PaymentStatus,
    PaymentTransactionStatus,
    SaleStatus,
)
from app.shared.schemas import PaginatedResponse


class PaymentProviderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PaymentProviderRepository(session)

    async def create(self, tenant_id: UUID, data: PaymentProviderCreate) -> PaymentProviderResponse:
        if await self.repo.get_by_code(tenant_id, data.code):
            raise ConflictError(f"Payment provider code '{data.code}' already exists")

        provider = PaymentProvider(
            tenant_id=tenant_id,
            name=data.name,
            code=data.code,
            provider_type=data.provider_type.value,
            description=data.description,
            supports_pos=data.supports_pos,
            supports_online=data.supports_online,
            is_active=True,
        )
        provider = await self.repo.create(provider)
        return PaymentProviderResponse.model_validate(provider)

    async def list(
        self, tenant_id: UUID, *, page: int = 1, page_size: int = 20
    ) -> PaginatedResponse[PaymentProviderResponse]:
        items, total = await self.repo.list_active(
            tenant_id, offset=(page - 1) * page_size, limit=page_size
        )
        return PaginatedResponse.create(
            [PaymentProviderResponse.model_validate(p) for p in items], total, page, page_size
        )

    async def get(self, tenant_id: UUID, provider_id: UUID) -> PaymentProviderResponse:
        provider = await self._get_or_raise(tenant_id, provider_id)
        return PaymentProviderResponse.model_validate(provider)

    async def update(
        self, tenant_id: UUID, provider_id: UUID, data: PaymentProviderUpdate
    ) -> PaymentProviderResponse:
        provider = await self._get_or_raise(tenant_id, provider_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(provider, field, value)
        provider = await self.repo.update(provider)
        return PaymentProviderResponse.model_validate(provider)

    async def _get_or_raise(self, tenant_id: UUID, provider_id: UUID) -> PaymentProvider:
        provider = await self.repo.get_by_id(provider_id)
        if provider is None or provider.tenant_id != tenant_id:
            raise NotFoundError("PaymentProvider", provider_id)
        return provider


class MerchantPaymentMethodService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = MerchantPaymentMethodRepository(session)
        self.provider_repo = PaymentProviderRepository(session)
        self.store_repo = StoreRepository(session)

    async def create(
        self, tenant_id: UUID, data: MerchantPaymentMethodCreate
    ) -> MerchantPaymentMethodResponse:
        provider = await self.provider_repo.get_by_id(data.provider_id)
        if provider is None or provider.tenant_id != tenant_id or not provider.is_active:
            raise NotFoundError("PaymentProvider", data.provider_id)

        if data.store_id:
            store = await self.store_repo.get_by_id(data.store_id)
            if store is None or store.tenant_id != tenant_id:
                raise NotFoundError("Store", data.store_id)

        if data.is_default:
            await self.repo.clear_default_flags(tenant_id, data.store_id)

        method = MerchantPaymentMethod(
            tenant_id=tenant_id,
            provider_id=data.provider_id,
            store_id=data.store_id,
            display_name=data.display_name,
            settings=data.settings or {},
            is_active=True,
            is_default=data.is_default,
            sort_order=data.sort_order,
        )
        method = await self.repo.create(method)
        return MerchantPaymentMethodResponse.model_validate(method)

    async def list(
        self,
        tenant_id: UUID,
        *,
        store_id: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[MerchantPaymentMethodResponse]:
        items, total = await self.repo.list_for_store(
            tenant_id, store_id, offset=(page - 1) * page_size, limit=page_size
        )
        return PaginatedResponse.create(
            [MerchantPaymentMethodResponse.model_validate(m) for m in items], total, page, page_size
        )

    async def get(self, tenant_id: UUID, method_id: UUID) -> MerchantPaymentMethodResponse:
        method = await self._get_or_raise(tenant_id, method_id)
        return MerchantPaymentMethodResponse.model_validate(method)

    async def update(
        self, tenant_id: UUID, method_id: UUID, data: MerchantPaymentMethodUpdate
    ) -> MerchantPaymentMethodResponse:
        method = await self._get_or_raise(tenant_id, method_id)
        update_data = data.model_dump(exclude_unset=True)
        if update_data.get("is_default"):
            await self.repo.clear_default_flags(tenant_id, method.store_id)
        for field, value in update_data.items():
            setattr(method, field, value)
        method = await self.repo.update(method)
        return MerchantPaymentMethodResponse.model_validate(method)

    async def _get_or_raise(self, tenant_id: UUID, method_id: UUID) -> MerchantPaymentMethod:
        method = await self.repo.get_by_id(method_id)
        if method is None or method.tenant_id != tenant_id:
            raise NotFoundError("MerchantPaymentMethod", method_id)
        return method


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.payment_repo = PaymentRepository(session)
        self.transaction_repo = PaymentTransactionRepository(session)
        self.method_repo = MerchantPaymentMethodRepository(session)
        self.sale_repo = SaleRepository(session)
        self.order_repo = OrderRepository(session)
        self.store_repo = StoreRepository(session)

    async def create(self, tenant_id: UUID, data: PaymentCreate) -> PaymentDetailResponse:
        ref_type = data.reference_type.value
        payable = await self._resolve_payable(tenant_id, ref_type, data.reference_id)

        existing = await self.payment_repo.get_active_for_reference(
            tenant_id, ref_type, data.reference_id
        )
        if existing:
            raise ConflictError("An active payment already exists for this reference")

        payment_number = await self._generate_payment_number(tenant_id)
        payment = Payment(
            tenant_id=tenant_id,
            payment_number=payment_number,
            reference_type=ref_type,
            reference_id=data.reference_id,
            customer_id=payable["customer_id"],
            store_id=payable["store_id"],
            currency=payable["currency"],
            amount_due=payable["amount_due"],
            amount_paid=Decimal("0"),
            status=PaymentStatus.PENDING.value,
            notes=data.notes,
        )
        payment = await self.payment_repo.create(payment)
        return PaymentDetailResponse.model_validate(payment)

    async def add_transaction(
        self,
        tenant_id: UUID,
        payment_id: UUID,
        data: PaymentTransactionCreate,
        *,
        processed_by: UUID | None = None,
    ) -> PaymentDetailResponse:
        payment = await self._get_mutable_payment(tenant_id, payment_id)
        await self._validate_transaction(payment, data)

        transaction = await self._create_transaction(
            tenant_id, payment, data, processed_by=processed_by
        )
        if data.complete:
            await self._complete_transaction(transaction, processed_by=processed_by)

        return await self._finalize_payment(tenant_id, payment.id)

    async def process(
        self,
        tenant_id: UUID,
        payment_id: UUID,
        data: PaymentProcessRequest,
        *,
        processed_by: UUID | None = None,
    ) -> PaymentDetailResponse:
        payment = await self._get_mutable_payment(tenant_id, payment_id)

        running = sum(
            tx.amount
            for tx in payment.transactions
            if tx.status == PaymentTransactionStatus.COMPLETED.value
        )
        total_new = sum(tx.amount for tx in data.transactions)
        if total_new > payment.amount_due - running:
            raise ValidationError(
                f"Transaction total {total_new} exceeds remaining balance {payment.amount_due - running}"
            )

        for tx_data in data.transactions:
            remaining = payment.amount_due - running
            if tx_data.amount > remaining:
                raise ValidationError(
                    f"Transaction amount {tx_data.amount} exceeds remaining balance {remaining}"
                )
            if tx_data.merchant_method_id:
                method = await self.method_repo.get_by_id(tx_data.merchant_method_id)
                if method is None or method.tenant_id != payment.tenant_id or not method.is_active:
                    raise NotFoundError("MerchantPaymentMethod", tx_data.merchant_method_id)

            transaction = await self._create_transaction(
                tenant_id, payment, tx_data, processed_by=processed_by
            )
            if tx_data.complete:
                await self._complete_transaction(transaction, processed_by=processed_by)
                running += tx_data.amount

        return await self._finalize_payment(tenant_id, payment.id)

    async def refund(
        self, tenant_id: UUID, payment_id: UUID, *, refunded_by: UUID | None = None
    ) -> PaymentDetailResponse:
        payment = await self.payment_repo.get_with_details(tenant_id, payment_id)
        if payment is None:
            raise NotFoundError("Payment", payment_id)
        if payment.status not in (PaymentStatus.PAID.value, PaymentStatus.PARTIAL.value):
            raise ValidationError("Only paid or partial payments can be refunded")

        for transaction in payment.transactions:
            if transaction.status == PaymentTransactionStatus.COMPLETED.value:
                transaction.status = PaymentTransactionStatus.REFUNDED.value
                await self.transaction_repo.update(transaction)

        payment.status = PaymentStatus.REFUNDED.value
        payment.amount_paid = Decimal("0")
        await self.payment_repo.update(payment)
        await self._sync_payable(payment)

        payment = await self.payment_repo.get_with_details(tenant_id, payment.id)
        return PaymentDetailResponse.model_validate(payment)

    async def list(
        self,
        tenant_id: UUID,
        *,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[PaymentResponse]:
        items, total = await self.payment_repo.list_for_tenant(
            tenant_id,
            reference_type=reference_type,
            reference_id=reference_id,
            status=status,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return PaginatedResponse.create(
            [PaymentResponse.model_validate(p) for p in items], total, page, page_size
        )

    async def get(self, tenant_id: UUID, payment_id: UUID) -> PaymentDetailResponse:
        payment = await self.payment_repo.get_with_details(tenant_id, payment_id)
        if payment is None:
            raise NotFoundError("Payment", payment_id)
        return PaymentDetailResponse.model_validate(payment)

    async def _resolve_payable(
        self, tenant_id: UUID, reference_type: str, reference_id: UUID
    ) -> dict:
        if reference_type == PaymentReferenceType.SALE.value:
            sale = await self.sale_repo.get_by_id(reference_id)
            if sale is None or sale.tenant_id != tenant_id:
                raise NotFoundError("Sale", reference_id)
            if sale.status != SaleStatus.COMPLETED.value:
                raise ValidationError("Payments can only be created for completed sales")
            if sale.payment_status == PaymentStatus.PAID.value:
                raise ValidationError("Sale is already fully paid")
            currency = "KES"
            if sale.store_id:
                store = await self.store_repo.get_by_id(sale.store_id)
                if store:
                    currency = store.currency
            return {
                "customer_id": sale.customer_id,
                "store_id": sale.store_id,
                "currency": currency,
                "amount_due": sale.total - sale.amount_paid,
            }

        if reference_type == PaymentReferenceType.ORDER.value:
            order = await self.order_repo.get_by_id(reference_id)
            if order is None or order.tenant_id != tenant_id:
                raise NotFoundError("Order", reference_id)
            if order.status not in (
                OrderStatus.CONFIRMED.value,
                OrderStatus.PROCESSING.value,
                OrderStatus.SHIPPED.value,
                OrderStatus.DELIVERED.value,
            ):
                raise ValidationError("Order must be confirmed before payment")
            if order.payment_status == PaymentStatus.PAID.value:
                raise ValidationError("Order is already fully paid")
            currency = "KES"
            if order.store_id:
                store = await self.store_repo.get_by_id(order.store_id)
                if store:
                    currency = store.currency
            return {
                "customer_id": order.customer_id,
                "store_id": order.store_id,
                "currency": currency,
                "amount_due": order.total,
            }

        raise ValidationError(f"Unsupported reference type: {reference_type}")

    async def _validate_transaction(
        self, payment: Payment, data: PaymentTransactionCreate
    ) -> None:
        if data.merchant_method_id:
            method = await self.method_repo.get_by_id(data.merchant_method_id)
            if method is None or method.tenant_id != payment.tenant_id or not method.is_active:
                raise NotFoundError("MerchantPaymentMethod", data.merchant_method_id)

        remaining = payment.amount_due - payment.amount_paid
        if data.amount > remaining:
            raise ValidationError(
                f"Transaction amount {data.amount} exceeds remaining balance {remaining}"
            )

    async def _create_transaction(
        self,
        tenant_id: UUID,
        payment: Payment,
        data: PaymentTransactionCreate,
        *,
        processed_by: UUID | None,
    ) -> PaymentTransaction:
        status = (
            PaymentTransactionStatus.COMPLETED.value
            if data.complete
            else PaymentTransactionStatus.PENDING.value
        )
        transaction = PaymentTransaction(
            tenant_id=tenant_id,
            payment_id=payment.id,
            merchant_method_id=data.merchant_method_id,
            method_type=data.method_type,
            amount=data.amount,
            status=status,
            external_reference=data.external_reference,
            notes=data.notes,
            processed_at=datetime.now(UTC) if data.complete else None,
            processed_by=processed_by if data.complete else None,
        )
        return await self.transaction_repo.create(transaction)

    async def _complete_transaction(
        self, transaction: PaymentTransaction, *, processed_by: UUID | None
    ) -> None:
        if transaction.status == PaymentTransactionStatus.COMPLETED.value:
            return
        transaction.status = PaymentTransactionStatus.COMPLETED.value
        transaction.processed_at = datetime.now(UTC)
        transaction.processed_by = processed_by
        await self.transaction_repo.update(transaction)

    async def _finalize_payment(self, tenant_id: UUID, payment_id: UUID) -> PaymentDetailResponse:
        payment = await self.payment_repo.get_with_details(tenant_id, payment_id)
        if payment is None:
            raise NotFoundError("Payment", payment_id)

        amount_paid = Decimal("0")
        for tx in payment.transactions:
            if tx.status == PaymentTransactionStatus.COMPLETED.value:
                amount_paid += tx.amount

        payment.amount_paid = amount_paid
        if amount_paid >= payment.amount_due:
            payment.status = PaymentStatus.PAID.value
            payment.paid_at = datetime.now(UTC)
        elif amount_paid > 0:
            payment.status = PaymentStatus.PARTIAL.value
        else:
            payment.status = PaymentStatus.PENDING.value

        await self.payment_repo.update(payment)
        await self._sync_payable(payment)

        payment = await self.payment_repo.get_with_details(tenant_id, payment.id)
        return PaymentDetailResponse.model_validate(payment)

    async def _sync_payable(self, payment: Payment) -> None:
        if payment.reference_type == PaymentReferenceType.SALE.value:
            sale = await self.sale_repo.get_by_id(payment.reference_id)
            if sale and sale.tenant_id == payment.tenant_id:
                if payment.status == PaymentStatus.REFUNDED.value:
                    sale.payment_status = PaymentStatus.REFUNDED.value
                    sale.amount_paid = Decimal("0")
                else:
                    sale.amount_paid = payment.amount_paid
                    sale.payment_status = payment.status
                await self.sale_repo.update(sale)
            return

        if payment.reference_type == PaymentReferenceType.ORDER.value:
            order = await self.order_repo.get_by_id(payment.reference_id)
            if order and order.tenant_id == payment.tenant_id:
                order.payment_status = payment.status
                await self.order_repo.update(order)

    async def _get_mutable_payment(self, tenant_id: UUID, payment_id: UUID) -> Payment:
        payment = await self.payment_repo.get_with_details(tenant_id, payment_id)
        if payment is None:
            raise NotFoundError("Payment", payment_id)
        if payment.status in (PaymentStatus.PAID.value, PaymentStatus.REFUNDED.value):
            raise ValidationError("Payment cannot be modified in current status")
        return payment

    async def _generate_payment_number(self, tenant_id: UUID) -> str:
        count = await self.payment_repo.count_for_tenant(tenant_id)
        return f"PAY-{count + 1:06d}"
