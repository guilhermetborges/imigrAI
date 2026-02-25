from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from apps.common.schemas import JobRead
from apps.common.services import JobsService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobRead)
async def get_job_status(job_id: UUID, db: AsyncSession = Depends(get_db)) -> JobRead:
    service = JobsService(db)
    return await service.get_job_status(job_id)
