from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.rate_limit import rate_limit
from app.core.security import get_current_user
from app.db import get_db
from apps.accounts.models import User
from apps.billing.schemas import CheckoutSessionCreate, CheckoutSessionRead, StripeWebhookAck
from apps.billing.services import BillingService

router = APIRouter(prefix="/billing", tags=["billing"])
settings = get_settings()
creation_rate_limiter = rate_limit(
    scope="checkout_create",
    limit=settings.creation_rate_limit_requests,
    window_seconds=settings.creation_rate_limit_window_seconds,
    identity="user_or_ip",
)


@router.post(
    "/checkout-session",
    response_model=CheckoutSessionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(creation_rate_limiter)],
)
async def create_checkout_session(
    payload: CheckoutSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CheckoutSessionRead:
    service = BillingService(db)
    return await service.create_checkout_session(
        user_id=current_user.id,
        user_email=current_user.email,
        payload=payload,
    )


@router.post("/webhook/stripe", response_model=StripeWebhookAck)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> StripeWebhookAck:
    payload = await request.body()
    service = BillingService(db)
    return await service.process_stripe_webhook(payload=payload, signature=stripe_signature)
