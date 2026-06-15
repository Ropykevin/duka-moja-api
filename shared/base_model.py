import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.types import GUID


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        self.deleted_at = datetime.now(UTC)


class TenantScopedMixin:
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        nullable=False,
        index=True,
    )


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )


class BaseModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __abstract__ = True


class TenantScopedModel(BaseModel, TenantScopedMixin):
    __abstract__ = True


class SubscriptionStatus(str, enum.Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    GRACE_PERIOD = "grace_period"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class BillingCycle(str, enum.Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class TenantStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class UserStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class StoreStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CLOSED = "closed"


class BranchStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class ProductStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ProductType(str, enum.Enum):
    SIMPLE = "simple"
    VARIABLE = "variable"


class AttributeDisplayType(str, enum.Enum):
    SELECT = "select"
    SWATCH = "swatch"
    TEXT = "text"


class InventoryMovementSource(str, enum.Enum):
    PURCHASE = "purchase"
    POS_SALE = "pos_sale"
    ONLINE_SALE = "online_sale"
    RETURN = "return"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    ADJUSTMENT = "adjustment"


class StockTransferStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    IN_TRANSIT = "in_transit"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class PurchaseOrderStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    PARTIAL_RECEIVED = "partial_received"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class CustomerStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class CartStatus(str, enum.Enum):
    ACTIVE = "active"
    CONVERTED = "converted"
    ABANDONED = "abandoned"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    PARTIAL = "partial"
    REFUNDED = "refunded"
    FAILED = "failed"


class LoyaltyTier(str, enum.Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class CashRegisterStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class CashSessionStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class SaleStatus(str, enum.Enum):
    DRAFT = "draft"
    COMPLETED = "completed"
    VOIDED = "voided"


class PaymentProviderType(str, enum.Enum):
    CASH = "cash"
    CARD = "card"
    MOBILE_MONEY = "mobile_money"
    BANK_TRANSFER = "bank_transfer"
    ONLINE = "online"


class PaymentTransactionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentReferenceType(str, enum.Enum):
    SALE = "sale"
    ORDER = "order"


class ShippingMethodType(str, enum.Enum):
    FLAT_RATE = "flat_rate"
    FREE = "free"
    PICKUP = "pickup"
    CARRIER = "carrier"


class ShipmentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class CouponDiscountType(str, enum.Enum):
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"


class CouponAppliesTo(str, enum.Enum):
    ALL = "all"
    ONLINE = "online"
    POS = "pos"


class CouponUsageReferenceType(str, enum.Enum):
    ORDER = "order"
    SALE = "sale"


class ReturnStatus(str, enum.Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    RECEIVED = "received"
    REFUNDED = "refunded"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ReturnReferenceType(str, enum.Enum):
    ORDER = "order"
    SALE = "sale"
