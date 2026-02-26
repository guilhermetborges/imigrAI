from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from apps.accounts.models import UserRole
from apps.accounts.repositories import UserRepository


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = UserRepository(db)
        self.settings = get_settings()

    async def register(self, email: str, password: str):
        existing = await self.repo.get_by_email(email)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        role = (
            UserRole.admin
            if email.lower() in {item.lower() for item in self.settings.admin_emails}
            else UserRole.member
        )
        user = await self.repo.create(
            email=email,
            password_hash=get_password_hash(password),
            role=role,
        )
        tokens = self._issue_tokens(str(user.id))
        return user, tokens

    async def login(self, email: str, password: str):
        user = await self.repo.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        return self._issue_tokens(str(user.id))

    def _issue_tokens(self, subject: str) -> dict[str, str]:
        return {
            "access_token": create_access_token(subject),
            "refresh_token": create_refresh_token(subject),
        }
