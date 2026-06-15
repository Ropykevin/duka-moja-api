from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.catalog.repository import ProductVariantRepository
from app.modules.customers.repository import CustomerRepository
from app.modules.inventory.service import InventoryService
from app.modules.pos.models import CashRegister, CashSession, Sale, SaleItem
from app.modules.pos.repository import (
    CashRegisterRepository,
    CashSessionRepository,
    SaleItemRepository,
    SaleRepository,
)
from app.modules.pos.schemas import (
    CashRegisterCreate,
    CashRegisterResponse,
    CashRegisterUpdate,
    CashSessionClose,
    CashSessionOpen,
    CashSessionResponse,
    SaleComplete,
    SaleCreate,
    SaleDetailResponse,
    SaleItemAdd,
    SaleItemCreate,
    SaleItemResponse,
    SaleResponse,
)
from app.modules.stores.repository import BranchRepository, StoreSettingsRepository
from app.shared.base_model import (
    CashRegisterStatus,
    CashSessionStatus,
    InventoryMovementSource,
    PaymentStatus,
    SaleStatus,
)
from app.shared.schemas import PaginatedResponse


class CashRegisterService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CashRegisterRepository(session)
        self.branch_repo = BranchRepository(session)

    async def create(self, tenant_id: UUID, data: CashRegisterCreate) -> CashRegisterResponse:
        branch = await self.branch_repo.get_by_id(data.branch_id)
        if branch is None or branch.tenant_id != tenant_id:
            raise NotFoundError("Branch", data.branch_id)

        if await self.repo.get_by_code(tenant_id, data.code):
            raise ConflictError(f"Register code '{data.code}' already exists")

        register = CashRegister(
            tenant_id=tenant_id,
            branch_id=data.branch_id,
            name=data.name,
            code=data.code,
            status=CashRegisterStatus.ACTIVE.value,
        )
        register = await self.repo.create(register)
        return CashRegisterResponse.model_validate(register)

    async def list(
        self,
        tenant_id: UUID,
        *,
        branch_id: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[CashRegisterResponse]:
        if branch_id:
            items, total = await self.repo.list_for_branch(
                tenant_id, branch_id, offset=(page - 1) * page_size, limit=page_size
            )
        else:
            items, total = await self.repo.list_for_tenant(
                tenant_id, offset=(page - 1) * page_size, limit=page_size
            )
        return PaginatedResponse.create(
            [CashRegisterResponse.model_validate(r) for r in items], total, page, page_size
        )

    async def get(self, tenant_id: UUID, register_id: UUID) -> CashRegisterResponse:
        register = await self._get_or_raise(tenant_id, register_id)
        return CashRegisterResponse.model_validate(register)

    async def update(
        self, tenant_id: UUID, register_id: UUID, data: CashRegisterUpdate
    ) -> CashRegisterResponse:
        register = await self._get_or_raise(tenant_id, register_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(register, field, value)
        register = await self.repo.update(register)
        return CashRegisterResponse.model_validate(register)

    async def _get_or_raise(self, tenant_id: UUID, register_id: UUID) -> CashRegister:
        register = await self.repo.get_by_id(register_id)
        if register is None or register.tenant_id != tenant_id:
            raise NotFoundError("CashRegister", register_id)
        return register


class CashSessionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.session_repo = CashSessionRepository(session)
        self.register_repo = CashRegisterRepository(session)
        self.sale_repo = SaleRepository(session)

    async def open(
        self, tenant_id: UUID, data: CashSessionOpen, *, opened_by: UUID
    ) -> CashSessionResponse:
        register = await self.register_repo.get_by_id(data.register_id)
        if register is None or register.tenant_id != tenant_id:
            raise NotFoundError("CashRegister", data.register_id)
        if register.status != CashRegisterStatus.ACTIVE.value:
            raise ValidationError("Register is not active")

        existing = await self.session_repo.get_open_for_register(tenant_id, data.register_id)
        if existing:
            raise ConflictError("Register already has an open session")

        session = CashSession(
            tenant_id=tenant_id,
            register_id=data.register_id,
            branch_id=register.branch_id,
            opened_by=opened_by,
            status=CashSessionStatus.OPEN.value,
            opening_balance=data.opening_balance,
            opened_at=datetime.now(UTC),
        )
        session = await self.session_repo.create(session)
        return CashSessionResponse.model_validate(session)

    async def close(
        self,
        tenant_id: UUID,
        session_id: UUID,
        data: CashSessionClose,
        *,
        closed_by: UUID,
    ) -> CashSessionResponse:
        session = await self._get_or_raise(tenant_id, session_id)
        if session.status != CashSessionStatus.OPEN.value:
            raise ValidationError("Session is not open")

        draft_count = await self.sale_repo.count_draft_for_session(tenant_id, session_id)
        if draft_count > 0:
            raise ValidationError("Cannot close session with draft sales")

        expected_cash = (
            session.opening_balance + session.total_sales - session.total_refunds
        )
        cash_difference = data.closing_balance - expected_cash

        session.status = CashSessionStatus.CLOSED.value
        session.closed_by = closed_by
        session.closing_balance = data.closing_balance
        session.expected_cash = expected_cash
        session.cash_difference = cash_difference
        session.closed_at = datetime.now(UTC)
        if data.notes:
            session.notes = data.notes

        session = await self.session_repo.update(session)
        return CashSessionResponse.model_validate(session)

    async def get_active(
        self, tenant_id: UUID, register_id: UUID
    ) -> CashSessionResponse | None:
        session = await self.session_repo.get_open_for_register(tenant_id, register_id)
        if session is None:
            return None
        return CashSessionResponse.model_validate(session)

    async def list(
        self,
        tenant_id: UUID,
        *,
        register_id: UUID | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[CashSessionResponse]:
        items, total = await self.session_repo.list_for_tenant(
            tenant_id,
            register_id=register_id,
            status=status,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return PaginatedResponse.create(
            [CashSessionResponse.model_validate(s) for s in items], total, page, page_size
        )

    async def get(self, tenant_id: UUID, session_id: UUID) -> CashSessionResponse:
        session = await self._get_or_raise(tenant_id, session_id)
        return CashSessionResponse.model_validate(session)

    async def _get_or_raise(self, tenant_id: UUID, session_id: UUID) -> CashSession:
        session = await self.session_repo.get_by_id(session_id)
        if session is None or session.tenant_id != tenant_id:
            raise NotFoundError("CashSession", session_id)
        return session


class SaleService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sale_repo = SaleRepository(session)
        self.sale_item_repo = SaleItemRepository(session)
        self.session_repo = CashSessionRepository(session)
        self.register_repo = CashRegisterRepository(session)
        self.branch_repo = BranchRepository(session)
        self.variant_repo = ProductVariantRepository(session)
        self.customer_repo = CustomerRepository(session)
        self.settings_repo = StoreSettingsRepository(session)
        self.inventory_service = InventoryService(session)

    async def create(
        self,
        tenant_id: UUID,
        data: SaleCreate,
        *,
        cashier_id: UUID,
    ) -> SaleDetailResponse:
        cash_session = await self._get_open_session(tenant_id, data.session_id)
        if data.customer_id:
            customer = await self.customer_repo.get_by_id(data.customer_id)
            if customer is None or customer.tenant_id != tenant_id:
                raise NotFoundError("Customer", data.customer_id)

        register = await self.register_repo.get_by_id(cash_session.register_id)
        branch = await self.branch_repo.get_by_id(cash_session.branch_id)
        tax_rate = await self._get_tax_rate(tenant_id, branch.store_id if branch else None)

        sale_number = await self._generate_sale_number(tenant_id)
        sale = Sale(
            tenant_id=tenant_id,
            sale_number=sale_number,
            session_id=cash_session.id,
            register_id=cash_session.register_id,
            branch_id=cash_session.branch_id,
            store_id=branch.store_id if branch else None,
            customer_id=data.customer_id,
            cashier_id=cashier_id,
            status=SaleStatus.DRAFT.value,
            payment_status=PaymentStatus.PENDING.value,
            discount_amount=data.discount_amount,
            notes=data.notes,
        )
        sale = await self.sale_repo.create(sale)

        for item_data in data.items:
            await self._add_item_to_sale(tenant_id, sale, item_data, tax_rate=tax_rate)

        await self._recalculate_totals(sale)
        sale = await self.sale_repo.get_with_details(tenant_id, sale.id)
        return SaleDetailResponse.model_validate(sale)

    async def add_item(
        self, tenant_id: UUID, sale_id: UUID, data: SaleItemAdd
    ) -> SaleDetailResponse:
        sale = await self._get_draft_sale(tenant_id, sale_id)
        branch = await self.branch_repo.get_by_id(sale.branch_id)
        tax_rate = await self._get_tax_rate(tenant_id, branch.store_id if branch else None)

        await self._add_item_to_sale(tenant_id, sale, data, tax_rate=tax_rate)
        await self._recalculate_totals(sale)
        sale = await self.sale_repo.get_with_details(tenant_id, sale.id)
        return SaleDetailResponse.model_validate(sale)

    async def complete(
        self,
        tenant_id: UUID,
        sale_id: UUID,
        data: SaleComplete | None = None,
        *,
        completed_by: UUID | None = None,
    ) -> SaleDetailResponse:
        sale = await self._get_draft_sale(tenant_id, sale_id)
        sale = await self.sale_repo.get_with_details(tenant_id, sale.id)
        if not sale.items:
            raise ValidationError("Sale has no items")

        for item in sale.items:
            await self.inventory_service.record_movement(
                tenant_id,
                sale.branch_id,
                item.product_variant_id,
                InventoryMovementSource.POS_SALE,
                -item.quantity,
                reference_type="sale",
                reference_id=sale.id,
                notes=f"POS sale {sale.sale_number}",
                created_by=completed_by,
            )

        amount_paid = data.amount_paid if data and data.amount_paid is not None else sale.total
        if amount_paid >= sale.total:
            payment_status = PaymentStatus.PAID.value
        elif amount_paid > 0:
            payment_status = PaymentStatus.PARTIAL.value
        else:
            payment_status = PaymentStatus.PENDING.value

        sale.status = SaleStatus.COMPLETED.value
        sale.payment_status = payment_status
        sale.amount_paid = amount_paid
        sale.completed_at = datetime.now(UTC)
        if data and data.notes:
            sale.notes = data.notes
        await self.sale_repo.update(sale)

        cash_session = await self.session_repo.get_by_id(sale.session_id)
        if cash_session:
            cash_session.total_sales += sale.total
            cash_session.sale_count += 1
            await self.session_repo.update(cash_session)

        sale = await self.sale_repo.get_with_details(tenant_id, sale.id)
        return SaleDetailResponse.model_validate(sale)

    async def void(
        self, tenant_id: UUID, sale_id: UUID, *, voided_by: UUID | None = None
    ) -> SaleDetailResponse:
        sale = await self.sale_repo.get_with_details(tenant_id, sale_id)
        if sale is None:
            raise NotFoundError("Sale", sale_id)
        if sale.status != SaleStatus.COMPLETED.value:
            raise ValidationError("Only completed sales can be voided")

        for item in sale.items:
            await self.inventory_service.record_movement(
                tenant_id,
                sale.branch_id,
                item.product_variant_id,
                InventoryMovementSource.RETURN,
                item.quantity,
                reference_type="sale",
                reference_id=sale.id,
                notes=f"POS sale {sale.sale_number} voided",
                created_by=voided_by,
            )

        sale.status = SaleStatus.VOIDED.value
        sale.voided_at = datetime.now(UTC)
        await self.sale_repo.update(sale)

        cash_session = await self.session_repo.get_by_id(sale.session_id)
        if cash_session:
            cash_session.total_refunds += sale.total
            await self.session_repo.update(cash_session)

        sale = await self.sale_repo.get_with_details(tenant_id, sale.id)
        return SaleDetailResponse.model_validate(sale)

    async def list(
        self,
        tenant_id: UUID,
        *,
        session_id: UUID | None = None,
        register_id: UUID | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[SaleResponse]:
        items, total = await self.sale_repo.list_for_tenant(
            tenant_id,
            session_id=session_id,
            register_id=register_id,
            status=status,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return PaginatedResponse.create(
            [SaleResponse.model_validate(s) for s in items], total, page, page_size
        )

    async def get(self, tenant_id: UUID, sale_id: UUID) -> SaleDetailResponse:
        sale = await self.sale_repo.get_with_details(tenant_id, sale_id)
        if sale is None:
            raise NotFoundError("Sale", sale_id)
        return SaleDetailResponse.model_validate(sale)

    async def _add_item_to_sale(
        self,
        tenant_id: UUID,
        sale: Sale,
        data: SaleItemCreate | SaleItemAdd,
        *,
        tax_rate: Decimal,
    ) -> SaleItem:
        variant = await self.variant_repo.get_by_id(data.product_variant_id)
        if variant is None or variant.tenant_id != tenant_id:
            raise NotFoundError("ProductVariant", data.product_variant_id)

        unit_price = (
            data.unit_price
            if data.unit_price is not None
            else Decimal(str(variant.price))
        )
        line_subtotal = unit_price * data.quantity
        line_tax = line_subtotal * tax_rate / Decimal("100")
        line_total = line_subtotal + line_tax - data.discount_amount

        existing = await self.sale_item_repo.get_by_sale_and_variant(
            sale.id, data.product_variant_id
        )
        if existing:
            existing.quantity += data.quantity
            existing.discount_amount += data.discount_amount
            line_subtotal = existing.unit_price * existing.quantity
            line_tax = line_subtotal * tax_rate / Decimal("100")
            existing.line_total = line_subtotal + line_tax - existing.discount_amount
            await self.sale_item_repo.update(existing)
            return existing

        product_name = variant.name
        item = SaleItem(
            tenant_id=tenant_id,
            sale_id=sale.id,
            product_variant_id=data.product_variant_id,
            product_name=product_name,
            sku=variant.sku,
            quantity=data.quantity,
            unit_price=unit_price,
            tax_rate=tax_rate,
            discount_amount=data.discount_amount,
            line_total=line_total,
        )
        await self.sale_item_repo.create(item)
        return item

    async def _recalculate_totals(self, sale: Sale) -> None:
        sale = await self.sale_repo.get_with_details(sale.tenant_id, sale.id)
        subtotal = Decimal("0")
        tax_amount = Decimal("0")
        for item in sale.items:
            line_subtotal = item.unit_price * item.quantity
            line_tax = line_subtotal * item.tax_rate / Decimal("100")
            subtotal += line_subtotal
            tax_amount += line_tax

        sale.subtotal = subtotal
        sale.tax_amount = tax_amount
        sale.total = subtotal + tax_amount - sale.discount_amount
        await self.sale_repo.update(sale)

    async def _get_open_session(self, tenant_id: UUID, session_id: UUID) -> CashSession:
        cash_session = await self.session_repo.get_by_id(session_id)
        if cash_session is None or cash_session.tenant_id != tenant_id:
            raise NotFoundError("CashSession", session_id)
        if cash_session.status != CashSessionStatus.OPEN.value:
            raise ValidationError("Cash session is not open")
        return cash_session

    async def _get_draft_sale(self, tenant_id: UUID, sale_id: UUID) -> Sale:
        sale = await self.sale_repo.get_by_id(sale_id)
        if sale is None or sale.tenant_id != tenant_id:
            raise NotFoundError("Sale", sale_id)
        if sale.status != SaleStatus.DRAFT.value:
            raise ValidationError("Only draft sales can be modified")
        return sale

    async def _generate_sale_number(self, tenant_id: UUID) -> str:
        count = await self.sale_repo.count_for_tenant(tenant_id)
        return f"SAL-{count + 1:06d}"

    async def _get_tax_rate(self, tenant_id: UUID, store_id: UUID | None) -> Decimal:
        if store_id is None:
            return Decimal("0")
        settings = await self.settings_repo.get_by_store_id(tenant_id, store_id)
        return Decimal(str(settings.tax_rate)) if settings else Decimal("0")
