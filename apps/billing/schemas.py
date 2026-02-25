from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from apps.billing.models import (
    BillingEventStatus,
    BillingProvider,
    EntitlementWindow,
    PlanInterval,
    SubscriptionStatus,
)


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    price_cents: int
    currency: str
    billing_interval: PlanInterval
    provider: BillingProvider
    stripe_price_id: str | None
    stripe_product_id: str | None
    is_free: bool
    is_active: bool
    created_at: datetime


class SubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    plan_id: UUID
    status: SubscriptionStatus
    started_at: datetime
    current_period_start: datetime
    current_period_end: datetime
    canceled_at: datetime | None
    provider: BillingProvider
    provider_customer_id: str | None
    provider_subscription_id: str | None
    cancel_at_period_end: bool
    created_at: datetime


class EntitlementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    plan_id: UUID | None
    subscription_id: UUID | None
    feature_key: str
    limit_value: int | None
    usage_window: EntitlementWindow
    is_enabled: bool
    valid_from: datetime
    valid_to: datetime | None
    created_at: datetime


class UsageCounterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    feature_key: str
    window_start: datetime
    window_end: datetime
    used_count: int
    created_at: datetime


class BillingEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: BillingProvider
    provider_event_id: str
    event_type: str
    status: BillingEventStatus
    payload_json: dict
    processed_at: datetime | None
    last_error: str | None
    created_at: datetime


class CheckoutSessionCreate(BaseModel):
    plan_code: str = Field(min_length=1, max_length=32)
    success_url: str = Field(min_length=8, max_length=2048)
    cancel_url: str = Field(min_length=8, max_length=2048)


class CheckoutSessionRead(BaseModel):
    checkout_session_id: str
    checkout_url: str


class StripeWebhookAck(BaseModel):
    received: bool = True
    idempotent_replay: bool = False


class EntitlementsMeRead(BaseModel):
    plan: PlanRead | None
    subscription: SubscriptionRead | None
    entitlements: list[EntitlementRead]
    usage_counters: list[UsageCounterRead]
