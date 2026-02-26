from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import is_admin
from apps.accounts.models import User
from apps.common.repositories import JobsRepository
from apps.common.schemas import JobRead


class JobsService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = JobsRepository(db)

    async def get_job_status(self, *, job_id: UUID, user: User) -> JobRead:
        job = (
            await self.repo.get_job(job_id)
            if is_admin(user)
            else await self.repo.get_job_for_user(job_id=job_id, user_id=user.id)
        )
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        return JobRead.model_validate(job)
