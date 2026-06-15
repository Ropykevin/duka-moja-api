import uuid

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BranchStatus, StoreStatus, TenantScopedModel
from app.shared.types import GUID


class Store(TenantScopedModel):
    __tablename__ = "stores"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_stores_tenant_slug"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=StoreStatus.ACTIVE.value
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="KES", nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)

    branches: Mapped[list["Branch"]] = relationship(
        back_populates="store", cascade="all, delete-orphan", lazy="selectin"
    )
    settings: Mapped["StoreSettings | None"] = relationship(
        back_populates="store", cascade="all, delete-orphan", uselist=False, lazy="selectin"
    )


class Branch(TenantScopedModel):
    __tablename__ = "branches"
    __table_args__ = (
        UniqueConstraint("store_id", "code", name="uq_branches_store_code"),
    )

    store_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=BranchStatus.ACTIVE.value
    )
    is_headquarters: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)

    store: Mapped["Store"] = relationship(back_populates="branches")


class StoreSettings(TenantScopedModel):
    __tablename__ = "store_settings"
    __table_args__ = (
        UniqueConstraint("store_id", name="uq_store_settings_store_id"),
    )

    store_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tax_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    tax_inclusive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    default_currency: Mapped[str] = mapped_column(String(3), default="KES", nullable=False)
    receipt_header: Mapped[str | None] = mapped_column(Text, nullable=True)
    receipt_footer: Mapped[str | None] = mapped_column(Text, nullable=True)
    allow_negative_stock: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    date_format: Mapped[str] = mapped_column(String(30), default="%Y-%m-%d", nullable=False)
    time_format: Mapped[str] = mapped_column(String(30), default="%H:%M", nullable=False)
    pos_settings: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    ecommerce_settings: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    inventory_settings: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    notification_settings: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    business_hours: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    store: Mapped["Store"] = relationship(back_populates="settings")
