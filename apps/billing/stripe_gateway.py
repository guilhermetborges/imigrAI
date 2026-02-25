from typing import Any


class StripeGatewayError(RuntimeError):
    pass


class StripeSignatureError(StripeGatewayError):
    pass


class StripeGateway:
    provider_name = "stripe"

    def __init__(self, *, api_key: str | None, webhook_secret: str | None) -> None:
        if not api_key:
            raise StripeGatewayError("STRIPE_SECRET_KEY is required for Stripe integration")
        try:
            import stripe
        except ImportError as exc:  # pragma: no cover - runtime packaging issue
            raise StripeGatewayError("stripe package is required") from exc

        stripe.api_key = api_key
        self._stripe = stripe
        self._webhook_secret = webhook_secret

    def create_checkout_session(
        self,
        *,
        customer_email: str,
        success_url: str,
        cancel_url: str,
        price_id: str,
        client_reference_id: str,
        metadata: dict[str, str],
    ) -> dict[str, str]:
        try:
            session = self._stripe.checkout.Session.create(
                mode="subscription",
                customer_email=customer_email,
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=client_reference_id,
                metadata=metadata,
            )
        except Exception as exc:
            raise StripeGatewayError(f"stripe checkout session create failed: {exc}") from exc

        return {
            "id": str(session.id),
            "url": str(session.url),
        }

    def verify_and_parse_webhook(self, *, payload: bytes, signature: str | None) -> dict[str, Any]:
        if not self._webhook_secret:
            raise StripeGatewayError("STRIPE_WEBHOOK_SECRET is required for webhook validation")
        if not signature:
            raise StripeSignatureError("Missing Stripe-Signature header")

        try:
            event = self._stripe.Webhook.construct_event(payload, signature, self._webhook_secret)
        except self._stripe.error.SignatureVerificationError as exc:
            raise StripeSignatureError("Invalid Stripe webhook signature") from exc
        except Exception as exc:
            raise StripeGatewayError(f"stripe webhook parse failed: {exc}") from exc

        if hasattr(event, "to_dict_recursive"):
            return event.to_dict_recursive()
        return dict(event)

    def retrieve_subscription(self, subscription_id: str) -> dict[str, Any]:
        try:
            subscription = self._stripe.Subscription.retrieve(subscription_id)
        except Exception as exc:
            raise StripeGatewayError(f"stripe subscription retrieve failed: {exc}") from exc

        if hasattr(subscription, "to_dict_recursive"):
            return subscription.to_dict_recursive()
        return dict(subscription)
