from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from apps.assessments.models import AssessmentStatus


class UserProfileSnapshotCreate(BaseModel):
    user_id: UUID
    snapshot_version: int = Field(ge=1)
    profile_json: dict
    profile_hash: str = Field(min_length=64, max_length=64)


class UserProfileSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    snapshot_version: int
    profile_json: dict
    profile_hash: str
    created_at: datetime


class AssessmentCreate(BaseModel):
    program_id: UUID
    profile_json: dict
    idempotency_key: str = Field(min_length=1, max_length=128)


class AssessmentPersistCreate(BaseModel):
    user_id: UUID
    program_id: UUID
    profile_snapshot_id: UUID
    idempotency_key: str = Field(min_length=1, max_length=128)
    requested_at: datetime


class AssessmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    program_id: UUID
    profile_snapshot_id: UUID
    idempotency_key: str
    status: AssessmentStatus
    requested_at: datetime
    completed_at: datetime | None
    created_at: datetime


class AssessmentResultCreate(BaseModel):
    assessment_id: UUID
    program_version_id: UUID
    rules_version_hash: str = Field(min_length=64, max_length=64)
    algorithm_version: str = Field(min_length=1, max_length=32)
    total_score: Decimal
    is_eligible: bool
    computed_at: datetime


class AssessmentResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assessment_id: UUID
    program_version_id: UUID
    rules_version_hash: str
    algorithm_version: str
    total_score: Decimal
    is_eligible: bool
    computed_at: datetime
    created_at: datetime


class AssessmentResultItemCreate(BaseModel):
    assessment_result_id: UUID
    rule_group_id: UUID | None = None
    rule_condition_id: UUID | None = None
    rule_outcome_id: UUID | None = None
    applied: bool
    score_delta: Decimal
    explanation_message: str
    audit_payload_json: dict = Field(default_factory=dict)


class AssessmentResultItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assessment_result_id: UUID
    rule_group_id: UUID | None
    rule_condition_id: UUID | None
    rule_outcome_id: UUID | None
    applied: bool
    score_delta: Decimal
    explanation_message: str
    audit_payload_json: dict
    created_at: datetime


class ProgramVersionUsedRead(BaseModel):
    id: UUID
    version: str
    effective_from: datetime
    effective_to: datetime | None


class AssessmentBreakdownEntryRead(BaseModel):
    rule_group_id: UUID | None
    rule_group_code: str
    rule_condition_id: UUID | None
    rule_outcome_id: UUID | None
    applied: bool
    score_delta: Decimal
    is_blocking: bool
    explanation_message: str
    condition_checks: list[dict]


class AssessmentBreakdownRead(BaseModel):
    assessment_id: UUID
    score_final: Decimal
    faixa: str
    fatores_positivos: list[str]
    gaps_criticos: list[str]
    program_version_used: ProgramVersionUsedRead
    algorithm_version: str
    rules_version_hash: str
    items: list[AssessmentBreakdownEntryRead]


class AssessmentQueuedRead(BaseModel):
    assessment_id: UUID
    status: AssessmentStatus
    job_id: UUID


class AssessmentStatusRead(BaseModel):
    assessment_id: UUID
    status: AssessmentStatus
    completed_at: datetime | None
    job_id: UUID | None
