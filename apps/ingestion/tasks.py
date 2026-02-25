import asyncio
import logging
import time
from uuid import UUID

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.db import AsyncSessionLocal
from apps.ingestion.models import IngestionRunItemStatus, IngestionRunTrigger
from apps.ingestion.repositories import IngestionRepository
from apps.ingestion.services import IngestionPipelineService

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(
    bind=True,
    name="apps.ingestion.tasks.ingest_source_task",
    max_retries=settings.ingestion_task_max_retries,
    soft_time_limit=settings.ingestion_task_soft_time_limit_seconds,
    time_limit=settings.ingestion_task_time_limit_seconds,
)
def ingest_source_task(
    self,
    run_id: str,
    run_item_id: str,
    trace_id: str | None = None,
) -> dict:
    started = time.perf_counter()
    run_uuid = UUID(run_id)
    run_item_uuid = UUID(run_item_id)

    try:
        status = asyncio.run(
            _process_run_item(
                run_id=run_uuid,
                run_item_id=run_item_uuid,
                attempt_number=int(self.request.retries) + 1,
                trace_id=trace_id,
            )
        )
        asyncio.run(_finalize_run(run_uuid))
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "ingestion_item_completed",
            extra={
                "run_id": run_id,
                "run_item_id": run_item_id,
                "status": status.value,
                "trace_id": trace_id,
                "duration_ms": duration_ms,
            },
        )
        return {"status": status.value, "run_id": run_id, "run_item_id": run_item_id}
    except Exception as exc:
        retries = int(self.request.retries)
        max_retries = int(self.max_retries or 0)
        if retries >= max_retries:
            asyncio.run(_finalize_run(run_uuid))
            logger.error(
                "ingestion_item_dead_letter",
                extra={
                    "run_id": run_id,
                    "run_item_id": run_item_id,
                    "trace_id": trace_id,
                    "error": str(exc),
                },
            )
            raise

        countdown = max(1, settings.ingestion_retry_backoff_base_seconds * (2**retries))
        logger.warning(
            "ingestion_item_retry",
            extra={
                "run_id": run_id,
                "run_item_id": run_item_id,
                "trace_id": trace_id,
                "retries": retries,
                "next_retry_in_seconds": countdown,
                "error": str(exc),
            },
        )
        raise self.retry(exc=exc, countdown=countdown) from exc


@celery_app.task(
    name="apps.ingestion.tasks.dispatch_country_ingestion_task",
)
def dispatch_country_ingestion_task(
    country_code: str,
    trace_id: str | None = None,
) -> dict:
    run_id, item_ids = asyncio.run(
        _create_run(
            trigger_type=IngestionRunTrigger.scheduled,
            country_code=country_code.upper(),
            trace_id=trace_id,
            requested_by="celery-country-dispatcher",
        )
    )
    for item_id in item_ids:
        ingest_source_task.apply_async(
            kwargs={
                "run_id": str(run_id),
                "run_item_id": str(item_id),
                "trace_id": trace_id,
            },
            queue="ingestion_queue",
        )
    return {"run_id": str(run_id), "items": len(item_ids), "country_code": country_code.upper()}


@celery_app.task(name="apps.ingestion.tasks.dispatch_scheduled_ingestion")
def dispatch_scheduled_ingestion() -> dict:
    try:
        run_id, item_ids = asyncio.run(
            _create_run(
                trigger_type=IngestionRunTrigger.scheduled,
                country_code=None,
                trace_id=None,
                requested_by="celery-beat",
                scheduler_filtered=True,
            )
        )
    except RuntimeError:
        return {"run_id": None, "items": 0}
    for item_id in item_ids:
        ingest_source_task.apply_async(
            kwargs={"run_id": str(run_id), "run_item_id": str(item_id), "trace_id": None},
            queue="ingestion_queue",
        )
    return {"run_id": str(run_id), "items": len(item_ids)}


async def _create_run(
    *,
    trigger_type: IngestionRunTrigger,
    country_code: str | None,
    trace_id: str | None,
    requested_by: str,
    scheduler_filtered: bool = False,
) -> tuple[UUID, list[UUID]]:
    async with AsyncSessionLocal() as db:
        service = IngestionPipelineService(db)
        if scheduler_filtered:
            repo = IngestionRepository(db)
            sources = await repo.list_sources_for_scheduler()
            if not sources:
                raise RuntimeError("no eligible source for scheduled ingestion")
            return await service.gateway.create_run_with_items(
                trigger_type=trigger_type,
                source_ids=[source.id for source in sources],
                requested_by=requested_by,
                trace_id=trace_id,
                metadata_json={"scheduler_filtered": True},
            )

        return await service.create_run(
            trigger_type=trigger_type,
            requested_by=requested_by,
            trace_id=trace_id,
            country_code=country_code,
        )


async def _process_run_item(
    *,
    run_id: UUID,
    run_item_id: UUID,
    attempt_number: int,
    trace_id: str | None,
) -> IngestionRunItemStatus:
    _ = trace_id
    async with AsyncSessionLocal() as db:
        service = IngestionPipelineService(db)
        status = await service.process_run_item(
            run_item_id=run_item_id, attempt_number=attempt_number
        )
        return status


async def _finalize_run(run_id: UUID) -> None:
    async with AsyncSessionLocal() as db:
        service = IngestionPipelineService(db)
        await service.finalize_run(run_id)
