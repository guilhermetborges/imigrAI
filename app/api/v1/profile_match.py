from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, get_optional_current_user
from app.db import get_db
from apps.accounts.models import User
from apps.profile_match.schemas import (
    ProfileMatchClaimRequest,
    ProfileMatchResultRead,
    ProfileMatchSubmitRead,
    ProfileMatchSubmitRequest,
)
from apps.profile_match.services import ProfileMatchService

router = APIRouter(prefix="/profile-match", tags=["profile-match"])


@router.post("/submit", response_model=ProfileMatchSubmitRead, status_code=status.HTTP_201_CREATED)
async def submit_profile_match(
    payload: ProfileMatchSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> ProfileMatchSubmitRead:
    service = ProfileMatchService(db)
    return await service.submit_profile(payload=payload, current_user=current_user)


@router.post("/claim", response_model=ProfileMatchResultRead)
async def claim_profile_match(
    payload: ProfileMatchClaimRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProfileMatchResultRead:
    service = ProfileMatchService(db)
    return await service.claim_submission(payload=payload, user=current_user)


@router.get("/{submission_id}/results", response_model=ProfileMatchResultRead)
async def get_profile_match_results(
    submission_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProfileMatchResultRead:
    service = ProfileMatchService(db)
    return await service.get_results(submission_id=submission_id, user=current_user)
