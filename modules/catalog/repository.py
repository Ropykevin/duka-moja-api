from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.modules.catalog.models import (
    Attribute,
    AttributeValue,
    Brand,
    Category,
    Product,
    ProductImage,
    ProductVariant,
)
from app.shared.base_repository import TenantScopedRepository


class CategoryRepository(TenantScopedRepository[Category]):
    model = Category

    async def get_by_slug(self, tenant_id: UUID, slug: str) -> Category | None:
        stmt = select(Category).where(Category.tenant_id == tenant_id, Category.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_roots(self, tenant_id: UUID) -> list[Category]:
        stmt = (
            select(Category)
            .where(Category.tenant_id == tenant_id, Category.parent_id.is_(None))
            .options(selectinload(Category.children))
            .order_by(Category.sort_order, Category.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def count_children(self, category_id: UUID) -> int:
        stmt = select(func.count()).select_from(Category).where(Category.parent_id == category_id)
        return (await self.session.execute(stmt)).scalar_one()

    async def count_products(self, category_id: UUID) -> int:
        stmt = select(func.count()).select_from(Product).where(Product.category_id == category_id)
        return (await self.session.execute(stmt)).scalar_one()


class BrandRepository(TenantScopedRepository[Brand]):
    model = Brand

    async def get_by_slug(self, tenant_id: UUID, slug: str) -> Brand | None:
        stmt = select(Brand).where(Brand.tenant_id == tenant_id, Brand.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(self, tenant_id: UUID, *, offset: int = 0, limit: int = 100) -> tuple[list[Brand], int]:
        count_stmt = select(func.count()).select_from(Brand).where(
            Brand.tenant_id == tenant_id, Brand.is_active.is_(True)
        )
        total = (await self.session.execute(count_stmt)).scalar_one()
        stmt = (
            select(Brand)
            .where(Brand.tenant_id == tenant_id, Brand.is_active.is_(True))
            .offset(offset)
            .limit(limit)
            .order_by(Brand.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total


class AttributeRepository(TenantScopedRepository[Attribute]):
    model = Attribute

    async def get_by_code(self, tenant_id: UUID, code: str) -> Attribute | None:
        stmt = (
            select(Attribute)
            .where(Attribute.tenant_id == tenant_id, Attribute.code == code)
            .options(selectinload(Attribute.values))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_values(self, tenant_id: UUID, attribute_id: UUID) -> Attribute | None:
        stmt = (
            select(Attribute)
            .where(Attribute.tenant_id == tenant_id, Attribute.id == attribute_id)
            .options(selectinload(Attribute.values))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all_for_tenant(self, tenant_id: UUID) -> list[Attribute]:
        stmt = (
            select(Attribute)
            .where(Attribute.tenant_id == tenant_id)
            .options(selectinload(Attribute.values))
            .order_by(Attribute.sort_order, Attribute.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class AttributeValueRepository(TenantScopedRepository[AttributeValue]):
    model = AttributeValue

    async def get_by_ids(self, tenant_id: UUID, ids: list[UUID]) -> list[AttributeValue]:
        if not ids:
            return []
        stmt = select(AttributeValue).where(
            AttributeValue.tenant_id == tenant_id,
            AttributeValue.id.in_(ids),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ProductRepository(TenantScopedRepository[Product]):
    model = Product

    async def get_by_slug(self, tenant_id: UUID, slug: str) -> Product | None:
        stmt = select(Product).where(Product.tenant_id == tenant_id, Product.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_sku(self, tenant_id: UUID, sku: str) -> Product | None:
        stmt = select(Product).where(Product.tenant_id == tenant_id, Product.sku == sku)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_details(self, tenant_id: UUID, product_id: UUID) -> Product | None:
        stmt = (
            select(Product)
            .where(Product.tenant_id == tenant_id, Product.id == product_id)
            .options(
                selectinload(Product.variants).selectinload(ProductVariant.attribute_values),
                selectinload(Product.images),
                selectinload(Product.attributes).selectinload(Attribute.values),
                selectinload(Product.category),
                selectinload(Product.brand),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_tenant_filtered(
        self,
        tenant_id: UUID,
        *,
        category_id: UUID | None = None,
        brand_id: UUID | None = None,
        status: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Product], int]:
        filters = [Product.tenant_id == tenant_id]
        if category_id:
            filters.append(Product.category_id == category_id)
        if brand_id:
            filters.append(Product.brand_id == brand_id)
        if status:
            filters.append(Product.status == status)
        if search:
            pattern = f"%{search}%"
            filters.append(or_(Product.name.ilike(pattern), Product.sku.ilike(pattern)))

        count_stmt = select(func.count()).select_from(Product).where(*filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(Product)
            .where(*filters)
            .offset(offset)
            .limit(limit)
            .order_by(Product.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total


class ProductVariantRepository(TenantScopedRepository[ProductVariant]):
    model = ProductVariant

    async def get_by_sku(self, tenant_id: UUID, sku: str) -> ProductVariant | None:
        stmt = select(ProductVariant).where(
            ProductVariant.tenant_id == tenant_id, ProductVariant.sku == sku
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_for_product(
        self, tenant_id: UUID, product_id: UUID, variant_id: UUID
    ) -> ProductVariant | None:
        stmt = (
            select(ProductVariant)
            .where(
                ProductVariant.tenant_id == tenant_id,
                ProductVariant.product_id == product_id,
                ProductVariant.id == variant_id,
            )
            .options(selectinload(ProductVariant.attribute_values))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def clear_default_flag(self, product_id: UUID, exclude_id: UUID | None = None) -> None:
        from sqlalchemy import update

        stmt = update(ProductVariant).where(
            ProductVariant.product_id == product_id,
            ProductVariant.is_default.is_(True),
        )
        if exclude_id:
            stmt = stmt.where(ProductVariant.id != exclude_id)
        await self.session.execute(stmt.values(is_default=False))


class ProductImageRepository(TenantScopedRepository[ProductImage]):
    model = ProductImage

    async def clear_primary_flag(self, product_id: UUID, exclude_id: UUID | None = None) -> None:
        from sqlalchemy import update

        stmt = update(ProductImage).where(
            ProductImage.product_id == product_id,
            ProductImage.is_primary.is_(True),
        )
        if exclude_id:
            stmt = stmt.where(ProductImage.id != exclude_id)
        await self.session.execute(stmt.values(is_primary=False))
