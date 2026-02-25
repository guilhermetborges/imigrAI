import asyncio
import logging
import time
from uuid import UUID

from billiard.exceptions import SoftTimeLimitExceeded

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.db import AsyncSessionLocal
from apps.assessments.services import AssessmentsService
from apps.common.repositories import JobsRepository

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(
    bind=True,
    name="apps.assessments.tasks.process_assessment_task",
    max_retries=settings.score_task_max_retries,
    soft_time_limit=settings.score_task_soft_time_limit_seconds,
    time_limit=settings.score_task_time_limit_seconds,
)
def process_assessment_task(
    self,
    assessment_id: str,
    job_id: str,
    trace_id: str | None = None,
) -> dict:
    started = time.perf_counter()
    assessment_uuid = UUID(assessment_id)
    job_uuid = UUID(job_id)

    try:
        asyncio.run(
            _run_assessment_job(
                assessment_id=assessment_uuid,
                job_id=job_uuid,
                trace_id=trace_id,
            )
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        asyncio.run(_mark_job_completed(job_uuid, duration_ms=duration_ms))
        logger.info(
            "score_job_completed",
            extra={
                "assessment_id": assessment_id,
                "job_id": job_id,
                "trace_id": trace_id,
                "duration_ms": duration_ms,
            },
        )
        return {"status": "completed", "assessment_id": assessment_id, "job_id": job_id}
    except SoftTimeLimitExceeded as exc:
        _handle_failure(
            task=self,
            exc=exc,
            job_id=job_uuid,
            trace_id=trace_id,
            started=started,
            event="score_job_timeout",
        )
        raise
    except Exception as exc:
        _handle_failure(
            task=self,
            exc=exc,
            job_id=job_uuid,
            trace_id=trace_id,
            started=started,
            event="score_job_failed",
        )
        raise


async def _run_assessment_job(*, assessment_id: UUID, job_id: UUID, trace_id: str | None) -> None:
    async with AsyncSessionLocal() as db:
        jobs_repo = JobsRepository(db)
        await jobs_repo.mark_running(job_id=job_id, trace_id=trace_id)
        service = AssessmentsService(db)
        await service.process_assessment(assessment_id)


async def _mark_job_completed(job_id: UUID, *, duration_ms: int) -> None:
    async with AsyncSessionLocal() as db:
        jobs_repo = JobsRepository(db)
        await jobs_repo.mark_completed(job_id=job_id, duration_ms=duration_ms)


def _handle_failure(
    *,
    task,
    exc: Exception,
    job_id: UUID,
    trace_id: str | None,
    started: float,
    event: str,
) -> None:
    retries = int(task.request.retries)
    max_retries = int(task.max_retries or 0)
    duration_ms = int((time.perf_counter() - started) * 1000)
    error_message = str(exc)

    if retries >= max_retries:
        asyncio.run(
            _mark_job_failed(
                job_id=job_id,
                error_message=error_message,
                duration_ms=duration_ms,
                dead_letter=True,
            )
        )
        logger.error(
            event,
            extra={
                "job_id": str(job_id),
                "trace_id": trace_id,
                "retries": retries,
                "duration_ms": duration_ms,
                "dead_letter": True,
                "error": error_message,
            },
        )
        return

    asyncio.run(_mark_job_pending_retry(job_id=job_id, error_message=error_message))
    countdown = max(1, 2**retries)
    logger.warning(
        f"{event}_retry",
        extra={
            "job_id": str(job_id),
            "trace_id": trace_id,
            "retries": retries,
            "next_retry_in_seconds": countdown,
            "duration_ms": duration_ms,
            "error": error_message,
        },
    )
    raise task.retry(exc=exc, countdown=countdown)


async def _mark_job_pending_retry(*, job_id: UUID, error_message: str) -> None:
    async with AsyncSessionLocal() as db:
        jobs_repo = JobsRepository(db)
        await jobs_repo.mark_pending_retry(job_id=job_id, error_message=error_message)


async def _mark_job_failed(
    *,
    job_id: UUID,
    error_message: str,
    duration_ms: int,
    dead_letter: bool,
) -> None:
    async with AsyncSessionLocal() as db:
        jobs_repo = JobsRepository(db)
        await jobs_repo.mark_failed(
            job_id=job_id,
            error_message=error_message,
            duration_ms=duration_ms,
            dead_letter=dead_letter,
        )
