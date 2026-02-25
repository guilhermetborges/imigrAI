from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from apps.immigration_rules.models import RuleGroupMatchOperator, RuleOperator
from apps.ingestion.models import (
    IngestionRunItemStatus,
    IngestionRunStatus,
    IngestionRunTrigger,
    ParserMode,
    SourceType,
)


class SourceRegistrySeed(BaseModel):
    source_key: str = Field(min_length=3, max_length=120)
    country_code: str = Field(min_length=2, max_length=2)
    country_name: str = Field(min_length=2, max_length=120)
    program_code: str = Field(min_length=2, max_length=64)
    program_name: str = Field(min_length=2, max_length=160)
    source_type: SourceType
    source_url: str
    robots_url: str | None = None
    terms_url: str | None = None
    schedule_cron: str | None = None
    parser_name: str = "deterministic-v1"
    parser_version: str = "1.0.0"
    confidence_threshold: Decimal = Decimal("0.80")
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SourceRegistryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_key: str
    country_code: str
    country_name: str
    program_code: str
    program_name: str
    source_type: SourceType
    source_url: str
    robots_url: str | None
    terms_url: str | None
    schedule_cron: str | None
    parser_name: str
    parser_version: str
    confidence_threshold: Decimal
    is_active: bool
    quarantine_until: datetime | None
    quarantine_reason: str | None
    consecutive_failures: int
    metadata_json: dict[str, Any]
    created_at: datetime


class IngestionRunCreate(BaseModel):
    trigger_type: IngestionRunTrigger
    source_ids: list[UUID] = Field(min_length=1)
    requested_by: str | None = None
    trace_id: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class IngestionRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trigger_type: IngestionRunTrigger
    status: IngestionRunStatus
    requested_by: str | None
    trace_id: str | None
    started_at: datetime | None
    completed_at: datetime | None
    total_items: int
    processed_items: int
    success_items: int
    failed_items: int
    notes: str | None
    metadata_json: dict[str, Any]
    created_at: datetime


class IngestionRunItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ingestion_run_id: UUID
    source_id: UUID
    status: IngestionRunItemStatus
    attempt_number: int
    started_at: datetime | None
    completed_at: datetime | None
    collected_at: datetime | None
    fetch_etag: str | None
    fetch_last_modified: str | None
    raw_hash_sha256: str | None
    semantic_hash_sha256: str | None
    parser_used: str | None
    parser_mode: ParserMode
    confidence_score: Decimal | None
    manual_review_required: bool
    error_message: str | None
    diff_summary_json: dict[str, Any]
    metadata_json: dict[str, Any]
    created_at: datetime


class BronzeDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    ingestion_run_item_id: UUID
    source_url: str
    content_type: str | None
    content_length: int | None
    storage_bucket: str
    storage_path: str
    storage_uri: str
    checksum_sha256: str
    metadata_json: dict[str, Any]
    created_at: datetime


class SilverSectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ingestion_run_item_id: UUID
    section_key: str
    heading: str | None
    section_order: int
    text_content: str
    semantic_hash_sha256: str
    metadata_json: dict[str, Any]
    created_at: datetime


class ReprocessSourceRequest(BaseModel):
    source_key: str = Field(min_length=3, max_length=120)
    sync: bool = False
    trace_id: str | None = None


class IngestionDispatchResponse(BaseModel):
    run_id: UUID
    run_item_id: UUID
    celery_task_id: str | None = None
    status: IngestionRunItemStatus


class NormalizedRuleCondition(BaseModel):
    field_key: str = Field(min_length=1, max_length=120)
    operator: RuleOperator
    value_json: Any
    condition_order: int = 1
    is_required: bool = True


class NormalizedRuleOutcome(BaseModel):
    score_delta: Decimal = Decimal("0")
    is_blocking: bool = False
    explanation_message: str = Field(min_length=3)
    outcome_code: str | None = Field(default=None, max_length=64)


class NormalizedRuleGroup(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=2, max_length=160)
    description: str | None = None
    priority: int = 100
    match_operator: RuleGroupMatchOperator = RuleGroupMatchOperator.all
    conditions: list[NormalizedRuleCondition] = Field(min_length=1)
    outcomes: list[NormalizedRuleOutcome] = Field(min_length=1)


class NormalizedProgramPayload(BaseModel):
    country_code: str = Field(min_length=2, max_length=2)
    country_name: str = Field(min_length=2, max_length=120)
    program_code: str = Field(min_length=2, max_length=64)
    program_name: str = Field(min_length=2, max_length=160)
    source_url: str
    source_title: str = Field(min_length=1, max_length=255)
    extracted_at: datetime
    parser_used: str = Field(min_length=1, max_length=64)
    parser_mode: ParserMode
    confidence_score: Decimal = Decimal("0.50")
    manual_review_required: bool = False
    summary_text: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    sections: list[dict[str, Any]] = Field(default_factory=list)
    rule_groups: list[NormalizedRuleGroup] = Field(min_length=1)

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(cls, value: str) -> str:
        return value.upper()

    @field_validator("program_code")
    @classmethod
    def normalize_program_code(cls, value: str) -> str:
        return value.upper().replace("-", "_")

    @field_validator("extracted_at", mode="before")
    @classmethod
    def ensure_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class DiffSummary(BaseModel):
    changed: bool
    previous_hash: str | None = None
    current_hash: str
    semantic_similarity: float = 1.0
    added_rule_groups: int = 0
    removed_rule_groups: int = 0
    added_conditions: int = 0
    removed_conditions: int = 0
    notes: str | None = None
