from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.rate_limit import rate_limit
from app.core.security import get_current_user
from app.db import get_db
from apps.accounts.models import User
from apps.assessments.schemas import (
    AssessmentBreakdownRead,
    AssessmentCreate,
    AssessmentQueuedRead,
    AssessmentStatusRead,
)
from apps.assessments.services import AssessmentsService

router = APIRouter(prefix="/assessments", tags=["assessments"])
settings = get_settings()
creation_rate_limiter = rate_limit(
    scope="assessment_create",
    limit=settings.creation_rate_limit_requests,
    window_seconds=settings.creation_rate_limit_window_seconds,
    identity="user_or_ip",
)
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
TraceIdHeader = Annotated[str | None, Header(default=None)]


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(creation_rate_limiter)],
)
async def create_assessment(
    payload: AssessmentCreate,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    x_trace_id: TraceIdHeader,
) -> AssessmentQueuedRead:
    service = AssessmentsService(db)
    trace_id = x_trace_id or getattr(request.state, "trace_id", None)
    return await service.create_assessment(
        user_id=current_user.id,
        payload=payload,
        trace_id=trace_id,
    )


@router.get("/{assessment_id}/status")
async def get_assessment_status(
    assessment_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> AssessmentStatusRead:
    service = AssessmentsService(db)
    return await service.get_assessment_status(assessment_id=assessment_id, user_id=current_user.id)


@router.get("/{assessment_id}/breakdown")
async def get_assessment_breakdown(
    assessment_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> AssessmentBreakdownRead:
    service = AssessmentsService(db)
    return await service.get_assessment_breakdown(
        assessment_id=assessment_id, user_id=current_user.id
    )
