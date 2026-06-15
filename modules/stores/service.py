from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.modules.stores.models import Branch, Store, StoreSettings
from app.modules.stores.repository import BranchRepository, StoreRepository, StoreSettingsRepository
from app.modules.stores.schemas import (
    BranchCreate,
    BranchResponse,
    BranchUpdate,
    StoreCreate,
    StoreDetailResponse,
    StoreResponse,
    StoreSettingsResponse,
    StoreSettingsUpdate,
    StoreUpdate,
)
from app.modules.subscriptions.service import SubscriptionService
from app.shared.base_model import BranchStatus, StoreStatus
from app.shared.schemas import PaginatedResponse


class StoreService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.store_repo = StoreRepository(session)
        self.settings_repo = StoreSettingsRepository(session)
        self.branch_repo = BranchRepository(session)
        self.subscription_service = SubscriptionService(session)

    async def create_store(self, tenant_id: UUID, data: StoreCreate) -> StoreDetailResponse:
        existing = await self.store_repo.get_by_slug(tenant_id, data.slug)
        if existing:
            raise ConflictError(f"Store slug '{data.slug}' already exists")

        store_count = await self.store_repo.count_for_tenant(tenant_id)
        is_default = data.is_default or store_count == 0

        if is_default:
            await self.store_repo.clear_default_flag(tenant_id)

        store = Store(
            tenant_id=tenant_id,
            name=data.name,
            slug=data.slug,
            description=data.description,
            email=str(data.email) if data.email else None,
            phone=data.phone,
            currency=data.currency,
            timezone=data.timezone,
            logo_url=data.logo_url,
            address_line1=data.address_line1,
            address_line2=data.address_line2,
            city=data.city,
            state=data.state,
            postal_code=data.postal_code,
            country=data.country,
            is_default=is_default,
            status=StoreStatus.ACTIVE.value,
        )
        store = await self.store_repo.create(store)

        settings = StoreSettings(
            tenant_id=tenant_id,
            store_id=store.id,
            default_currency=data.currency,
        )
        settings = await self.settings_repo.create(settings)

        if store_count == 0:
            hq_branch = Branch(
                tenant_id=tenant_id,
                store_id=store.id,
                name=f"{store.name} HQ",
                code="HQ",
                is_headquarters=True,
                status=BranchStatus.ACTIVE.value,
                address_line1=data.address_line1,
                city=data.city,
                country=data.country,
            )
            await self.branch_repo.create(hq_branch)

        response = StoreDetailResponse.model_validate(store)
        response.settings = StoreSettingsResponse.model_validate(settings)
        response.branch_count = 1 if store_count == 0 else 0
        return response

    async def list_stores(
        self, tenant_id: UUID, *, page: int = 1, page_size: int = 20
    ) -> PaginatedResponse[StoreResponse]:
        items, total = await self.store_repo.list_for_tenant(
            tenant_id, offset=(page - 1) * page_size, limit=page_size
        )
        return PaginatedResponse.create(
            [StoreResponse.model_validate(s) for s in items], total, page, page_size
        )

    async def get_store(self, tenant_id: UUID, store_id: UUID) -> StoreDetailResponse:
        store = await self.store_repo.get_with_details(tenant_id, store_id)
        if store is None:
            raise NotFoundError("Store", store_id)

        response = StoreDetailResponse.model_validate(store)
        if store.settings:
            response.settings = StoreSettingsResponse.model_validate(store.settings)
        response.branch_count = len(store.branches)
        return response

    async def update_store(
        self, tenant_id: UUID, store_id: UUID, data: StoreUpdate
    ) -> StoreResponse:
        store = await self._get_store_or_raise(tenant_id, store_id)
        update_data = data.model_dump(exclude_unset=True)

        if update_data.get("is_default"):
            await self.store_repo.clear_default_flag(tenant_id, exclude_id=store_id)

        if "email" in update_data and update_data["email"] is not None:
            update_data["email"] = str(update_data["email"])
        if "status" in update_data and update_data["status"] is not None:
            update_data["status"] = update_data["status"].value

        for field, value in update_data.items():
            setattr(store, field, value)

        store = await self.store_repo.update(store)
        return StoreResponse.model_validate(store)

    async def delete_store(self, tenant_id: UUID, store_id: UUID) -> None:
        store = await self._get_store_or_raise(tenant_id, store_id)
        if store.is_default:
            raise ValidationError("Cannot delete the default store. Set another store as default first.")
        store.status = StoreStatus.CLOSED.value
        await self.store_repo.update(store)

    async def get_settings(
        self, tenant_id: UUID, store_id: UUID
    ) -> StoreSettingsResponse:
        await self._get_store_or_raise(tenant_id, store_id)
        settings = await self.settings_repo.get_by_store_id(tenant_id, store_id)
        if settings is None:
            raise NotFoundError("StoreSettings", store_id)
        return StoreSettingsResponse.model_validate(settings)

    async def update_settings(
        self, tenant_id: UUID, store_id: UUID, data: StoreSettingsUpdate
    ) -> StoreSettingsResponse:
        await self._get_store_or_raise(tenant_id, store_id)
        settings = await self.settings_repo.get_by_store_id(tenant_id, store_id)
        if settings is None:
            raise NotFoundError("StoreSettings", store_id)

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(settings, field, value)

        settings = await self.settings_repo.update(settings)
        return StoreSettingsResponse.model_validate(settings)

    async def _get_store_or_raise(self, tenant_id: UUID, store_id: UUID) -> Store:
        store = await self.store_repo.get_by_id(store_id)
        if store is None or store.tenant_id != tenant_id:
            raise NotFoundError("Store", store_id)
        return store


class BranchService:
    MAX_BRANCHES_WITHOUT_FEATURE = 1

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.branch_repo = BranchRepository(session)
        self.store_repo = StoreRepository(session)
        self.subscription_service = SubscriptionService(session)

    async def create_branch(self, tenant_id: UUID, data: BranchCreate) -> BranchResponse:
        store = await self.store_repo.get_by_id(data.store_id)
        if store is None or store.tenant_id != tenant_id:
            raise NotFoundError("Store", data.store_id)

        existing = await self.branch_repo.get_by_code(tenant_id, data.store_id, data.code)
        if existing:
            raise ConflictError(f"Branch code '{data.code}' already exists for this store")

        branch_count = await self.branch_repo.count_for_tenant(tenant_id)
        has_multi_branch = await self.subscription_service.tenant_has_feature(
            tenant_id, "multi_branch"
        )
        if branch_count >= self.MAX_BRANCHES_WITHOUT_FEATURE and not has_multi_branch:
            raise ForbiddenError(
                "Multi-branch feature required to create additional branches. "
                "Upgrade your subscription plan."
            )

        if data.is_headquarters:
            await self.branch_repo.clear_headquarters_flag(tenant_id, data.store_id)

        branch = Branch(
            tenant_id=tenant_id,
            store_id=data.store_id,
            name=data.name,
            code=data.code,
            email=str(data.email) if data.email else None,
            phone=data.phone,
            is_headquarters=data.is_headquarters,
            status=BranchStatus.ACTIVE.value,
            address_line1=data.address_line1,
            address_line2=data.address_line2,
            city=data.city,
            state=data.state,
            postal_code=data.postal_code,
            country=data.country,
            latitude=data.latitude,
            longitude=data.longitude,
        )
        branch = await self.branch_repo.create(branch)
        return BranchResponse.model_validate(branch)

    async def list_branches(
        self,
        tenant_id: UUID,
        store_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[BranchResponse]:
        await self._validate_store(tenant_id, store_id)
        items, total = await self.branch_repo.list_for_store(
            tenant_id, store_id, offset=(page - 1) * page_size, limit=page_size
        )
        return PaginatedResponse.create(
            [BranchResponse.model_validate(b) for b in items], total, page, page_size
        )

    async def get_branch(
        self, tenant_id: UUID, store_id: UUID, branch_id: UUID
    ) -> BranchResponse:
        branch = await self._get_branch_or_raise(tenant_id, store_id, branch_id)
        return BranchResponse.model_validate(branch)

    async def update_branch(
        self, tenant_id: UUID, store_id: UUID, branch_id: UUID, data: BranchUpdate
    ) -> BranchResponse:
        branch = await self._get_branch_or_raise(tenant_id, store_id, branch_id)
        update_data = data.model_dump(exclude_unset=True)

        if update_data.get("is_headquarters"):
            await self.branch_repo.clear_headquarters_flag(
                tenant_id, store_id, exclude_id=branch_id
            )

        if "email" in update_data and update_data["email"] is not None:
            update_data["email"] = str(update_data["email"])
        if "status" in update_data and update_data["status"] is not None:
            update_data["status"] = update_data["status"].value

        for field, value in update_data.items():
            setattr(branch, field, value)

        branch = await self.branch_repo.update(branch)
        return BranchResponse.model_validate(branch)

    async def delete_branch(
        self, tenant_id: UUID, store_id: UUID, branch_id: UUID
    ) -> None:
        branch = await self._get_branch_or_raise(tenant_id, store_id, branch_id)
        if branch.is_headquarters:
            raise ValidationError("Cannot deactivate the headquarters branch.")
        branch.status = BranchStatus.INACTIVE.value
        await self.branch_repo.update(branch)

    async def _validate_store(self, tenant_id: UUID, store_id: UUID) -> None:
        store = await self.store_repo.get_by_id(store_id)
        if store is None or store.tenant_id != tenant_id:
            raise NotFoundError("Store", store_id)

    async def _get_branch_or_raise(
        self, tenant_id: UUID, store_id: UUID, branch_id: UUID
    ) -> Branch:
        branch = await self.branch_repo.get_by_id(branch_id)
        if (
            branch is None
            or branch.tenant_id != tenant_id
            or branch.store_id != store_id
        ):
            raise NotFoundError("Branch", branch_id)
        return branch
