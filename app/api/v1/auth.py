from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.rate_limit import rate_limit
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
)
from app.db import get_db
from apps.accounts.models import User
from apps.accounts.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPairResponse,
    UserResponse,
)
from apps.accounts.services import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
auth_rate_limiter = rate_limit(
    scope="auth",
    limit=settings.auth_rate_limit_requests,
    window_seconds=settings.auth_rate_limit_window_seconds,
    identity="user_or_ip",
)


@router.post(
    "/register", response_model=TokenPairResponse, dependencies=[Depends(auth_rate_limiter)]
)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenPairResponse:
    service = AuthService(db)
    _, tokens = await service.register(email=payload.email, password=payload.password)
    return TokenPairResponse(**tokens)


@router.post("/login", response_model=TokenPairResponse, dependencies=[Depends(auth_rate_limiter)])
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenPairResponse:
    service = AuthService(db)
    tokens = await service.login(email=payload.email, password=payload.password)
    return TokenPairResponse(**tokens)


@router.post(
    "/refresh", response_model=TokenPairResponse, dependencies=[Depends(auth_rate_limiter)]
)
async def refresh(payload: RefreshRequest) -> TokenPairResponse:
    token_payload = decode_token(payload.refresh_token, expected_type="refresh")
    subject = token_payload["sub"]
    return TokenPairResponse(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
