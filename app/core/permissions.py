from collections.abc import Callable
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db import get_db
from apps.accounts.models import User
from apps.billing.services import BillingService


def require_feature(feature_key: str) -> Callable:
    async def dependency(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> UUID:
        service = BillingService(db)
        await service.require_entitlement(user_id=current_user.id, feature_key=feature_key)
        return current_user.id

    return dependency
