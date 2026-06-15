from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.shared.base_model import AttributeDisplayType, ProductStatus, ProductType
from app.shared.schemas import BaseSchema


# --- Category ---

class CategoryCreate(BaseSchema):
    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    parent_id: UUID | None = None
    description: str | None = Field(default=None, max_length=2000)
    image_url: str | None = Field(default=None, max_length=500)
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = True


class CategoryUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    parent_id: UUID | None = None
    description: str | None = Field(default=None, max_length=2000)
    image_url: str | None = Field(default=None, max_length=500)
    sort_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class CategoryResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    parent_id: UUID | None
    name: str
    slug: str
    description: str | None
    image_url: str | None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CategoryTreeResponse(CategoryResponse):
    children: list["CategoryTreeResponse"] = []


# --- Brand ---

class BrandCreate(BaseSchema):
    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(default=None, max_length=2000)
    logo_url: str | None = Field(default=None, max_length=500)
    is_active: bool = True


class BrandUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    logo_url: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class BrandResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    description: str | None
    logo_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# --- Attribute ---

class AttributeValueCreate(BaseSchema):
    value: str = Field(min_length=1, max_length=100)
    sort_order: int = Field(default=0, ge=0)


class AttributeValueResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    attribute_id: UUID
    value: str
    sort_order: int


class AttributeCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9_]+$")
    display_type: AttributeDisplayType = AttributeDisplayType.SELECT
    sort_order: int = Field(default=0, ge=0)
    values: list[AttributeValueCreate] = []


class AttributeUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    display_type: AttributeDisplayType | None = None
    sort_order: int | None = Field(default=None, ge=0)


class AttributeResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    name: str
    code: str
    display_type: str
    sort_order: int
    values: list[AttributeValueResponse] = []
    created_at: datetime
    updated_at: datetime


# --- Product Image ---

class ProductImageCreate(BaseSchema):
    url: str = Field(min_length=1, max_length=500)
    alt_text: str | None = Field(default=None, max_length=255)
    variant_id: UUID | None = None
    sort_order: int = Field(default=0, ge=0)
    is_primary: bool = False


class ProductImageResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    product_id: UUID
    variant_id: UUID | None
    url: str
    alt_text: str | None
    sort_order: int
    is_primary: bool


# --- Product Variant ---

class ProductVariantCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=255)
    sku: str = Field(min_length=1, max_length=100)
    barcode: str | None = Field(default=None, max_length=100)
    price: Decimal = Field(default=Decimal("0"), ge=0)
    compare_at_price: Decimal | None = Field(default=None, ge=0)
    cost_price: Decimal | None = Field(default=None, ge=0)
    weight: Decimal | None = Field(default=None, ge=0)
    is_default: bool = False
    sort_order: int = Field(default=0, ge=0)
    attribute_value_ids: list[UUID] = []


class ProductVariantUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    barcode: str | None = Field(default=None, max_length=100)
    price: Decimal | None = Field(default=None, ge=0)
    compare_at_price: Decimal | None = Field(default=None, ge=0)
    cost_price: Decimal | None = Field(default=None, ge=0)
    weight: Decimal | None = Field(default=None, ge=0)
    is_default: bool | None = None
    sort_order: int | None = Field(default=None, ge=0)
    attribute_value_ids: list[UUID] | None = None


class ProductVariantResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    product_id: UUID
    name: str
    sku: str
    barcode: str | None
    price: Decimal
    compare_at_price: Decimal | None
    cost_price: Decimal | None
    weight: Decimal | None
    is_default: bool
    sort_order: int
    attribute_values: list[AttributeValueResponse] = []


# --- Product ---

class ProductCreate(BaseSchema):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=150, pattern=r"^[a-z0-9-]+$")
    sku: str = Field(min_length=1, max_length=100)
    barcode: str | None = Field(default=None, max_length=100)
    description: str | None = None
    short_description: str | None = Field(default=None, max_length=500)
    product_type: ProductType = ProductType.SIMPLE
    store_id: UUID | None = None
    category_id: UUID | None = None
    brand_id: UUID | None = None
    base_price: Decimal = Field(default=Decimal("0"), ge=0)
    compare_at_price: Decimal | None = Field(default=None, ge=0)
    cost_price: Decimal | None = Field(default=None, ge=0)
    track_inventory: bool = True
    is_taxable: bool = True
    weight: Decimal | None = Field(default=None, ge=0)
    weight_unit: str = Field(default="kg", max_length=10)
    attribute_ids: list[UUID] = []
    variants: list[ProductVariantCreate] = []
    images: list[ProductImageCreate] = []


class ProductUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    barcode: str | None = Field(default=None, max_length=100)
    description: str | None = None
    short_description: str | None = Field(default=None, max_length=500)
    status: ProductStatus | None = None
    store_id: UUID | None = None
    category_id: UUID | None = None
    brand_id: UUID | None = None
    base_price: Decimal | None = Field(default=None, ge=0)
    compare_at_price: Decimal | None = Field(default=None, ge=0)
    cost_price: Decimal | None = Field(default=None, ge=0)
    track_inventory: bool | None = None
    is_taxable: bool | None = None
    weight: Decimal | None = Field(default=None, ge=0)
    weight_unit: str | None = Field(default=None, max_length=10)
    attribute_ids: list[UUID] | None = None


class ProductResponse(BaseSchema):
    id: UUID
    tenant_id: UUID
    store_id: UUID | None
    category_id: UUID | None
    brand_id: UUID | None
    name: str
    slug: str
    sku: str
    barcode: str | None
    description: str | None
    short_description: str | None
    product_type: str
    status: str
    base_price: Decimal
    compare_at_price: Decimal | None
    cost_price: Decimal | None
    track_inventory: bool
    is_taxable: bool
    weight: Decimal | None
    weight_unit: str
    created_at: datetime
    updated_at: datetime


class ProductDetailResponse(ProductResponse):
    variants: list[ProductVariantResponse] = []
    images: list[ProductImageResponse] = []
    attributes: list[AttributeResponse] = []
    category: CategoryResponse | None = None
    brand: BrandResponse | None = None


CategoryTreeResponse.model_rebuild()
