from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.assessments.models import Assessment
from apps.common.models import Job, JobStatus, JobType
from apps.roadmaps.models import Roadmap


class JobsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_job(self, job_id: UUID) -> Job | None:
        result = await self.db.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    async def get_job_for_user(self, *, job_id: UUID, user_id: UUID) -> Job | None:
        result = await self.db.execute(
            select(Job)
            .outerjoin(Assessment, Assessment.id == Job.assessment_id)
            .outerjoin(Roadmap, Roadmap.id == Job.roadmap_id)
            .where(Job.id == job_id)
            .where(or_(Assessment.user_id == user_id, Roadmap.user_id == user_id))
        )
        return result.scalar_one_or_none()

    async def get_job_by_key(
        self,
        *,
        job_type: JobType,
        idempotency_key: str,
    ) -> Job | None:
        result = await self.db.execute(
            select(Job).where(
                Job.job_type == job_type,
                Job.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_job(
        self,
        *,
        job_type: JobType,
        idempotency_key: str,
        assessment_id: UUID | None = None,
        roadmap_id: UUID | None = None,
        trace_id: str | None = None,
    ) -> Job:
        existing = await self.get_job_by_key(job_type=job_type, idempotency_key=idempotency_key)
        if existing is not None:
            if trace_id and not existing.trace_id:
                existing.trace_id = trace_id
                await self.db.commit()
                await self.db.refresh(existing)
            return existing

        job = Job(
            job_type=job_type,
            idempotency_key=idempotency_key,
            status=JobStatus.pending,
            assessment_id=assessment_id,
            roadmap_id=roadmap_id,
            trace_id=trace_id,
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def get_latest_job_for_assessment(self, assessment_id: UUID) -> Job | None:
        result = await self.db.execute(
            select(Job)
            .where(Job.assessment_id == assessment_id, Job.job_type == JobType.score_job)
            .order_by(Job.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_job_for_roadmap(self, roadmap_id: UUID) -> Job | None:
        result = await self.db.execute(
            select(Job)
            .where(Job.roadmap_id == roadmap_id, Job.job_type == JobType.roadmap_job)
            .order_by(Job.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def mark_running(self, *, job_id: UUID, trace_id: str | None = None) -> Job:
        result = await self.db.execute(select(Job).where(Job.id == job_id).with_for_update())
        job = result.scalar_one()
        if job.status != JobStatus.completed:
            job.status = JobStatus.running
            job.attempts += 1
            job.started_at = datetime.now(UTC)
            if trace_id:
                job.trace_id = trace_id
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def mark_pending_retry(self, *, job_id: UUID, error_message: str) -> Job:
        result = await self.db.execute(select(Job).where(Job.id == job_id).with_for_update())
        job = result.scalar_one()
        if job.status != JobStatus.completed:
            job.status = JobStatus.pending
            job.last_error = error_message
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def mark_completed(self, *, job_id: UUID, duration_ms: int) -> Job:
        result = await self.db.execute(select(Job).where(Job.id == job_id).with_for_update())
        job = result.scalar_one()
        now = datetime.now(UTC)
        job.status = JobStatus.completed
        job.last_error = None
        job.duration_ms = duration_ms
        job.completed_at = now
        if job.started_at is None:
            job.started_at = now
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def mark_failed(
        self,
        *,
        job_id: UUID,
        error_message: str,
        duration_ms: int,
        dead_letter: bool = False,
    ) -> Job:
        result = await self.db.execute(select(Job).where(Job.id == job_id).with_for_update())
        job = result.scalar_one()
        now = datetime.now(UTC)
        job.status = JobStatus.dead_letter if dead_letter else JobStatus.failed
        job.last_error = error_message
        job.duration_ms = duration_ms
        job.completed_at = now
        if job.started_at is None:
            job.started_at = now
        await self.db.commit()
        await self.db.refresh(job)
        return job
