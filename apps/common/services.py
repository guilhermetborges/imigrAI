from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.repositories import JobsRepository
from apps.common.schemas import JobRead


class JobsService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = JobsRepository(db)

    async def get_job_status(self, job_id: UUID) -> JobRead:
        job = await self.repo.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        return JobRead.model_validate(job)
