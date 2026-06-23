from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db import get_db
from apps.accounts.models import User
from apps.common.schemas import JobRead
from apps.common.services import JobsService

router = APIRouter(prefix="/jobs", tags=["jobs"])
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/{job_id}")
async def get_job_status(
    job_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> JobRead:
    service = JobsService(db)
    return await service.get_job_status(job_id=job_id, user=current_user)
