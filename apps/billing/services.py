from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.metrics import increment_free_to_pro_conversion
from apps.accounts.models import User
from apps.billing.models import (
    BillingEventStatus,
    BillingProvider,
    Entitlement,
    EntitlementWindow,
    Plan,
    PlanInterval,
    SubscriptionStatus,
)
from apps.billing.repositories import BillingRepository
from apps.billing.schemas import (
    CheckoutSessionCreate,
    CheckoutSessionRead,
    EntitlementRead,
    EntitlementsMeRead,
    PlanRead,
    StripeWebhookAck,
    SubscriptionRead,
    UsageCounterRead,
)
from apps.billing.stripe_gateway import StripeGateway, StripeGatewayError, StripeSignatureError


@dataclass(frozen=True)
class EntitlementSpec:
    feature_key: str
    limit_value: int | None
    usage_window: EntitlementWindow
    is_enabled: bool


@dataclass(frozen=True)
class AssessmentQuotaDecision:
    priority: bool


class BillingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = BillingRepository(db)
        self.settings = get_settings()

    async def require_entitlement(self, *, user_id: UUID, feature_key: str) -> Entitlement:
        await self.ensure_user_access_baseline(user_id)
        entitlement = await self.repo.get_active_entitlement(
            user_id=user_id, feature_key=feature_key
        )
        if entitlement is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{feature_key}' requires active entitlement",
            )
        return entitlement

    async def consume_assessment_quota(self, *, user_id: UUID) -> AssessmentQuotaDecision:
        await self.ensure_user_access_baseline(user_id)
        entitlement = await self.repo.get_active_entitlement(
            user_id=user_id,
            feature_key=self.settings.assessment_feature_key,
        )
        if entitlement is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No active entitlement for assessments",
            )

        if entitlement.limit_value is not None:
            now = datetime.now(UTC)
            window_start, window_end = self._current_month_window(now)
            counter = await self.repo.get_or_create_usage_counter(
                user_id=user_id,
                feature_key=self.settings.assessment_feature_key,
                window_start=window_start,
                window_end=window_end,
            )
            if counter.used_count >= entitlement.limit_value:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        "Monthly assessment quota reached for free plan "
                        f"({entitlement.limit_value}/{entitlement.limit_value})"
                    ),
                )
            counter.used_count += 1

        priority = await self.repo.get_active_entitlement(
            user_id=user_id,
            feature_key=self.settings.processing_priority_feature_key,
        )
        await self.repo.commit()
        return AssessmentQuotaDecision(priority=priority is not None)

    async def has_priority_processing(self, *, user_id: UUID) -> bool:
        await self.ensure_user_access_baseline(user_id)
        priority = await self.repo.get_active_entitlement(
            user_id=user_id,
            feature_key=self.settings.processing_priority_feature_key,
        )
        return priority is not None

    async def get_entitlements_me(self, *, user_id: UUID) -> EntitlementsMeRead:
        await self.ensure_user_access_baseline(user_id)
        now = datetime.now(UTC)
        entitlements = await self.repo.list_active_entitlements(user_id=user_id, at=now)
        usage = await self.repo.list_current_usage_counters(user_id=user_id, at=now)
        subscription = await self.repo.get_active_subscription_for_user(user_id)
        plan = (
            subscription.plan
            if subscription is not None
            else await self.repo.get_plan_by_code(self.settings.free_plan_code)
        )
        return EntitlementsMeRead(
            plan=PlanRead.model_validate(plan) if plan else None,
            subscription=SubscriptionRead.model_validate(subscription) if subscription else None,
            entitlements=[EntitlementRead.model_validate(e) for e in entitlements],
            usage_counters=[UsageCounterRead.model_validate(c) for c in usage],
        )

    async def create_checkout_session(
        self,
        *,
        user_id: UUID,
        user_email: str,
        payload: CheckoutSessionCreate,
    ) -> CheckoutSessionRead:
        await self._ensure_default_plans()
        plan = await self.repo.get_plan_by_code(payload.plan_code)
        if plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
        if plan.is_free:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Checkout not applicable for free plan",
            )
        if not plan.stripe_price_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Plan is missing Stripe price id",
            )

        gateway = self._build_stripe_gateway()
        session = gateway.create_checkout_session(
            customer_email=user_email,
            success_url=payload.success_url,
            cancel_url=payload.cancel_url,
            price_id=plan.stripe_price_id,
            client_reference_id=str(user_id),
            metadata={"user_id": str(user_id), "plan_code": plan.code},
        )
        return CheckoutSessionRead(
            checkout_session_id=session["id"],
            checkout_url=session["url"],
        )

    async def process_stripe_webhook(
        self,
        *,
        payload: bytes,
        signature: str | None,
    ) -> StripeWebhookAck:
        await self._ensure_default_plans()
        gateway = self._build_stripe_gateway()
        try:
            event = gateway.verify_and_parse_webhook(payload=payload, signature=signature)
        except StripeSignatureError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        except StripeGatewayError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
            ) from exc

        event_id = str(event.get("id", ""))
        event_type = str(event.get("type", ""))
        if not event_id or not event_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Stripe event payload"
            )

        existing = await self.repo.get_billing_event(
            provider=BillingProvider.stripe,
            provider_event_id=event_id,
        )
        if existing and existing.status in {
            BillingEventStatus.processed,
            BillingEventStatus.ignored,
        }:
            return StripeWebhookAck(received=True, idempotent_replay=True)

        billing_event = existing or await self.repo.create_billing_event(
            provider=BillingProvider.stripe,
            provider_event_id=event_id,
            event_type=event_type,
            payload_json=event,
        )

        try:
            handled = await self._handle_stripe_event(event=event, gateway=gateway)
            await self.repo.mark_billing_event_processed(
                billing_event,
                status_value=(
                    BillingEventStatus.processed if handled else BillingEventStatus.ignored
                ),
            )
            await self.repo.commit()
        except Exception as exc:
            await self.repo.mark_billing_event_failed(billing_event, error_message=str(exc))
            await self.repo.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process billing event: {exc}",
            ) from exc

        return StripeWebhookAck(received=True, idempotent_replay=False)

    async def ensure_user_access_baseline(self, user_id: UUID) -> None:
        await self._ensure_default_plans()
        entitlements = await self.repo.list_active_entitlements(user_id=user_id)
        if entitlements:
            return
        free_plan = await self.repo.get_plan_by_code(self.settings.free_plan_code)
        if free_plan is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Free plan not configured",
            )
        await self._apply_plan_entitlements(user_id=user_id, plan=free_plan, subscription_id=None)
        await self.repo.commit()

    async def _handle_stripe_event(self, *, event: dict, gateway: StripeGateway) -> bool:
        event_type = str(event["type"])
        data_object = event.get("data", {}).get("object", {})

        if event_type == "checkout.session.completed":
            subscription_id = data_object.get("subscription")
            if not subscription_id:
                return False
            user_id_hint = data_object.get("client_reference_id") or data_object.get(
                "metadata", {}
            ).get("user_id")
            customer_id = data_object.get("customer")
            await self._sync_subscription_from_provider(
                gateway=gateway,
                provider_subscription_id=str(subscription_id),
                user_id_hint=str(user_id_hint) if user_id_hint else None,
                customer_id_hint=str(customer_id) if customer_id else None,
            )
            return True

        if event_type == "invoice.paid":
            subscription_id = data_object.get("subscription")
            if not subscription_id:
                return False
            await self._sync_subscription_from_provider(
                gateway=gateway,
                provider_subscription_id=str(subscription_id),
                user_id_hint=None,
                customer_id_hint=None,
            )
            return True

        if event_type in {"customer.subscription.updated", "customer.subscription.deleted"}:
            await self._sync_subscription_object(subscription_object=data_object)
            return True

        return False

    async def _sync_subscription_from_provider(
        self,
        *,
        gateway: StripeGateway,
        provider_subscription_id: str,
        user_id_hint: str | None,
        customer_id_hint: str | None,
    ) -> None:
        subscription_object = gateway.retrieve_subscription(provider_subscription_id)
        if customer_id_hint and not subscription_object.get("customer"):
            subscription_object["customer"] = customer_id_hint
        if (
            user_id_hint
            and "metadata" in subscription_object
            and not subscription_object["metadata"].get("user_id")
        ):
            subscription_object["metadata"]["user_id"] = user_id_hint
        await self._sync_subscription_object(
            subscription_object=subscription_object, user_id_hint=user_id_hint
        )

    async def _sync_subscription_object(
        self,
        *,
        subscription_object: dict,
        user_id_hint: str | None = None,
    ) -> None:
        provider_subscription_id = str(subscription_object.get("id", ""))
        if not provider_subscription_id:
            raise ValueError("Stripe subscription payload missing id")

        plan = await self._resolve_plan_from_subscription_payload(subscription_object)
        status_value = self._map_subscription_status(str(subscription_object.get("status", "")))

        existing = await self.repo.get_subscription_by_provider_id(
            provider=BillingProvider.stripe,
            provider_subscription_id=provider_subscription_id,
        )
        should_count_conversion = plan.code == self.settings.pro_plan_code and (
            existing is None or existing.plan_id != plan.id
        )
        if existing is not None:
            user_id = existing.user_id
        else:
            metadata = subscription_object.get("metadata", {}) or {}
            raw_user_id = user_id_hint or metadata.get("user_id")
            if not raw_user_id:
                raise ValueError(
                    "Cannot resolve user for subscription event without metadata.user_id"
                )
            user_id = UUID(str(raw_user_id))

        now = datetime.now(UTC)
        started_at = self._from_unix(subscription_object.get("start_date")) or now
        current_period_start = (
            self._from_unix(subscription_object.get("current_period_start")) or now
        )
        current_period_end = self._from_unix(subscription_object.get("current_period_end")) or now
        canceled_at = self._from_unix(subscription_object.get("canceled_at"))
        cancel_at_period_end = bool(subscription_object.get("cancel_at_period_end", False))
        customer_id = subscription_object.get("customer")

        subscription = await self.repo.upsert_subscription(
            user_id=user_id,
            plan_id=plan.id,
            provider=BillingProvider.stripe,
            provider_customer_id=str(customer_id) if customer_id else None,
            provider_subscription_id=provider_subscription_id,
            status=status_value,
            started_at=started_at,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            cancel_at_period_end=cancel_at_period_end,
            canceled_at=canceled_at,
        )
        if should_count_conversion:
            increment_free_to_pro_conversion()

        if status_value in {
            SubscriptionStatus.active,
            SubscriptionStatus.trialing,
            SubscriptionStatus.past_due,
        }:
            await self._apply_plan_entitlements(
                user_id=user_id,
                plan=plan,
                subscription_id=subscription.id,
            )
        else:
            free_plan = await self.repo.get_plan_by_code(self.settings.free_plan_code)
            if free_plan is None:
                raise ValueError("Free plan not configured")
            await self._apply_plan_entitlements(
                user_id=user_id,
                plan=free_plan,
                subscription_id=subscription.id,
            )

    async def _resolve_plan_from_subscription_payload(self, subscription_object: dict) -> Plan:
        items = subscription_object.get("items", {}).get("data", [])
        price_id = None
        if items and isinstance(items, list):
            first = items[0]
            price_id = (first or {}).get("price", {}).get("id")

        if not price_id:
            pro_plan = await self.repo.get_plan_by_code(self.settings.pro_plan_code)
            if pro_plan is None:
                raise ValueError("Pro plan not configured")
            return pro_plan

        plan = await self.repo.get_plan_by_stripe_price_id(str(price_id))
        if plan is not None:
            return plan

        if self.settings.stripe_pro_price_id and str(price_id) == self.settings.stripe_pro_price_id:
            pro_plan = await self.repo.get_plan_by_code(self.settings.pro_plan_code)
            if pro_plan is None:
                raise ValueError("Pro plan not configured")
            return pro_plan

        raise ValueError(f"Unknown Stripe price id: {price_id}")

    async def _ensure_default_plans(self) -> None:
        await self.repo.get_or_create_plan(
            code=self.settings.free_plan_code,
            name=self.settings.free_plan_name,
            description="Free tier",
            price_cents=0,
            currency="BRL",
            billing_interval=PlanInterval.month,
            provider=BillingProvider.stripe,
            stripe_price_id=None,
            stripe_product_id=None,
            is_free=True,
        )
        await self.repo.get_or_create_plan(
            code=self.settings.pro_plan_code,
            name=self.settings.pro_plan_name,
            description="Pro tier",
            price_cents=0,
            currency="BRL",
            billing_interval=PlanInterval.month,
            provider=BillingProvider.stripe,
            stripe_price_id=self.settings.stripe_pro_price_id,
            stripe_product_id=None,
            is_free=False,
        )

    async def _apply_plan_entitlements(
        self,
        *,
        user_id: UUID,
        plan: Plan,
        subscription_id: UUID | None,
    ) -> None:
        now = datetime.now(UTC)
        await self.repo.deactivate_active_entitlements(user_id=user_id, at=now)
        specs = self._entitlements_for_plan(plan.code)
        for spec in specs:
            await self.repo.create_entitlement(
                user_id=user_id,
                plan_id=plan.id,
                subscription_id=subscription_id,
                feature_key=spec.feature_key,
                limit_value=spec.limit_value,
                usage_window=spec.usage_window,
                is_enabled=spec.is_enabled,
                valid_from=now,
                valid_to=None,
            )

    def _entitlements_for_plan(self, plan_code: str) -> list[EntitlementSpec]:
        if plan_code == self.settings.pro_plan_code:
            return [
                EntitlementSpec(
                    feature_key=self.settings.assessment_feature_key,
                    limit_value=None,
                    usage_window=EntitlementWindow.monthly,
                    is_enabled=True,
                ),
                EntitlementSpec(
                    feature_key=self.settings.pro_roadmap_feature_key,
                    limit_value=None,
                    usage_window=EntitlementWindow.lifetime,
                    is_enabled=True,
                ),
                EntitlementSpec(
                    feature_key=self.settings.history_extended_feature_key,
                    limit_value=None,
                    usage_window=EntitlementWindow.lifetime,
                    is_enabled=True,
                ),
                EntitlementSpec(
                    feature_key=self.settings.country_comparison_feature_key,
                    limit_value=None,
                    usage_window=EntitlementWindow.lifetime,
                    is_enabled=True,
                ),
                EntitlementSpec(
                    feature_key=self.settings.processing_priority_feature_key,
                    limit_value=None,
                    usage_window=EntitlementWindow.lifetime,
                    is_enabled=True,
                ),
            ]

        return [
            EntitlementSpec(
                feature_key=self.settings.assessment_feature_key,
                limit_value=self.settings.free_assessment_monthly_limit,
                usage_window=EntitlementWindow.monthly,
                is_enabled=True,
            )
        ]

    def _current_month_window(self, now: datetime) -> tuple[datetime, datetime]:
        start = datetime(year=now.year, month=now.month, day=1, tzinfo=UTC)
        if now.month == 12:
            end = datetime(year=now.year + 1, month=1, day=1, tzinfo=UTC)
        else:
            end = datetime(year=now.year, month=now.month + 1, day=1, tzinfo=UTC)
        return start, end

    def _map_subscription_status(self, raw_status: str) -> SubscriptionStatus:
        normalized = raw_status.strip().lower()
        if normalized == "active":
            return SubscriptionStatus.active
        if normalized == "trialing":
            return SubscriptionStatus.trialing
        if normalized in {"past_due", "unpaid"}:
            return SubscriptionStatus.past_due
        if normalized in {"canceled", "cancelled"}:
            return SubscriptionStatus.canceled
        return SubscriptionStatus.expired

    def _from_unix(self, value: int | None) -> datetime | None:
        if value is None:
            return None
        return datetime.fromtimestamp(int(value), tz=UTC)

    def _build_stripe_gateway(self) -> StripeGateway:
        return StripeGateway(
            api_key=self.settings.stripe_secret_key,
            webhook_secret=self.settings.stripe_webhook_secret,
        )


async def get_user_email(db: AsyncSession, user_id: UUID) -> str:
    result = await db.execute(select(User.email).where(User.id == user_id))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return str(email)
