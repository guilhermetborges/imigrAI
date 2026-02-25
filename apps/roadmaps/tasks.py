import asyncio
import logging
import time
from uuid import UUID

from billiard.exceptions import SoftTimeLimitExceeded

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.db import AsyncSessionLocal
from apps.common.repositories import JobsRepository
from apps.roadmaps.services import RoadmapsService

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(
    bind=True,
    name="apps.roadmaps.tasks.generate_roadmap_task",
    max_retries=settings.roadmap_task_max_retries,
    soft_time_limit=settings.roadmap_task_soft_time_limit_seconds,
    time_limit=settings.roadmap_task_time_limit_seconds,
)
def generate_roadmap_task(
    self,
    roadmap_id: str,
    job_id: str,
    trace_id: str | None = None,
) -> dict:
    started = time.perf_counter()
    roadmap_uuid = UUID(roadmap_id)
    job_uuid = UUID(job_id)

    try:
        asyncio.run(
            _run_roadmap_job(
                roadmap_id=roadmap_uuid,
                job_id=job_uuid,
                trace_id=trace_id,
            )
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        asyncio.run(_mark_job_completed(job_uuid, duration_ms=duration_ms))
        logger.info(
            "roadmap_job_completed",
            extra={
                "roadmap_id": roadmap_id,
                "job_id": job_id,
                "trace_id": trace_id,
                "duration_ms": duration_ms,
            },
        )
        return {"status": "completed", "roadmap_id": roadmap_id, "job_id": job_id}
    except SoftTimeLimitExceeded as exc:
        _handle_failure(
            task=self,
            exc=exc,
            roadmap_id=roadmap_uuid,
            job_id=job_uuid,
            trace_id=trace_id,
            started=started,
            event="roadmap_job_timeout",
        )
        raise
    except Exception as exc:
        _handle_failure(
            task=self,
            exc=exc,
            roadmap_id=roadmap_uuid,
            job_id=job_uuid,
            trace_id=trace_id,
            started=started,
            event="roadmap_job_failed",
        )
        raise


async def _run_roadmap_job(*, roadmap_id: UUID, job_id: UUID, trace_id: str | None) -> None:
    async with AsyncSessionLocal() as db:
        jobs_repo = JobsRepository(db)
        await jobs_repo.mark_running(job_id=job_id, trace_id=trace_id)
        service = RoadmapsService(db)
        await service.process_roadmap(roadmap_id)


async def _mark_job_completed(job_id: UUID, *, duration_ms: int) -> None:
    async with AsyncSessionLocal() as db:
        jobs_repo = JobsRepository(db)
        await jobs_repo.mark_completed(job_id=job_id, duration_ms=duration_ms)


def _handle_failure(
    *,
    task,
    exc: Exception,
    roadmap_id: UUID,
    job_id: UUID,
    trace_id: str | None,
    started: float,
    event: str,
) -> None:
    retries = int(task.request.retries)
    max_retries = int(task.max_retries or 0)
    duration_ms = int((time.perf_counter() - started) * 1000)
    error_message = str(exc)
    dead_letter = retries >= max_retries

    asyncio.run(
        _mark_failure_state(
            roadmap_id=roadmap_id,
            job_id=job_id,
            error_message=error_message,
            duration_ms=duration_ms,
            dead_letter=dead_letter,
        )
    )

    if dead_letter:
        logger.error(
            event,
            extra={
                "roadmap_id": str(roadmap_id),
                "job_id": str(job_id),
                "trace_id": trace_id,
                "retries": retries,
                "duration_ms": duration_ms,
                "dead_letter": True,
                "error": error_message,
            },
        )
        return

    countdown = max(1, 2**retries)
    logger.warning(
        f"{event}_retry",
        extra={
            "roadmap_id": str(roadmap_id),
            "job_id": str(job_id),
            "trace_id": trace_id,
            "retries": retries,
            "next_retry_in_seconds": countdown,
            "duration_ms": duration_ms,
            "error": error_message,
        },
    )
    raise task.retry(exc=exc, countdown=countdown)


async def _mark_failure_state(
    *,
    roadmap_id: UUID,
    job_id: UUID,
    error_message: str,
    duration_ms: int,
    dead_letter: bool,
) -> None:
    async with AsyncSessionLocal() as db:
        jobs_repo = JobsRepository(db)
        if dead_letter:
            await jobs_repo.mark_failed(
                job_id=job_id,
                error_message=error_message,
                duration_ms=duration_ms,
                dead_letter=True,
            )
        else:
            await jobs_repo.mark_pending_retry(job_id=job_id, error_message=error_message)

        service = RoadmapsService(db)
        if dead_letter:
            await service.mark_roadmap_failed(roadmap_id, error_message)
