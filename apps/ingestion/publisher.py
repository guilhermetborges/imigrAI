from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from apps.immigration_rules.models import ProgramVersionStatus
from apps.ingestion.models import IngestionRunItem, SourceRegistry
from apps.ingestion.repositories import IngestionRepository
from apps.ingestion.schemas import DiffSummary, NormalizedProgramPayload


class Publisher:
    def __init__(self, repo: IngestionRepository) -> None:
        self.repo = repo

    async def publish(
        self,
        *,
        source: SourceRegistry,
        run_item: IngestionRunItem,
        payload: NormalizedProgramPayload,
        diff_summary: DiffSummary,
        semantic_hash: str,
        raw_hash_sha256: str,
        raw_storage_uri: str,
        allow_publish: bool,
    ) -> dict:
        country = await self.repo.get_country_by_code(payload.country_code)
        if country is None:
            country = await self.repo.create_country(
                {"code": payload.country_code, "name": payload.country_name}
            )

        program = await self.repo.get_program_by_country_and_code(
            country_id=country.id,
            code=payload.program_code,
        )
        if program is None:
            program = await self.repo.create_program(
                {
                    "country_id": country.id,
                    "code": payload.program_code,
                    "name": payload.program_name,
                    "description": f"Auto-created from source registry ({source.source_key})",
                    "is_active": True,
                }
            )

        latest_program_version = await self.repo.get_latest_program_version(program.id)
        published_version_id: UUID | None = (
            latest_program_version.id if latest_program_version else None
        )
        published = False

        if allow_publish and diff_summary.changed:
            published_version_id, published = await self._publish_version(
                program=program,
                payload=payload,
                semantic_hash=semantic_hash,
            )

        source_document = await self.repo.create_source_document(
            {
                "source_id": source.id,
                "ingestion_run_item_id": run_item.id,
                "program_version_id": published_version_id,
                "title": payload.source_title,
                "source_url": payload.source_url,
                "checksum_sha256": raw_hash_sha256,
                "raw_storage_uri": raw_storage_uri,
                "published_at": datetime.now(UTC),
                "metadata_json": {
                    "parser_used": payload.parser_used,
                    "parser_mode": payload.parser_mode.value,
                    "manual_review_required": payload.manual_review_required,
                    "semantic_hash_sha256": semantic_hash,
                    "diff": diff_summary.model_dump(),
                },
            }
        )

        extraction = await self.repo.create_source_extraction(
            {
                "source_document_id": source_document.id,
                "extraction_version": source.parser_version,
                "extracted_text": payload.summary_text,
                "structured_data_json": payload.model_dump(mode="json"),
                "confidence_score": payload.confidence_score,
                "parser_used": payload.parser_used,
                "parser_mode": payload.parser_mode,
                "manual_review_required": payload.manual_review_required,
                "semantic_hash_sha256": semantic_hash,
                "extraction_metadata_json": {
                    "published": published,
                    "diff_summary": diff_summary.model_dump(),
                },
            }
        )

        return {
            "published": published,
            "program_version_id": str(published_version_id) if published_version_id else None,
            "source_document_id": str(source_document.id),
            "source_extraction_id": str(extraction.id),
        }

    async def _publish_version(
        self,
        *,
        program: object,
        payload: NormalizedProgramPayload,
        semantic_hash: str,
    ) -> tuple[UUID, bool]:
        now = datetime.now(UTC)
        active_versions = await self.repo.list_active_program_versions(program.id)
        if active_versions:
            await self.repo.archive_program_versions(active_versions, at=now)

        version_label = self._build_version_label(now=now, semantic_hash=semantic_hash)
        program_version = await self.repo.create_program_version(
            {
                "program_id": program.id,
                "version": version_label,
                "status": ProgramVersionStatus.active,
                "effective_from": now,
                "effective_to": None,
            }
        )

        for group in payload.rule_groups:
            rule_group = await self.repo.create_rule_group(
                {
                    "program_version_id": program_version.id,
                    "code": group.code,
                    "name": group.name,
                    "description": group.description,
                    "priority": group.priority,
                    "match_operator": group.match_operator,
                }
            )
            for condition in group.conditions:
                await self.repo.create_rule_condition(
                    {
                        "rule_group_id": rule_group.id,
                        "field_key": condition.field_key,
                        "operator": condition.operator,
                        "value_json": condition.value_json,
                        "condition_order": condition.condition_order,
                        "is_required": condition.is_required,
                    }
                )
            for outcome in group.outcomes:
                await self.repo.create_rule_outcome(
                    {
                        "rule_group_id": rule_group.id,
                        "score_delta": outcome.score_delta,
                        "is_blocking": outcome.is_blocking,
                        "explanation_message": outcome.explanation_message,
                        "outcome_code": outcome.outcome_code,
                    }
                )

        return program_version.id, True

    def _build_version_label(self, *, now: datetime, semantic_hash: str) -> str:
        label = f"{now:%Y%m%d%H%M%S}-{semantic_hash[:8]}"
        return label[:32]
