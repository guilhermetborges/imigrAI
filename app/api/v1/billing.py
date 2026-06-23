from typing import Annotated

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
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
StripeSignatureHeader = Annotated[str | None, Header(alias="Stripe-Signature")]


@router.post(
    "/checkout-session",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(creation_rate_limiter)],
)
async def create_checkout_session(
    payload: CheckoutSessionCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> CheckoutSessionRead:
    service = BillingService(db)
    return await service.create_checkout_session(
        user_id=current_user.id,
        user_email=current_user.email,
        payload=payload,
    )


@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    db: DbSession,
    stripe_signature: StripeSignatureHeader = None,
) -> StripeWebhookAck:
    payload = await request.body()
    service = BillingService(db)
    return await service.process_stripe_webhook(payload=payload, signature=stripe_signature)
