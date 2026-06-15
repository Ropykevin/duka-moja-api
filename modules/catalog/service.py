from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.catalog.models import (
    Attribute,
    AttributeValue,
    Brand,
    Category,
    Product,
    ProductImage,
    ProductVariant,
)
from app.modules.catalog.repository import (
    AttributeRepository,
    AttributeValueRepository,
    BrandRepository,
    CategoryRepository,
    ProductImageRepository,
    ProductRepository,
    ProductVariantRepository,
)
from app.modules.catalog.schemas import (
    AttributeCreate,
    AttributeResponse,
    AttributeUpdate,
    AttributeValueCreate,
    AttributeValueResponse,
    BrandCreate,
    BrandResponse,
    BrandUpdate,
    CategoryCreate,
    CategoryResponse,
    CategoryTreeResponse,
    CategoryUpdate,
    ProductCreate,
    ProductDetailResponse,
    ProductImageCreate,
    ProductImageResponse,
    ProductResponse,
    ProductUpdate,
    ProductVariantCreate,
    ProductVariantResponse,
    ProductVariantUpdate,
)
from app.modules.stores.repository import StoreRepository
from app.shared.base_model import ProductStatus, ProductType
from app.shared.schemas import PaginatedResponse


class CategoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CategoryRepository(session)

    async def create(self, tenant_id: UUID, data: CategoryCreate) -> CategoryResponse:
        if await self.repo.get_by_slug(tenant_id, data.slug):
            raise ConflictError(f"Category slug '{data.slug}' already exists")
        if data.parent_id:
            await self._validate_parent(tenant_id, data.parent_id)

        category = Category(
            tenant_id=tenant_id,
            name=data.name,
            slug=data.slug,
            parent_id=data.parent_id,
            description=data.description,
            image_url=data.image_url,
            sort_order=data.sort_order,
            is_active=data.is_active,
        )
        category = await self.repo.create(category)
        return CategoryResponse.model_validate(category)

    async def list_tree(self, tenant_id: UUID) -> list[CategoryTreeResponse]:
        roots = await self.repo.list_roots(tenant_id)
        return [self._build_tree(cat) for cat in roots]

    async def list_flat(
        self, tenant_id: UUID, *, page: int = 1, page_size: int = 50
    ) -> PaginatedResponse[CategoryResponse]:
        items, total = await self.repo.list_for_tenant(
            tenant_id, offset=(page - 1) * page_size, limit=page_size
        )
        return PaginatedResponse.create(
            [CategoryResponse.model_validate(c) for c in items], total, page, page_size
        )

    async def get(self, tenant_id: UUID, category_id: UUID) -> CategoryResponse:
        category = await self._get_or_raise(tenant_id, category_id)
        return CategoryResponse.model_validate(category)

    async def update(
        self, tenant_id: UUID, category_id: UUID, data: CategoryUpdate
    ) -> CategoryResponse:
        category = await self._get_or_raise(tenant_id, category_id)
        update_data = data.model_dump(exclude_unset=True)

        if "parent_id" in update_data:
            new_parent = update_data["parent_id"]
            if new_parent == category_id:
                raise ValidationError("Category cannot be its own parent")
            if new_parent:
                await self._validate_parent(tenant_id, new_parent, exclude_id=category_id)

        for field, value in update_data.items():
            setattr(category, field, value)

        category = await self.repo.update(category)
        return CategoryResponse.model_validate(category)

    async def delete(self, tenant_id: UUID, category_id: UUID) -> None:
        category = await self._get_or_raise(tenant_id, category_id)
        if await self.repo.count_children(category_id) > 0:
            raise ValidationError("Cannot delete category with subcategories")
        if await self.repo.count_products(category_id) > 0:
            raise ValidationError("Cannot delete category with assigned products")
        await self.repo.delete(category)

    async def _get_or_raise(self, tenant_id: UUID, category_id: UUID) -> Category:
        category = await self.repo.get_by_id(category_id)
        if category is None or category.tenant_id != tenant_id:
            raise NotFoundError("Category", category_id)
        return category

    async def _validate_parent(
        self, tenant_id: UUID, parent_id: UUID, exclude_id: UUID | None = None
    ) -> None:
        parent = await self.repo.get_by_id(parent_id)
        if parent is None or parent.tenant_id != tenant_id:
            raise NotFoundError("Category", parent_id)
        if exclude_id and parent.parent_id == exclude_id:
            raise ValidationError("Circular category hierarchy detected")

    def _build_tree(self, category: Category) -> CategoryTreeResponse:
        node = CategoryTreeResponse.model_validate(category)
        node.children = [self._build_tree(child) for child in category.children]
        return node


class BrandService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = BrandRepository(session)

    async def create(self, tenant_id: UUID, data: BrandCreate) -> BrandResponse:
        if await self.repo.get_by_slug(tenant_id, data.slug):
            raise ConflictError(f"Brand slug '{data.slug}' already exists")
        brand = Brand(
            tenant_id=tenant_id,
            name=data.name,
            slug=data.slug,
            description=data.description,
            logo_url=data.logo_url,
            is_active=data.is_active,
        )
        brand = await self.repo.create(brand)
        return BrandResponse.model_validate(brand)

    async def list(
        self, tenant_id: UUID, *, page: int = 1, page_size: int = 20
    ) -> PaginatedResponse[BrandResponse]:
        items, total = await self.repo.list_active(
            tenant_id, offset=(page - 1) * page_size, limit=page_size
        )
        return PaginatedResponse.create(
            [BrandResponse.model_validate(b) for b in items], total, page, page_size
        )

    async def get(self, tenant_id: UUID, brand_id: UUID) -> BrandResponse:
        brand = await self._get_or_raise(tenant_id, brand_id)
        return BrandResponse.model_validate(brand)

    async def update(
        self, tenant_id: UUID, brand_id: UUID, data: BrandUpdate
    ) -> BrandResponse:
        brand = await self._get_or_raise(tenant_id, brand_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(brand, field, value)
        brand = await self.repo.update(brand)
        return BrandResponse.model_validate(brand)

    async def delete(self, tenant_id: UUID, brand_id: UUID) -> None:
        brand = await self._get_or_raise(tenant_id, brand_id)
        brand.is_active = False
        await self.repo.update(brand)

    async def _get_or_raise(self, tenant_id: UUID, brand_id: UUID) -> Brand:
        brand = await self.repo.get_by_id(brand_id)
        if brand is None or brand.tenant_id != tenant_id:
            raise NotFoundError("Brand", brand_id)
        return brand


class AttributeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AttributeRepository(session)
        self.value_repo = AttributeValueRepository(session)

    async def create(self, tenant_id: UUID, data: AttributeCreate) -> AttributeResponse:
        if await self.repo.get_by_code(tenant_id, data.code):
            raise ConflictError(f"Attribute code '{data.code}' already exists")

        attribute = Attribute(
            tenant_id=tenant_id,
            name=data.name,
            code=data.code,
            display_type=data.display_type.value,
            sort_order=data.sort_order,
        )
        attribute = await self.repo.create(attribute)

        for val in data.values:
            await self.value_repo.create(
                AttributeValue(
                    tenant_id=tenant_id,
                    attribute_id=attribute.id,
                    value=val.value,
                    sort_order=val.sort_order,
                )
            )

        attribute = await self.repo.get_with_values(tenant_id, attribute.id)
        return AttributeResponse.model_validate(attribute)

    async def list(self, tenant_id: UUID) -> list[AttributeResponse]:
        attributes = await self.repo.list_all_for_tenant(tenant_id)
        return [AttributeResponse.model_validate(a) for a in attributes]

    async def get(self, tenant_id: UUID, attribute_id: UUID) -> AttributeResponse:
        attribute = await self.repo.get_with_values(tenant_id, attribute_id)
        if attribute is None:
            raise NotFoundError("Attribute", attribute_id)
        return AttributeResponse.model_validate(attribute)

    async def update(
        self, tenant_id: UUID, attribute_id: UUID, data: AttributeUpdate
    ) -> AttributeResponse:
        attribute = await self.repo.get_with_values(tenant_id, attribute_id)
        if attribute is None:
            raise NotFoundError("Attribute", attribute_id)

        update_data = data.model_dump(exclude_unset=True)
        if "display_type" in update_data and update_data["display_type"]:
            update_data["display_type"] = update_data["display_type"].value

        for field, value in update_data.items():
            setattr(attribute, field, value)

        attribute = await self.repo.update(attribute)
        return AttributeResponse.model_validate(attribute)

    async def add_value(
        self, tenant_id: UUID, attribute_id: UUID, data: AttributeValueCreate
    ) -> AttributeValueResponse:
        attribute = await self.repo.get_by_id(attribute_id)
        if attribute is None or attribute.tenant_id != tenant_id:
            raise NotFoundError("Attribute", attribute_id)

        value = AttributeValue(
            tenant_id=tenant_id,
            attribute_id=attribute_id,
            value=data.value,
            sort_order=data.sort_order,
        )
        value = await self.value_repo.create(value)
        return AttributeValueResponse.model_validate(value)

    async def delete(self, tenant_id: UUID, attribute_id: UUID) -> None:
        attribute = await self.repo.get_by_id(attribute_id)
        if attribute is None or attribute.tenant_id != tenant_id:
            raise NotFoundError("Attribute", attribute_id)
        await self.repo.delete(attribute)


class ProductService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.product_repo = ProductRepository(session)
        self.variant_repo = ProductVariantRepository(session)
        self.image_repo = ProductImageRepository(session)
        self.category_repo = CategoryRepository(session)
        self.brand_repo = BrandRepository(session)
        self.attribute_repo = AttributeRepository(session)
        self.attribute_value_repo = AttributeValueRepository(session)
        self.store_repo = StoreRepository(session)

    async def create(self, tenant_id: UUID, data: ProductCreate) -> ProductDetailResponse:
        if await self.product_repo.get_by_slug(tenant_id, data.slug):
            raise ConflictError(f"Product slug '{data.slug}' already exists")
        if await self.product_repo.get_by_sku(tenant_id, data.sku):
            raise ConflictError(f"Product SKU '{data.sku}' already exists")

        await self._validate_refs(tenant_id, data.store_id, data.category_id, data.brand_id)

        if data.product_type == ProductType.VARIABLE and not data.variants:
            raise ValidationError("Variable products require at least one variant")

        product = Product(
            tenant_id=tenant_id,
            store_id=data.store_id,
            category_id=data.category_id,
            brand_id=data.brand_id,
            name=data.name,
            slug=data.slug,
            sku=data.sku,
            barcode=data.barcode,
            description=data.description,
            short_description=data.short_description,
            product_type=data.product_type.value,
            status=ProductStatus.DRAFT.value,
            base_price=data.base_price,
            compare_at_price=data.compare_at_price,
            cost_price=data.cost_price,
            track_inventory=data.track_inventory,
            is_taxable=data.is_taxable,
            weight=data.weight,
            weight_unit=data.weight_unit,
        )

        if data.attribute_ids:
            product.attributes = await self._resolve_attributes(tenant_id, data.attribute_ids)

        product = await self.product_repo.create(product)

        if data.product_type == ProductType.VARIABLE:
            for i, variant_data in enumerate(data.variants):
                await self._create_variant(tenant_id, product, variant_data, is_first=(i == 0))
        elif data.product_type == ProductType.SIMPLE:
            await self._create_variant(
                tenant_id,
                product,
                ProductVariantCreate(
                    name=product.name,
                    sku=product.sku,
                    barcode=product.barcode,
                    price=data.base_price,
                    compare_at_price=data.compare_at_price,
                    cost_price=data.cost_price,
                    weight=data.weight,
                    is_default=True,
                ),
                is_first=True,
            )

        for image_data in data.images:
            await self._create_image(tenant_id, product.id, image_data)

        return await self.get(tenant_id, product.id)

    async def list(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        category_id: UUID | None = None,
        brand_id: UUID | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> PaginatedResponse[ProductResponse]:
        items, total = await self.product_repo.list_for_tenant_filtered(
            tenant_id,
            category_id=category_id,
            brand_id=brand_id,
            status=status,
            search=search,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return PaginatedResponse.create(
            [ProductResponse.model_validate(p) for p in items], total, page, page_size
        )

    async def get(self, tenant_id: UUID, product_id: UUID) -> ProductDetailResponse:
        product = await self.product_repo.get_with_details(tenant_id, product_id)
        if product is None:
            raise NotFoundError("Product", product_id)
        return ProductDetailResponse.model_validate(product)

    async def update(
        self, tenant_id: UUID, product_id: UUID, data: ProductUpdate
    ) -> ProductDetailResponse:
        product = await self.product_repo.get_with_details(tenant_id, product_id)
        if product is None:
            raise NotFoundError("Product", product_id)

        update_data = data.model_dump(exclude_unset=True)

        if "store_id" in update_data or "category_id" in update_data or "brand_id" in update_data:
            await self._validate_refs(
                tenant_id,
                update_data.get("store_id", product.store_id),
                update_data.get("category_id", product.category_id),
                update_data.get("brand_id", product.brand_id),
            )

        if "status" in update_data and update_data["status"]:
            update_data["status"] = update_data["status"].value

        attribute_ids = update_data.pop("attribute_ids", None)
        for field, value in update_data.items():
            setattr(product, field, value)

        if attribute_ids is not None:
            product.attributes = await self._resolve_attributes(tenant_id, attribute_ids)

        await self.product_repo.update(product)
        return await self.get(tenant_id, product_id)

    async def delete(self, tenant_id: UUID, product_id: UUID) -> None:
        product = await self.product_repo.get_by_id(product_id)
        if product is None or product.tenant_id != tenant_id:
            raise NotFoundError("Product", product_id)
        product.status = ProductStatus.ARCHIVED.value
        await self.product_repo.update(product)

    async def add_variant(
        self, tenant_id: UUID, product_id: UUID, data: ProductVariantCreate
    ) -> ProductVariantResponse:
        product = await self.product_repo.get_by_id(product_id)
        if product is None or product.tenant_id != tenant_id:
            raise NotFoundError("Product", product_id)
        if product.product_type != ProductType.VARIABLE.value:
            raise ValidationError("Variants can only be added to variable products")

        if await self.variant_repo.get_by_sku(tenant_id, data.sku):
            raise ConflictError(f"Variant SKU '{data.sku}' already exists")

        variant = await self._create_variant(tenant_id, product, data, is_first=False)
        return ProductVariantResponse.model_validate(variant)

    async def update_variant(
        self,
        tenant_id: UUID,
        product_id: UUID,
        variant_id: UUID,
        data: ProductVariantUpdate,
    ) -> ProductVariantResponse:
        variant = await self.variant_repo.get_for_product(tenant_id, product_id, variant_id)
        if variant is None:
            raise NotFoundError("ProductVariant", variant_id)

        update_data = data.model_dump(exclude_unset=True)
        attribute_value_ids = update_data.pop("attribute_value_ids", None)

        if update_data.get("is_default"):
            await self.variant_repo.clear_default_flag(product_id, exclude_id=variant_id)

        for field, value in update_data.items():
            setattr(variant, field, value)

        if attribute_value_ids is not None:
            variant.attribute_values = await self.attribute_value_repo.get_by_ids(
                tenant_id, attribute_value_ids
            )

        variant = await self.variant_repo.update(variant)
        return ProductVariantResponse.model_validate(variant)

    async def add_image(
        self, tenant_id: UUID, product_id: UUID, data: ProductImageCreate
    ) -> ProductImageResponse:
        product = await self.product_repo.get_by_id(product_id)
        if product is None or product.tenant_id != tenant_id:
            raise NotFoundError("Product", product_id)
        image = await self._create_image(tenant_id, product_id, data)
        return ProductImageResponse.model_validate(image)

    async def _create_variant(
        self,
        tenant_id: UUID,
        product: Product,
        data: ProductVariantCreate,
        *,
        is_first: bool,
    ) -> ProductVariant:
        if await self.variant_repo.get_by_sku(tenant_id, data.sku):
            raise ConflictError(f"Variant SKU '{data.sku}' already exists")

        is_default = data.is_default or is_first
        if is_default:
            await self.variant_repo.clear_default_flag(product.id)

        attribute_values = []
        if data.attribute_value_ids:
            attribute_values = await self.attribute_value_repo.get_by_ids(
                tenant_id, data.attribute_value_ids
            )

        variant = ProductVariant(
            tenant_id=tenant_id,
            product_id=product.id,
            name=data.name,
            sku=data.sku,
            barcode=data.barcode,
            price=data.price,
            compare_at_price=data.compare_at_price,
            cost_price=data.cost_price,
            weight=data.weight,
            is_default=is_default,
            sort_order=data.sort_order,
            attribute_values=attribute_values,
        )
        return await self.variant_repo.create(variant)

    async def _create_image(
        self, tenant_id: UUID, product_id: UUID, data: ProductImageCreate
    ) -> ProductImage:
        if data.is_primary:
            await self.image_repo.clear_primary_flag(product_id)

        image = ProductImage(
            tenant_id=tenant_id,
            product_id=product_id,
            variant_id=data.variant_id,
            url=data.url,
            alt_text=data.alt_text,
            sort_order=data.sort_order,
            is_primary=data.is_primary,
        )
        return await self.image_repo.create(image)

    async def _validate_refs(
        self,
        tenant_id: UUID,
        store_id: UUID | None,
        category_id: UUID | None,
        brand_id: UUID | None,
    ) -> None:
        if store_id:
            store = await self.store_repo.get_by_id(store_id)
            if store is None or store.tenant_id != tenant_id:
                raise NotFoundError("Store", store_id)
        if category_id:
            cat = await self.category_repo.get_by_id(category_id)
            if cat is None or cat.tenant_id != tenant_id:
                raise NotFoundError("Category", category_id)
        if brand_id:
            brand = await self.brand_repo.get_by_id(brand_id)
            if brand is None or brand.tenant_id != tenant_id:
                raise NotFoundError("Brand", brand_id)

    async def _resolve_attributes(
        self, tenant_id: UUID, attribute_ids: list[UUID]
    ) -> list[Attribute]:
        attributes = []
        for attr_id in attribute_ids:
            attr = await self.attribute_repo.get_by_id(attr_id)
            if attr is None or attr.tenant_id != tenant_id:
                raise NotFoundError("Attribute", attr_id)
            attributes.append(attr)
        return attributes
