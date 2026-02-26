from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db import get_db
from apps.accounts.models import User, UserRole
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


def require_role(*allowed_roles: UserRole) -> Callable:
    allowed = set(allowed_roles)

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User role is not allowed for this resource",
            )
        return current_user

    return dependency


def is_admin(user: User) -> bool:
    return user.role == UserRole.admin
