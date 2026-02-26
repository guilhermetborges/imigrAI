from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pwdlib import PasswordHash
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.log_context import bind_log_context
from app.db import get_db
from apps.accounts.models import User

password_hasher = PasswordHash.recommended()
bearer_scheme = HTTPBearer(auto_error=False)
internal_token_header = APIKeyHeader(name="x-internal-token", auto_error=False)
settings = get_settings()


class TokenError(HTTPException):
    def __init__(self, detail: str = "Could not validate credentials") -> None:
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hasher.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_hasher.hash(password)


def _create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str) -> str:
    return _create_token(
        subject,
        "access",
        timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(
        subject,
        "refresh",
        timedelta(minutes=settings.jwt_refresh_token_expire_minutes),
    )


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise TokenError() from exc

    if payload.get("type") != expected_type:
        raise TokenError("Invalid token type")
    if not payload.get("sub"):
        raise TokenError("Token subject is missing")
    return payload


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise TokenError("Authentication required")

    payload = decode_token(credentials.credentials, expected_type="access")
    user_id = UUID(payload["sub"])

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        raise TokenError("User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    bind_log_context(
        trace_id=getattr(request.state, "trace_id", None),
        user_id=str(user.id),
    )
    await apply_rls_context(db, user)
    return user


async def get_optional_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except TokenError:
        return None

    query = select(User).where(User.id == UUID(payload["sub"]))
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if user is None:
        return None

    bind_log_context(
        trace_id=getattr(request.state, "trace_id", None),
        user_id=str(user.id),
    )
    await apply_rls_context(db, user)
    return user


async def apply_rls_context(db: AsyncSession, user: User) -> None:
    try:
        await db.execute(
            text(
                "SELECT "
                "set_config('app.current_user_id', :user_id, true), "
                "set_config('app.current_user_role', :user_role, true)"
            ),
            {
                "user_id": str(user.id),
                "user_role": str(getattr(user, "role", "member")),
            },
        )
    except Exception:
        # SQLite de testes e alguns ambientes locais nao suportam set_config.
        return


def require_internal_token(token: str | None = Depends(internal_token_header)) -> None:
    if not settings.ingestion_internal_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal ingestion token is not configured",
        )
    if token != settings.ingestion_internal_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal token",
        )
