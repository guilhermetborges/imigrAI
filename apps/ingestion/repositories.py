from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from apps.immigration_rules.models import (
    Country,
    ImmigrationProgram,
    ProgramVersion,
    ProgramVersionStatus,
    RuleCondition,
    RuleGroup,
    RuleOutcome,
)
from apps.ingestion.models import (
    BronzeDocument,
    IngestionRun,
    IngestionRunItem,
    IngestionRunItemStatus,
    IngestionRunStatus,
    IngestionRunTrigger,
    ParserMode,
    SilverSection,
    SourceDocument,
    SourceExtraction,
    SourceRegistry,
)
from apps.ingestion.schemas import SourceRegistrySeed


class IngestionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_source_by_key(self, source_key: str) -> SourceRegistry | None:
        query = select(SourceRegistry).where(SourceRegistry.source_key == source_key)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_active_sources(self, country_code: str | None = None) -> list[SourceRegistry]:
        query = select(SourceRegistry).where(SourceRegistry.is_active.is_(True))
        if country_code:
            query = query.where(SourceRegistry.country_code == country_code.upper())
        query = query.order_by(SourceRegistry.country_code.asc(), SourceRegistry.source_key.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_sources_for_scheduler(self) -> list[SourceRegistry]:
        now = datetime.now(UTC)
        query = select(SourceRegistry).where(
            SourceRegistry.is_active.is_(True),
            (SourceRegistry.quarantine_until.is_(None) | (SourceRegistry.quarantine_until <= now)),
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def upsert_source_seed(self, payload: SourceRegistrySeed) -> SourceRegistry:
        existing = await self.get_source_by_key(payload.source_key)
        if existing is None:
            source = SourceRegistry(**payload.model_dump())
            self.db.add(source)
            await self.db.flush()
            return source

        data = payload.model_dump()
        for field, value in data.items():
            setattr(existing, field, value)
        existing.is_active = True
        await self.db.flush()
        return existing

    async def create_ingestion_run(
        self,
        *,
        trigger_type: IngestionRunTrigger,
        requested_by: str | None,
        trace_id: str | None,
        source_count: int,
        metadata_json: dict,
    ) -> IngestionRun:
        run = IngestionRun(
            trigger_type=trigger_type,
            status=IngestionRunStatus.pending,
            requested_by=requested_by,
            trace_id=trace_id,
            total_items=source_count,
            metadata_json=metadata_json,
        )
        self.db.add(run)
        await self.db.flush()
        return run

    async def get_run(self, run_id: UUID) -> IngestionRun | None:
        result = await self.db.execute(select(IngestionRun).where(IngestionRun.id == run_id))
        return result.scalar_one_or_none()

    async def mark_run_running(self, run: IngestionRun) -> None:
        run.status = IngestionRunStatus.running
        run.started_at = datetime.now(UTC)
        await self.db.flush()

    async def mark_run_completed(
        self,
        run: IngestionRun,
        *,
        success_items: int,
        failed_items: int,
        notes: str | None = None,
    ) -> None:
        run.processed_items = success_items + failed_items
        run.success_items = success_items
        run.failed_items = failed_items
        run.status = (
            IngestionRunStatus.completed if failed_items == 0 else IngestionRunStatus.failed
        )
        run.completed_at = datetime.now(UTC)
        run.notes = notes
        await self.db.flush()

    async def create_run_item(self, *, run_id: UUID, source_id: UUID) -> IngestionRunItem:
        item = IngestionRunItem(
            ingestion_run_id=run_id,
            source_id=source_id,
            status=IngestionRunItemStatus.pending,
        )
        self.db.add(item)
        await self.db.flush()
        return item

    async def get_run_item(self, run_item_id: UUID) -> IngestionRunItem | None:
        query = (
            select(IngestionRunItem)
            .where(IngestionRunItem.id == run_item_id)
            .options(joinedload(IngestionRunItem.source), joinedload(IngestionRunItem.run))
        )
        result = await self.db.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_run_item_by_run_and_source(
        self, *, run_id: UUID, source_id: UUID
    ) -> IngestionRunItem | None:
        query = select(IngestionRunItem).where(
            IngestionRunItem.ingestion_run_id == run_id,
            IngestionRunItem.source_id == source_id,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_run_items(self, run_id: UUID) -> list[IngestionRunItem]:
        query = (
            select(IngestionRunItem)
            .where(IngestionRunItem.ingestion_run_id == run_id)
            .options(joinedload(IngestionRunItem.source))
            .order_by(IngestionRunItem.created_at.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def mark_run_item_running(self, item: IngestionRunItem, attempt_number: int) -> None:
        item.status = IngestionRunItemStatus.running
        item.started_at = datetime.now(UTC)
        item.attempt_number = attempt_number
        await self.db.flush()

    async def mark_run_item_completed(
        self,
        item: IngestionRunItem,
        *,
        status: IngestionRunItemStatus,
        raw_hash_sha256: str | None,
        semantic_hash_sha256: str | None,
        parser_used: str | None,
        parser_mode: ParserMode,
        confidence_score: float | None,
        manual_review_required: bool,
        diff_summary_json: dict,
        metadata_json: dict,
    ) -> None:
        item.status = status
        item.completed_at = datetime.now(UTC)
        item.collected_at = item.completed_at
        item.raw_hash_sha256 = raw_hash_sha256
        item.semantic_hash_sha256 = semantic_hash_sha256
        item.parser_used = parser_used
        item.parser_mode = parser_mode
        item.confidence_score = confidence_score
        item.manual_review_required = manual_review_required
        item.diff_summary_json = diff_summary_json
        item.metadata_json = metadata_json
        item.error_message = None
        await self.db.flush()

    async def mark_run_item_failed(self, item: IngestionRunItem, *, error_message: str) -> None:
        item.status = IngestionRunItemStatus.failed
        item.completed_at = datetime.now(UTC)
        item.error_message = error_message
        await self.db.flush()

    async def mark_run_item_quarantined(
        self, item: IngestionRunItem, *, error_message: str
    ) -> None:
        item.status = IngestionRunItemStatus.quarantined
        item.completed_at = datetime.now(UTC)
        item.error_message = error_message
        await self.db.flush()

    async def get_latest_bronze_document_by_source(self, source_id: UUID) -> BronzeDocument | None:
        query = (
            select(BronzeDocument)
            .where(BronzeDocument.source_id == source_id)
            .order_by(BronzeDocument.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_bronze_document(self, payload: dict) -> BronzeDocument:
        document = BronzeDocument(**payload)
        self.db.add(document)
        await self.db.flush()
        return document

    async def replace_silver_sections(
        self, *, run_item_id: UUID, sections_payload: list[dict]
    ) -> None:
        existing = await self.db.execute(
            select(SilverSection).where(SilverSection.ingestion_run_item_id == run_item_id)
        )
        for row in existing.scalars().all():
            await self.db.delete(row)

        for payload in sections_payload:
            self.db.add(SilverSection(ingestion_run_item_id=run_item_id, **payload))
        await self.db.flush()

    async def create_source_document(self, payload: dict) -> SourceDocument:
        source_doc = SourceDocument(**payload)
        self.db.add(source_doc)
        await self.db.flush()
        return source_doc

    async def create_source_extraction(self, payload: dict) -> SourceExtraction:
        extraction = SourceExtraction(**payload)
        self.db.add(extraction)
        await self.db.flush()
        return extraction

    async def get_country_by_code(self, code: str) -> Country | None:
        result = await self.db.execute(select(Country).where(Country.code == code.upper()))
        return result.scalar_one_or_none()

    async def create_country(self, payload: dict) -> Country:
        country = Country(**payload)
        self.db.add(country)
        await self.db.flush()
        return country

    async def get_program_by_country_and_code(
        self, *, country_id: UUID, code: str
    ) -> ImmigrationProgram | None:
        result = await self.db.execute(
            select(ImmigrationProgram).where(
                ImmigrationProgram.country_id == country_id,
                ImmigrationProgram.code == code,
            )
        )
        return result.scalar_one_or_none()

    async def create_program(self, payload: dict) -> ImmigrationProgram:
        program = ImmigrationProgram(**payload)
        self.db.add(program)
        await self.db.flush()
        return program

    async def list_active_program_versions(self, program_id: UUID) -> list[ProgramVersion]:
        query = select(ProgramVersion).where(
            ProgramVersion.program_id == program_id,
            ProgramVersion.status == ProgramVersionStatus.active,
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_latest_program_version(self, program_id: UUID) -> ProgramVersion | None:
        query = (
            select(ProgramVersion)
            .where(ProgramVersion.program_id == program_id)
            .order_by(ProgramVersion.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_latest_program_version_with_rules(
        self, program_id: UUID
    ) -> ProgramVersion | None:
        query = (
            select(ProgramVersion)
            .where(ProgramVersion.program_id == program_id)
            .order_by(ProgramVersion.created_at.desc())
            .limit(1)
            .options(
                selectinload(ProgramVersion.rule_groups).selectinload(RuleGroup.conditions),
                selectinload(ProgramVersion.rule_groups).selectinload(RuleGroup.outcomes),
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_program_version(self, payload: dict) -> ProgramVersion:
        version = ProgramVersion(**payload)
        self.db.add(version)
        await self.db.flush()
        return version

    async def archive_program_versions(
        self, versions: list[ProgramVersion], *, at: datetime
    ) -> None:
        for version in versions:
            version.status = ProgramVersionStatus.archived
            version.effective_to = at
        await self.db.flush()

    async def create_rule_group(self, payload: dict) -> RuleGroup:
        rule_group = RuleGroup(**payload)
        self.db.add(rule_group)
        await self.db.flush()
        return rule_group

    async def create_rule_condition(self, payload: dict) -> RuleCondition:
        condition = RuleCondition(**payload)
        self.db.add(condition)
        await self.db.flush()
        return condition

    async def create_rule_outcome(self, payload: dict) -> RuleOutcome:
        outcome = RuleOutcome(**payload)
        self.db.add(outcome)
        await self.db.flush()
        return outcome

    async def increase_source_failure(
        self, source: SourceRegistry, *, reason: str, quarantine_until: datetime | None
    ) -> None:
        source.consecutive_failures += 1
        source.quarantine_reason = reason
        source.quarantine_until = quarantine_until
        await self.db.flush()

    async def reset_source_health(self, source: SourceRegistry) -> None:
        source.consecutive_failures = 0
        source.quarantine_until = None
        source.quarantine_reason = None
        await self.db.flush()

    async def get_last_completed_item_for_source(self, source_id: UUID) -> IngestionRunItem | None:
        query = (
            select(IngestionRunItem)
            .where(
                and_(
                    IngestionRunItem.source_id == source_id,
                    IngestionRunItem.status.in_(
                        (
                            IngestionRunItemStatus.completed,
                            IngestionRunItemStatus.manual_review,
                            IngestionRunItemStatus.skipped,
                        )
                    ),
                )
            )
            .order_by(IngestionRunItem.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def commit(self) -> None:
        await self.db.commit()

    async def rollback(self) -> None:
        await self.db.rollback()
