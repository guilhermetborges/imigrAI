from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from apps.ingestion.diff_engine import DiffEngine
from apps.ingestion.extractors import DeterministicExtractor, LLMFallbackExtractor
from apps.ingestion.fetchers import SourceFetcher
from apps.ingestion.gateway import LocalDataGateway
from apps.ingestion.models import (
    IngestionRunItemStatus,
    IngestionRunStatus,
    IngestionRunTrigger,
)
from apps.ingestion.publisher import Publisher
from apps.ingestion.repositories import IngestionRepository
from apps.ingestion.schemas import (
    DiffSummary,
    IngestionRunRead,
    NormalizedProgramPayload,
    SourceRegistryRead,
)
from apps.ingestion.source_seeds import DEFAULT_SOURCE_SEEDS
from apps.ingestion.storage import BronzeStorageClient

logger = logging.getLogger(__name__)


class SourceRegistryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = IngestionRepository(db)
        settings = get_settings()
        self.gateway = LocalDataGateway(
            db,
            max_retries=settings.ingestion_gateway_max_retries,
            base_backoff_seconds=settings.ingestion_gateway_base_backoff_seconds,
            quarantine_hours=settings.ingestion_quarantine_hours,
            quarantine_after_failures=settings.ingestion_quarantine_after_failures,
        )

    async def seed_default_sources(self) -> int:
        return await self.gateway.seed_sources(DEFAULT_SOURCE_SEEDS)

    async def list_active_sources(
        self, country_code: str | None = None
    ) -> list[SourceRegistryRead]:
        sources = await self.repo.list_active_sources(country_code=country_code)
        return [SourceRegistryRead.model_validate(source) for source in sources]


class IngestionPipelineService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = IngestionRepository(db)
        self.settings = get_settings()
        self.gateway = LocalDataGateway(
            db,
            max_retries=self.settings.ingestion_gateway_max_retries,
            base_backoff_seconds=self.settings.ingestion_gateway_base_backoff_seconds,
            quarantine_hours=self.settings.ingestion_quarantine_hours,
            quarantine_after_failures=self.settings.ingestion_quarantine_after_failures,
        )
        self.fetcher = SourceFetcher(
            user_agent=self.settings.ingestion_user_agent,
            timeout_seconds=self.settings.ingestion_fetch_timeout_seconds,
            enforce_robots=self.settings.ingestion_enforce_robots,
        )
        self.storage = BronzeStorageClient(
            bucket=self.settings.ingestion_bronze_bucket,
            local_fallback_dir=self.settings.ingestion_local_fallback_dir,
        )
        self.deterministic_extractor = DeterministicExtractor()
        self.llm_fallback_extractor = LLMFallbackExtractor(
            api_key=self.settings.openai_api_key,
            model_name=self.settings.openai_model,
            timeout_seconds=self.settings.llm_timeout_seconds,
            temperature=self.settings.llm_temperature,
        )
        self.diff_engine = DiffEngine()
        self.publisher = Publisher(self.repo)

    async def create_run(
        self,
        *,
        trigger_type: IngestionRunTrigger,
        requested_by: str | None = None,
        trace_id: str | None = None,
        source_key: str | None = None,
        country_code: str | None = None,
        metadata_json: dict | None = None,
    ) -> tuple[UUID, list[UUID]]:
        if source_key:
            source = await self.repo.get_source_by_key(source_key)
            if source is None:
                raise ValueError(f"source_key not found: {source_key}")
            source_ids = [source.id]
        else:
            sources = await self.repo.list_active_sources(country_code=country_code)
            if not sources:
                raise ValueError("no active sources available for ingestion run")
            source_ids = [source.id for source in sources]

        return await self.gateway.create_run_with_items(
            trigger_type=trigger_type,
            source_ids=source_ids,
            requested_by=requested_by,
            trace_id=trace_id,
            metadata_json=metadata_json or {},
        )

    async def process_run_item(
        self,
        *,
        run_item_id: UUID,
        attempt_number: int = 1,
    ) -> IngestionRunItemStatus:
        item = await self.repo.get_run_item(run_item_id)
        if item is None:
            raise ValueError("ingestion run item not found")
        if item.source is None:
            raise ValueError("ingestion run item has no source")
        if item.run is None:
            raise ValueError("ingestion run item has no run")

        source = item.source
        run = item.run
        now = datetime.now(UTC)

        try:
            if run.status == IngestionRunStatus.pending:
                await self.repo.mark_run_running(run)
            await self.repo.mark_run_item_running(item, attempt_number=attempt_number)
            await self.repo.commit()

            if source.quarantine_until and source.quarantine_until > now:
                await self.repo.mark_run_item_quarantined(
                    item,
                    error_message=f"source quarantined until {source.quarantine_until.isoformat()}",
                )
                await self.repo.commit()
                return IngestionRunItemStatus.quarantined

            fetch_result = self.fetcher.fetch(source)
            raw_hash = hashlib.sha256(fetch_result.content).hexdigest()

            latest_bronze = await self.repo.get_latest_bronze_document_by_source(source.id)
            if latest_bronze and latest_bronze.checksum_sha256 == raw_hash:
                await self.repo.mark_run_item_completed(
                    item,
                    status=IngestionRunItemStatus.skipped,
                    raw_hash_sha256=raw_hash,
                    semantic_hash_sha256=item.semantic_hash_sha256,
                    parser_used=item.parser_used,
                    parser_mode=item.parser_mode,
                    confidence_score=(
                        float(item.confidence_score) if item.confidence_score else None
                    ),
                    manual_review_required=item.manual_review_required,
                    diff_summary_json={"changed": False, "reason": "raw hash unchanged"},
                    metadata_json={"fetch_metadata": fetch_result.metadata_json},
                )
                await self.repo.commit()
                return IngestionRunItemStatus.skipped

            stored = self.storage.store(
                source_key=source.source_key,
                run_item_id=item.id,
                payload=fetch_result.content,
                content_type=fetch_result.content_type,
            )
            await self.repo.create_bronze_document(
                {
                    "source_id": source.id,
                    "ingestion_run_item_id": item.id,
                    "source_url": fetch_result.final_url,
                    "content_type": fetch_result.content_type,
                    "content_length": fetch_result.content_length,
                    "storage_bucket": stored.bucket,
                    "storage_path": stored.path,
                    "storage_uri": stored.uri,
                    "checksum_sha256": raw_hash,
                    "metadata_json": {
                        **fetch_result.metadata_json,
                        **stored.metadata_json,
                    },
                }
            )

            deterministic = self.deterministic_extractor.extract(
                source=source,
                content=fetch_result.content,
                content_type=fetch_result.content_type,
                title=fetch_result.title,
            )
            payload = deterministic.payload

            if payload.confidence_score < source.confidence_threshold:
                payload = self.llm_fallback_extractor.extract(
                    source=source,
                    text_content=deterministic.text_content,
                    fallback_title=fetch_result.title,
                )

            validated_payload = NormalizedProgramPayload.model_validate(
                payload.model_dump(mode="json")
            )
            semantic_hash = self.diff_engine.compute_semantic_hash(validated_payload)

            previous_item = await self.repo.get_last_completed_item_for_source(source.id)
            previous_hash = previous_item.semantic_hash_sha256 if previous_item else None

            previous_program_version = None
            country = await self.repo.get_country_by_code(validated_payload.country_code)
            if country is not None:
                program = await self.repo.get_program_by_country_and_code(
                    country_id=country.id,
                    code=validated_payload.program_code,
                )
                if program is not None:
                    previous_program_version = (
                        await self.repo.get_latest_program_version_with_rules(program.id)
                    )

            diff_summary: DiffSummary = self.diff_engine.compare(
                payload=validated_payload,
                current_hash=semantic_hash,
                previous_hash=previous_hash,
                previous_program_version=previous_program_version,
            )

            await self.repo.replace_silver_sections(
                run_item_id=item.id,
                sections_payload=[
                    {
                        **section,
                        "semantic_hash_sha256": hashlib.sha256(
                            section["text_content"].encode("utf-8")
                        ).hexdigest(),
                    }
                    for section in validated_payload.sections
                ],
            )

            can_auto_publish = (
                not validated_payload.manual_review_required
                and validated_payload.confidence_score >= source.confidence_threshold
            )
            publish_result = await self.publisher.publish(
                source=source,
                run_item=item,
                payload=validated_payload,
                diff_summary=diff_summary,
                semantic_hash=semantic_hash,
                raw_hash_sha256=raw_hash,
                raw_storage_uri=stored.uri,
                allow_publish=can_auto_publish,
            )

            status = IngestionRunItemStatus.completed
            if not can_auto_publish:
                status = IngestionRunItemStatus.manual_review
            elif not diff_summary.changed:
                status = IngestionRunItemStatus.skipped

            await self.repo.mark_run_item_completed(
                item,
                status=status,
                raw_hash_sha256=raw_hash,
                semantic_hash_sha256=semantic_hash,
                parser_used=validated_payload.parser_used,
                parser_mode=validated_payload.parser_mode,
                confidence_score=float(validated_payload.confidence_score),
                manual_review_required=validated_payload.manual_review_required,
                diff_summary_json=diff_summary.model_dump(),
                metadata_json={
                    "fetch_etag": fetch_result.etag,
                    "fetch_last_modified": fetch_result.last_modified,
                    "publish": publish_result,
                },
            )
            await self.repo.reset_source_health(source)
            await self.repo.commit()
            return status
        except Exception as exc:
            logger.exception(
                "ingestion_run_item_failed",
                extra={"run_item_id": str(run_item_id), "source_key": source.source_key},
            )
            await self.repo.rollback()
            _, quarantined = await self.gateway.mark_source_failure(
                source_id=source.id, reason=str(exc)
            )
            item = await self.repo.get_run_item(run_item_id)
            if item is not None:
                if quarantined:
                    await self.repo.mark_run_item_quarantined(item, error_message=str(exc))
                else:
                    await self.repo.mark_run_item_failed(item, error_message=str(exc))
                await self.repo.commit()
            raise

    async def finalize_run(self, run_id: UUID) -> IngestionRunRead:
        run = await self.repo.get_run(run_id)
        if run is None:
            raise ValueError("ingestion run not found")

        items = await self.repo.list_run_items(run_id)
        success_statuses = {
            IngestionRunItemStatus.completed,
            IngestionRunItemStatus.skipped,
            IngestionRunItemStatus.manual_review,
        }
        success_items = sum(1 for item in items if item.status in success_statuses)
        failed_items = sum(
            1
            for item in items
            if item.status in {IngestionRunItemStatus.failed, IngestionRunItemStatus.quarantined}
        )
        pending_items = sum(
            1
            for item in items
            if item.status in {IngestionRunItemStatus.pending, IngestionRunItemStatus.running}
        )

        if pending_items > 0:
            run.processed_items = success_items + failed_items
            run.success_items = success_items
            run.failed_items = failed_items
            run.status = IngestionRunStatus.running
            await self.repo.commit()
            return IngestionRunRead.model_validate(run)

        notes = None
        if failed_items:
            notes = "Run completed with failures and/or quarantined sources."

        await self.repo.mark_run_completed(
            run,
            success_items=success_items,
            failed_items=failed_items,
            notes=notes,
        )
        await self.repo.commit()
        return IngestionRunRead.model_validate(run)
