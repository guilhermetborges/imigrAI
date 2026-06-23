from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db import get_db
from apps.accounts.models import User
from apps.billing.schemas import EntitlementsMeRead
from apps.billing.services import BillingService

router = APIRouter(prefix="/entitlements", tags=["entitlements"])
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/me")
async def get_my_entitlements(
    db: DbSession,
    current_user: CurrentUser,
) -> EntitlementsMeRead:
    service = BillingService(db)
    return await service.get_entitlements_me(user_id=current_user.id)
