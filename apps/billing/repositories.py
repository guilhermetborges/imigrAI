from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from apps.billing.models import (
    BillingEvent,
    BillingEventStatus,
    BillingProvider,
    Entitlement,
    EntitlementWindow,
    Plan,
    Subscription,
    SubscriptionStatus,
    UsageCounter,
)


class BillingRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_plan_by_code(self, code: str) -> Plan | None:
        query = select(Plan).where(Plan.code == code, Plan.is_active.is_(True))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_plan_by_stripe_price_id(self, stripe_price_id: str) -> Plan | None:
        query = select(Plan).where(
            Plan.stripe_price_id == stripe_price_id, Plan.is_active.is_(True)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_or_create_plan(
        self,
        *,
        code: str,
        name: str,
        description: str | None,
        price_cents: int,
        currency: str,
        billing_interval,
        provider: BillingProvider = BillingProvider.stripe,
        stripe_price_id: str | None = None,
        stripe_product_id: str | None = None,
        is_free: bool,
    ) -> Plan:
        existing = await self.get_plan_by_code(code)
        if existing is not None:
            existing.name = name
            existing.description = description
            existing.price_cents = price_cents
            existing.currency = currency
            existing.billing_interval = billing_interval
            existing.provider = provider
            existing.stripe_price_id = stripe_price_id
            existing.stripe_product_id = stripe_product_id
            existing.is_free = is_free
            existing.is_active = True
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        plan = Plan(
            code=code,
            name=name,
            description=description,
            price_cents=price_cents,
            currency=currency,
            billing_interval=billing_interval,
            provider=provider,
            stripe_price_id=stripe_price_id,
            stripe_product_id=stripe_product_id,
            is_free=is_free,
            is_active=True,
        )
        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)
        return plan

    async def get_subscription_by_provider_id(
        self,
        *,
        provider: BillingProvider,
        provider_subscription_id: str,
    ) -> Subscription | None:
        query = select(Subscription).where(
            Subscription.provider == provider,
            Subscription.provider_subscription_id == provider_subscription_id,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_active_subscription_for_user(self, user_id: UUID) -> Subscription | None:
        query = (
            select(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.status.in_(
                    [
                        SubscriptionStatus.active,
                        SubscriptionStatus.trialing,
                        SubscriptionStatus.past_due,
                    ]
                ),
            )
            .options(joinedload(Subscription.plan))
            .order_by(Subscription.current_period_end.desc(), Subscription.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_active_entitlements(
        self,
        *,
        user_id: UUID,
        at: datetime | None = None,
    ) -> list[Entitlement]:
        at_utc = (at or datetime.now(UTC)).astimezone(UTC)
        query = (
            select(Entitlement)
            .where(
                Entitlement.user_id == user_id,
                Entitlement.is_enabled.is_(True),
                Entitlement.valid_from <= at_utc,
                or_(Entitlement.valid_to.is_(None), Entitlement.valid_to > at_utc),
            )
            .order_by(Entitlement.feature_key.asc(), Entitlement.valid_from.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_active_entitlement(
        self,
        *,
        user_id: UUID,
        feature_key: str,
        at: datetime | None = None,
    ) -> Entitlement | None:
        at_utc = (at or datetime.now(UTC)).astimezone(UTC)
        query = (
            select(Entitlement)
            .where(
                Entitlement.user_id == user_id,
                Entitlement.feature_key == feature_key,
                Entitlement.is_enabled.is_(True),
                Entitlement.valid_from <= at_utc,
                or_(Entitlement.valid_to.is_(None), Entitlement.valid_to > at_utc),
            )
            .order_by(Entitlement.valid_from.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def deactivate_active_entitlements(self, *, user_id: UUID, at: datetime) -> None:
        active = await self.list_active_entitlements(user_id=user_id, at=at)
        for entitlement in active:
            entitlement.valid_to = at
        await self.db.flush()

    async def create_entitlement(
        self,
        *,
        user_id: UUID,
        feature_key: str,
        limit_value: int | None,
        usage_window: EntitlementWindow,
        valid_from: datetime,
        valid_to: datetime | None,
        is_enabled: bool,
        plan_id: UUID | None = None,
        subscription_id: UUID | None = None,
    ) -> Entitlement:
        entitlement = Entitlement(
            user_id=user_id,
            plan_id=plan_id,
            subscription_id=subscription_id,
            feature_key=feature_key,
            limit_value=limit_value,
            usage_window=usage_window,
            is_enabled=is_enabled,
            valid_from=valid_from,
            valid_to=valid_to,
        )
        self.db.add(entitlement)
        await self.db.flush()
        return entitlement

    async def upsert_subscription(
        self,
        *,
        user_id: UUID,
        plan_id: UUID,
        provider: BillingProvider,
        provider_customer_id: str | None,
        provider_subscription_id: str | None,
        status: SubscriptionStatus,
        started_at: datetime,
        current_period_start: datetime,
        current_period_end: datetime,
        cancel_at_period_end: bool,
        canceled_at: datetime | None,
    ) -> Subscription:
        subscription: Subscription | None = None
        if provider_subscription_id:
            subscription = await self.get_subscription_by_provider_id(
                provider=provider,
                provider_subscription_id=provider_subscription_id,
            )

        if subscription is None:
            subscription = Subscription(
                user_id=user_id,
                plan_id=plan_id,
                provider=provider,
                provider_customer_id=provider_customer_id,
                provider_subscription_id=provider_subscription_id,
                status=status,
                started_at=started_at,
                current_period_start=current_period_start,
                current_period_end=current_period_end,
                cancel_at_period_end=cancel_at_period_end,
                canceled_at=canceled_at,
            )
            self.db.add(subscription)
        else:
            subscription.user_id = user_id
            subscription.plan_id = plan_id
            subscription.provider = provider
            subscription.provider_customer_id = provider_customer_id
            subscription.provider_subscription_id = provider_subscription_id
            subscription.status = status
            subscription.started_at = started_at
            subscription.current_period_start = current_period_start
            subscription.current_period_end = current_period_end
            subscription.cancel_at_period_end = cancel_at_period_end
            subscription.canceled_at = canceled_at

        await self.db.flush()
        return subscription

    async def get_or_create_usage_counter(
        self,
        *,
        user_id: UUID,
        feature_key: str,
        window_start: datetime,
        window_end: datetime,
    ) -> UsageCounter:
        query = select(UsageCounter).where(
            UsageCounter.user_id == user_id,
            UsageCounter.feature_key == feature_key,
            UsageCounter.window_start == window_start,
        )
        result = await self.db.execute(query)
        counter = result.scalar_one_or_none()
        if counter is not None:
            return counter

        counter = UsageCounter(
            user_id=user_id,
            feature_key=feature_key,
            window_start=window_start,
            window_end=window_end,
            used_count=0,
        )
        self.db.add(counter)
        await self.db.flush()
        return counter

    async def list_current_usage_counters(
        self, *, user_id: UUID, at: datetime
    ) -> list[UsageCounter]:
        query = (
            select(UsageCounter)
            .where(
                UsageCounter.user_id == user_id,
                UsageCounter.window_start <= at,
                UsageCounter.window_end > at,
            )
            .order_by(UsageCounter.feature_key.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_billing_event(
        self,
        *,
        provider: BillingProvider,
        provider_event_id: str,
    ) -> BillingEvent | None:
        query = select(BillingEvent).where(
            BillingEvent.provider == provider,
            BillingEvent.provider_event_id == provider_event_id,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_billing_event(
        self,
        *,
        provider: BillingProvider,
        provider_event_id: str,
        event_type: str,
        payload_json: dict,
    ) -> BillingEvent:
        event = BillingEvent(
            provider=provider,
            provider_event_id=provider_event_id,
            event_type=event_type,
            payload_json=payload_json,
            status=BillingEventStatus.received,
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def mark_billing_event_processed(
        self,
        event: BillingEvent,
        *,
        status_value: BillingEventStatus = BillingEventStatus.processed,
    ) -> None:
        event.status = status_value
        event.processed_at = datetime.now(UTC)
        event.last_error = None
        await self.db.flush()

    async def mark_billing_event_failed(self, event: BillingEvent, *, error_message: str) -> None:
        event.status = BillingEventStatus.failed
        event.last_error = error_message
        event.processed_at = datetime.now(UTC)
        await self.db.flush()

    async def commit(self) -> None:
        await self.db.commit()

    async def rollback(self) -> None:
        await self.db.rollback()
