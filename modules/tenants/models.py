from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import (
    BaseModel,
    BillingCycle,
    SubscriptionStatus,
    TenantStatus,
)
from app.shared.types import GUID


class Tenant(BaseModel):
    __tablename__ = "tenants"
    __table_args__ = (UniqueConstraint("slug", name="uq_tenants_slug"),)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=TenantStatus.PENDING.value
    )
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    settings: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="tenant", lazy="selectin"
    )


class SubscriptionPlan(BaseModel):
    __tablename__ = "subscription_plans"
    __table_args__ = (UniqueConstraint("code", name="uq_subscription_plans_code"),)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    monthly_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    yearly_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    trial_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    features: Mapped[list["PlanFeature"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", lazy="selectin"
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="plan")


class Feature(BaseModel):
    __tablename__ = "features"
    __table_args__ = (UniqueConstraint("code", name="uq_features_code"),)

    code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    module: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    plan_features: Mapped[list["PlanFeature"]] = relationship(back_populates="feature")


class PlanFeature(BaseModel):
    __tablename__ = "plan_features"
    __table_args__ = (
        UniqueConstraint("plan_id", "feature_id", name="uq_plan_features"),
    )

    plan_id: Mapped[UUID] = mapped_column(
        GUID(),
        ForeignKey("subscription_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    feature_id: Mapped[UUID] = mapped_column(
        GUID(),
        ForeignKey("features.id", ondelete="CASCADE"),
        nullable=False,
    )
    limit_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    plan: Mapped["SubscriptionPlan"] = relationship(back_populates="features")
    feature: Mapped["Feature"] = relationship(back_populates="plan_features", lazy="selectin")


class Subscription(BaseModel):
    __tablename__ = "subscriptions"

    tenant_id: Mapped[UUID] = mapped_column(GUID(), nullable=False, index=True)
    plan_id: Mapped[UUID] = mapped_column(
        GUID(),
        ForeignKey("subscription_plans.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SubscriptionStatus.TRIAL.value
    )
    billing_cycle: Mapped[str] = mapped_column(
        String(20), nullable=False, default=BillingCycle.MONTHLY.value
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    current_period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    trial_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    grace_period_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    suspended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="subscriptions")
    plan: Mapped["SubscriptionPlan"] = relationship(
        back_populates="subscriptions", lazy="selectin"
    )
