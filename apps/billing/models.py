import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from apps.common.models import CreatedAtMixin, UUIDPrimaryKeyMixin


class PlanInterval(enum.StrEnum):
    month = "month"
    year = "year"


class SubscriptionStatus(enum.StrEnum):
    trialing = "trialing"
    active = "active"
    past_due = "past_due"
    canceled = "canceled"
    expired = "expired"


class EntitlementWindow(enum.StrEnum):
    daily = "daily"
    monthly = "monthly"
    lifetime = "lifetime"


class BillingProvider(enum.StrEnum):
    stripe = "stripe"


class BillingEventStatus(enum.StrEnum):
    received = "received"
    processed = "processed"
    ignored = "ignored"
    failed = "failed"


class Plan(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "plans"

    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    billing_interval: Mapped[PlanInterval] = mapped_column(
        Enum(PlanInterval, name="plan_interval"),
        nullable=False,
        default=PlanInterval.month,
    )
    provider: Mapped[BillingProvider] = mapped_column(
        Enum(BillingProvider, name="billing_provider"),
        nullable=False,
        default=BillingProvider.stripe,
    )
    stripe_price_id: Mapped[str | None] = mapped_column(String(120), unique=True)
    stripe_product_id: Mapped[str | None] = mapped_column(String(120))
    is_free: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="plan")


class Subscription(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "subscriptions"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider: Mapped[BillingProvider] = mapped_column(
        Enum(BillingProvider, name="billing_provider"),
        nullable=False,
        default=BillingProvider.stripe,
    )
    provider_customer_id: Mapped[str | None] = mapped_column(String(120), index=True)
    provider_subscription_id: Mapped[str | None] = mapped_column(
        String(120),
        unique=True,
        index=True,
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped["User"] = relationship()
    plan: Mapped["Plan"] = relationship(back_populates="subscriptions")
    entitlements: Mapped[list["Entitlement"]] = relationship(back_populates="subscription")


class Entitlement(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "entitlements"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "feature_key",
            "usage_window",
            "valid_from",
            name="uq_entitlements_user_feature_window_from",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("plans.id", ondelete="SET NULL"),
        index=True,
    )
    subscription_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        index=True,
    )
    feature_key: Mapped[str] = mapped_column(String(64), nullable=False)
    limit_value: Mapped[int | None] = mapped_column(Integer)
    usage_window: Mapped[EntitlementWindow] = mapped_column(
        Enum(EntitlementWindow, name="entitlement_window"),
        nullable=False,
        default=EntitlementWindow.monthly,
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship()
    plan: Mapped["Plan | None"] = relationship()
    subscription: Mapped["Subscription | None"] = relationship(back_populates="entitlements")


class UsageCounter(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "usage_counters"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "feature_key",
            "window_start",
            name="uq_usage_counters_user_feature_window_start",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feature_key: Mapped[str] = mapped_column(String(64), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    user: Mapped["User"] = relationship()


class BillingEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "billing_events"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_event_id",
            name="uq_billing_events_provider_event_id",
        ),
    )

    provider: Mapped[BillingProvider] = mapped_column(
        Enum(BillingProvider, name="billing_provider"),
        nullable=False,
        index=True,
    )
    provider_event_id: Mapped[str] = mapped_column(String(120), nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[BillingEventStatus] = mapped_column(
        Enum(BillingEventStatus, name="billing_event_status"),
        nullable=False,
        default=BillingEventStatus.received,
        index=True,
    )
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


if TYPE_CHECKING:
    from apps.accounts.models import User
