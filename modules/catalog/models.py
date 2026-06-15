import uuid

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.base_model import ProductStatus, ProductType, TenantScopedModel
from app.shared.types import GUID

product_attributes = Table(
    "product_attributes",
    Base.metadata,
    Column("product_id", GUID(), ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("attribute_id", GUID(), ForeignKey("attributes.id", ondelete="CASCADE"), primary_key=True),
)

product_variant_attribute_values = Table(
    "product_variant_attribute_values",
    Base.metadata,
    Column(
        "variant_id", GUID(), ForeignKey("product_variants.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "attribute_value_id",
        GUID(),
        ForeignKey("attribute_values.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Category(TenantScopedModel):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_categories_tenant_slug"),
    )

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    parent: Mapped["Category | None"] = relationship(
        back_populates="children", remote_side="Category.id"
    )
    children: Mapped[list["Category"]] = relationship(back_populates="parent")
    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Brand(TenantScopedModel):
    __tablename__ = "brands"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_brands_tenant_slug"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    products: Mapped[list["Product"]] = relationship(back_populates="brand")


class Attribute(TenantScopedModel):
    __tablename__ = "attributes"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_attributes_tenant_code"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    display_type: Mapped[str] = mapped_column(String(20), default="select", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    values: Mapped[list["AttributeValue"]] = relationship(
        back_populates="attribute", cascade="all, delete-orphan", lazy="selectin"
    )
    products: Mapped[list["Product"]] = relationship(
        secondary=product_attributes, back_populates="attributes"
    )


class AttributeValue(TenantScopedModel):
    __tablename__ = "attribute_values"
    __table_args__ = (
        UniqueConstraint("attribute_id", "value", name="uq_attribute_values_attr_value"),
    )

    attribute_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("attributes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    attribute: Mapped["Attribute"] = relationship(back_populates="values")
    variants: Mapped[list["ProductVariant"]] = relationship(
        secondary=product_variant_attribute_values, back_populates="attribute_values"
    )


class Product(TenantScopedModel):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_products_tenant_slug"),
        UniqueConstraint("tenant_id", "sku", name="uq_products_tenant_sku"),
    )

    store_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("stores.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("brands.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    barcode: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    product_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ProductType.SIMPLE.value
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ProductStatus.DRAFT.value
    )
    base_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    compare_at_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    cost_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    track_inventory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_taxable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    weight: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    weight_unit: Mapped[str] = mapped_column(String(10), default="kg", nullable=False)

    category: Mapped["Category | None"] = relationship(back_populates="products")
    brand: Mapped["Brand | None"] = relationship(back_populates="products")
    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", lazy="selectin"
    )
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", lazy="selectin"
    )
    attributes: Mapped[list["Attribute"]] = relationship(
        secondary=product_attributes, back_populates="products"
    )


class ProductVariant(TenantScopedModel):
    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("tenant_id", "sku", name="uq_product_variants_tenant_sku"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    barcode: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    price: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    compare_at_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    cost_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    weight: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    product: Mapped["Product"] = relationship(back_populates="variants")
    images: Mapped[list["ProductImage"]] = relationship(back_populates="variant")
    attribute_values: Mapped[list["AttributeValue"]] = relationship(
        secondary=product_variant_attribute_values, back_populates="variants"
    )


class ProductImage(TenantScopedModel):
    __tablename__ = "product_images"

    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    product: Mapped["Product"] = relationship(back_populates="images")
    variant: Mapped["ProductVariant | None"] = relationship(back_populates="images")
