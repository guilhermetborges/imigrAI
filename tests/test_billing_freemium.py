from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from apps.accounts.models import User
from apps.billing.models import BillingEvent, Entitlement, Plan, Subscription, UsageCounter
from apps.billing.services import BillingService


class FakeStripeGateway:
    def __init__(self, *, events: list[dict], subscriptions: dict[str, dict]) -> None:
        self._events = events
        self._subscriptions = subscriptions

    def verify_and_parse_webhook(self, *, payload: bytes, signature: str | None) -> dict:
        assert signature
        assert payload is not None
        if not self._events:
            raise RuntimeError("No fake events queued")
        return self._events.pop(0)

    def retrieve_subscription(self, subscription_id: str) -> dict:
        return self._subscriptions[subscription_id]

    def create_checkout_session(self, **kwargs) -> dict[str, str]:
        return {"id": "cs_test", "url": "https://stripe.test/checkout/cs_test"}


@pytest.fixture
async def billing_service_with_user():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(
            User.metadata.create_all,
            tables=[
                User.__table__,
                Plan.__table__,
                Subscription.__table__,
                Entitlement.__table__,
                UsageCounter.__table__,
                BillingEvent.__table__,
            ],
        )

    async with session_factory() as session:
        user = User(email="billing@example.com", password_hash="hashed")
        session.add(user)
        await session.commit()
        await session.refresh(user)

        service = BillingService(session)
        service.settings.stripe_pro_price_id = "price_pro_test"
        yield service, user

    await engine.dispose()


@pytest.mark.asyncio
async def test_upgrade_to_pro_enables_roadmap_and_is_idempotent(billing_service_with_user) -> None:
    service, user = billing_service_with_user
    await service.ensure_user_access_baseline(user.id)

    with pytest.raises(HTTPException) as exc:
        await service.require_entitlement(
            user_id=user.id,
            feature_key=service.settings.pro_roadmap_feature_key,
        )
    assert exc.value.status_code == 403

    subscription_payload = {
        "id": "sub_pro_1",
        "status": "active",
        "start_date": int(datetime(2026, 2, 1, tzinfo=UTC).timestamp()),
        "current_period_start": int(datetime(2026, 2, 1, tzinfo=UTC).timestamp()),
        "current_period_end": int(datetime(2026, 3, 1, tzinfo=UTC).timestamp()),
        "cancel_at_period_end": False,
        "canceled_at": None,
        "customer": "cus_1",
        "metadata": {"user_id": str(user.id)},
        "items": {"data": [{"price": {"id": "price_pro_test"}}]},
    }
    gateway = FakeStripeGateway(
        events=[
            {
                "id": "evt_upgrade_1",
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "cs_1",
                        "subscription": "sub_pro_1",
                        "client_reference_id": str(user.id),
                        "customer": "cus_1",
                        "metadata": {"user_id": str(user.id)},
                    }
                },
            },
            {
                "id": "evt_upgrade_1",
                "type": "checkout.session.completed",
                "data": {
                    "object": {"subscription": "sub_pro_1", "client_reference_id": str(user.id)}
                },
            },
        ],
        subscriptions={"sub_pro_1": subscription_payload},
    )
    service._build_stripe_gateway = lambda: gateway  # type: ignore[method-assign]

    first = await service.process_stripe_webhook(payload=b"{}", signature="sig")
    second = await service.process_stripe_webhook(payload=b"{}", signature="sig")
    assert first.idempotent_replay is False
    assert second.idempotent_replay is True

    entitlement = await service.require_entitlement(
        user_id=user.id,
        feature_key=service.settings.pro_roadmap_feature_key,
    )
    assert entitlement.is_enabled is True

    me = await service.get_entitlements_me(user_id=user.id)
    assert me.subscription is not None
    assert me.subscription.status.value == "active"


@pytest.mark.asyncio
async def test_downgrade_to_free_restores_monthly_quota(billing_service_with_user) -> None:
    service, user = billing_service_with_user
    await service.ensure_user_access_baseline(user.id)

    pro_subscription_payload = {
        "id": "sub_pro_2",
        "status": "active",
        "start_date": int(datetime(2026, 2, 1, tzinfo=UTC).timestamp()),
        "current_period_start": int(datetime(2026, 2, 1, tzinfo=UTC).timestamp()),
        "current_period_end": int(datetime(2026, 3, 1, tzinfo=UTC).timestamp()),
        "cancel_at_period_end": False,
        "canceled_at": None,
        "customer": "cus_2",
        "metadata": {"user_id": str(user.id)},
        "items": {"data": [{"price": {"id": "price_pro_test"}}]},
    }
    upgraded_gateway = FakeStripeGateway(
        events=[
            {
                "id": "evt_upgrade_2",
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "subscription": "sub_pro_2",
                        "client_reference_id": str(user.id),
                        "customer": "cus_2",
                        "metadata": {"user_id": str(user.id)},
                    }
                },
            }
        ],
        subscriptions={"sub_pro_2": pro_subscription_payload},
    )
    service._build_stripe_gateway = lambda: upgraded_gateway  # type: ignore[method-assign]
    await service.process_stripe_webhook(payload=b"{}", signature="sig")

    downgraded_gateway = FakeStripeGateway(
        events=[
            {
                "id": "evt_downgrade_1",
                "type": "customer.subscription.updated",
                "data": {
                    "object": {
                        **pro_subscription_payload,
                        "status": "incomplete_expired",
                    }
                },
            }
        ],
        subscriptions={"sub_pro_2": pro_subscription_payload},
    )
    service._build_stripe_gateway = lambda: downgraded_gateway  # type: ignore[method-assign]
    await service.process_stripe_webhook(payload=b"{}", signature="sig")

    me = await service.get_entitlements_me(user_id=user.id)
    assert me.subscription is None or me.subscription.status.value in {"expired", "canceled"}
    monthly = [
        e for e in me.entitlements if e.feature_key == service.settings.assessment_feature_key
    ]
    assert monthly
    assert monthly[0].limit_value == service.settings.free_assessment_monthly_limit

    with pytest.raises(HTTPException):
        await service.require_entitlement(
            user_id=user.id,
            feature_key=service.settings.pro_roadmap_feature_key,
        )


@pytest.mark.asyncio
async def test_cancel_event_blocks_roadmap_entitlement(billing_service_with_user) -> None:
    service, user = billing_service_with_user
    await service.ensure_user_access_baseline(user.id)

    pro_subscription_payload = {
        "id": "sub_pro_3",
        "status": "active",
        "start_date": int(datetime(2026, 2, 1, tzinfo=UTC).timestamp()),
        "current_period_start": int(datetime(2026, 2, 1, tzinfo=UTC).timestamp()),
        "current_period_end": int(datetime(2026, 3, 1, tzinfo=UTC).timestamp()),
        "cancel_at_period_end": False,
        "canceled_at": None,
        "customer": "cus_3",
        "metadata": {"user_id": str(user.id)},
        "items": {"data": [{"price": {"id": "price_pro_test"}}]},
    }
    gateway = FakeStripeGateway(
        events=[
            {
                "id": "evt_upgrade_3",
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "subscription": "sub_pro_3",
                        "client_reference_id": str(user.id),
                        "customer": "cus_3",
                        "metadata": {"user_id": str(user.id)},
                    }
                },
            },
            {
                "id": "evt_cancel_3",
                "type": "customer.subscription.deleted",
                "data": {"object": {**pro_subscription_payload, "status": "canceled"}},
            },
        ],
        subscriptions={"sub_pro_3": pro_subscription_payload},
    )
    service._build_stripe_gateway = lambda: gateway  # type: ignore[method-assign]

    await service.process_stripe_webhook(payload=b"{}", signature="sig")
    await service.require_entitlement(
        user_id=user.id,
        feature_key=service.settings.pro_roadmap_feature_key,
    )

    await service.process_stripe_webhook(payload=b"{}", signature="sig")
    with pytest.raises(HTTPException) as exc:
        await service.require_entitlement(
            user_id=user.id,
            feature_key=service.settings.pro_roadmap_feature_key,
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_free_quota_allows_three_assessments_per_month(billing_service_with_user) -> None:
    service, user = billing_service_with_user
    await service.ensure_user_access_baseline(user.id)

    await service.consume_assessment_quota(user_id=user.id)
    await service.consume_assessment_quota(user_id=user.id)
    await service.consume_assessment_quota(user_id=user.id)

    with pytest.raises(HTTPException) as exc:
        await service.consume_assessment_quota(user_id=user.id)
    assert exc.value.status_code == 403
