from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_internal_token
from app.db import get_db
from apps.ingestion.models import IngestionRunItemStatus, IngestionRunTrigger
from apps.ingestion.repositories import IngestionRepository
from apps.ingestion.schemas import (
    IngestionDispatchResponse,
    IngestionRunRead,
    ReprocessSourceRequest,
    SourceRegistryRead,
)
from apps.ingestion.services import IngestionPipelineService, SourceRegistryService
from apps.ingestion.tasks import ingest_source_task

router = APIRouter(prefix="/ingestion", tags=["ingestion"])
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/source-registry/seed",
    dependencies=[Depends(require_internal_token)],
)
async def seed_source_registry(db: DbSession) -> dict:
    service = SourceRegistryService(db)
    seeded = await service.seed_default_sources()
    return {"seeded": seeded}


@router.get(
    "/source-registry",
    dependencies=[Depends(require_internal_token)],
)
async def list_source_registry(
    db: DbSession,
    country_code: str | None = None,
) -> list[SourceRegistryRead]:
    service = SourceRegistryService(db)
    return await service.list_active_sources(country_code=country_code)


@router.post(
    "/reprocess-source",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_internal_token)],
)
async def reprocess_source(
    payload: ReprocessSourceRequest,
    db: DbSession,
) -> IngestionDispatchResponse:
    service = IngestionPipelineService(db)
    run_id, run_item_ids = await service.create_run(
        trigger_type=IngestionRunTrigger.reprocess,
        requested_by="internal-api",
        trace_id=payload.trace_id,
        source_key=payload.source_key,
        metadata_json={"requested_via": "internal_endpoint"},
    )
    if not run_item_ids:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="run has no items",
        )

    run_item_id = run_item_ids[0]
    if payload.sync:
        item_status = await service.process_run_item(run_item_id=run_item_id, attempt_number=1)
        await service.finalize_run(run_id)
        return IngestionDispatchResponse(
            run_id=run_id,
            run_item_id=run_item_id,
            celery_task_id=None,
            status=item_status,
        )

    task = ingest_source_task.apply_async(
        kwargs={
            "run_id": str(run_id),
            "run_item_id": str(run_item_id),
            "trace_id": payload.trace_id,
        },
        queue="ingestion_queue",
    )
    return IngestionDispatchResponse(
        run_id=run_id,
        run_item_id=run_item_id,
        celery_task_id=task.id,
        status=IngestionRunItemStatus.pending,
    )


@router.get(
    "/runs/{run_id}",
    dependencies=[Depends(require_internal_token)],
)
async def get_ingestion_run(run_id: UUID, db: DbSession) -> IngestionRunRead:
    repo = IngestionRepository(db)
    run = await repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ingestion run not found")
    return IngestionRunRead.model_validate(run)
