from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db import get_db
from apps.accounts.models import User
from apps.billing.schemas import EntitlementsMeRead
from apps.billing.services import BillingService

router = APIRouter(prefix="/entitlements", tags=["entitlements"])


@router.get("/me", response_model=EntitlementsMeRead)
async def get_my_entitlements(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EntitlementsMeRead:
    service = BillingService(db)
    return await service.get_entitlements_me(user_id=current_user.id)
