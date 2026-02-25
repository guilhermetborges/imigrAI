from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db import get_db
from apps.accounts.models import User
from apps.billing.schemas import CheckoutSessionCreate, CheckoutSessionRead, StripeWebhookAck
from apps.billing.services import BillingService

router = APIRouter(prefix="/billing", tags=["billing"])


@router.post(
    "/checkout-session", response_model=CheckoutSessionRead, status_code=status.HTTP_201_CREATED
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
