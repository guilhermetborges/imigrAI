import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import TypeVar
from uuid import UUID

from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.ingestion.models import IngestionRunTrigger, SourceRegistry
from apps.ingestion.repositories import IngestionRepository
from apps.ingestion.schemas import SourceRegistrySeed

T = TypeVar("T")

logger = logging.getLogger(__name__)


class LocalDataGateway:
    def __init__(
        self,
        db: AsyncSession,
        *,
        max_retries: int = 3,
        base_backoff_seconds: float = 0.5,
        quarantine_hours: int = 24,
        quarantine_after_failures: int = 3,
    ) -> None:
        self.db = db
        self.repo = IngestionRepository(db)
        self.max_retries = max_retries
        self.base_backoff_seconds = base_backoff_seconds
        self.quarantine_hours = quarantine_hours
        self.quarantine_after_failures = quarantine_after_failures

    async def with_retry(self, operation_name: str, operation: Callable[[], Awaitable[T]]) -> T:
        for attempt in range(self.max_retries + 1):
            try:
                return await operation()
            except DBAPIError as exc:
                if attempt >= self.max_retries:
                    logger.exception(
                        "gateway_operation_failed",
                        extra={
                            "operation": operation_name,
                            "attempts": attempt + 1,
                            "error": str(exc),
                        },
                    )
                    raise
                delay = self.base_backoff_seconds * (2**attempt)
                logger.warning(
                    "gateway_operation_retry",
                    extra={
                        "operation": operation_name,
                        "attempt": attempt + 1,
                        "next_delay_seconds": delay,
                        "error": str(exc),
                    },
                )
                await asyncio.sleep(delay)
        raise RuntimeError(f"operation {operation_name} exceeded retry guard")

    @asynccontextmanager
    async def transaction(self):
        try:
            yield
            await self.db.commit()
        except:
            await self.db.rollback()
            raise

    async def seed_sources(self, seeds: list[SourceRegistrySeed]) -> int:
        async def _seed() -> int:
            async with self.transaction():
                for seed in seeds:
                    await self.repo.upsert_source_seed(seed)
            return len(seeds)

        return await self.with_retry("seed_sources", _seed)

    async def create_run_with_items(
        self,
        *,
        trigger_type: IngestionRunTrigger,
        source_ids: list[UUID],
        requested_by: str | None,
        trace_id: str | None,
        metadata_json: dict,
    ) -> tuple[UUID, list[UUID]]:
        async def _create() -> tuple[UUID, list[UUID]]:
            async with self.transaction():
                run = await self.repo.create_ingestion_run(
                    trigger_type=trigger_type,
                    requested_by=requested_by,
                    trace_id=trace_id,
                    source_count=len(source_ids),
                    metadata_json=metadata_json,
                )
                item_ids: list[UUID] = []
                for source_id in source_ids:
                    item = await self.repo.create_run_item(run_id=run.id, source_id=source_id)
                    item_ids.append(item.id)
            return run.id, item_ids

        return await self.with_retry("create_run_with_items", _create)

    async def reset_source_health(self, source_id: UUID) -> None:
        async def _reset() -> None:
            async with self.transaction():
                source = await self.db.get(SourceRegistry, source_id)
                if source is None:
                    return
                await self.repo.reset_source_health(source)

        await self.with_retry("reset_source_health", _reset)

    async def mark_source_failure(self, *, source_id: UUID, reason: str) -> tuple[int, bool]:
        async def _mark() -> tuple[int, bool]:
            async with self.transaction():
                source = await self.db.get(SourceRegistry, source_id)
                if source is None:
                    return 0, False
                quarantine_until = None
                new_total = int(source.consecutive_failures) + 1
                should_quarantine = new_total >= self.quarantine_after_failures
                if should_quarantine:
                    quarantine_until = datetime.now(UTC) + timedelta(hours=self.quarantine_hours)
                await self.repo.increase_source_failure(
                    source,
                    reason=reason,
                    quarantine_until=quarantine_until,
                )
                return source.consecutive_failures, should_quarantine

        return await self.with_retry("mark_source_failure", _mark)


SupabaseDataGateway = LocalDataGateway
