from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from apps.immigration_rules.models import (
    ProgramVersionStatus,
    RuleGroupMatchOperator,
    RuleOperator,
)


class CountryCreate(BaseModel):
    code: str = Field(min_length=2, max_length=2)
    name: str = Field(min_length=2, max_length=120)
    priority_rank: int | None = None
    diaspora_population_estimate: int | None = None
    prioritization_source_url: str | None = None


class CountryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    priority_rank: int | None = None
    diaspora_population_estimate: int | None = None
    prioritization_source_url: str | None = None
    is_active: bool | None = None


class CountryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    priority_rank: int | None
    diaspora_population_estimate: int | None
    prioritization_source_url: str | None
    is_active: bool
    created_at: datetime


class ImmigrationProgramCreate(BaseModel):
    country_id: UUID
    code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=2, max_length=160)
    description: str | None = None


class ImmigrationProgramUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = None
    is_active: bool | None = None


class ImmigrationProgramRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    country_id: UUID
    code: str
    name: str
    description: str | None
    is_active: bool
    created_at: datetime


class ProgramVersionCreate(BaseModel):
    program_id: UUID
    version: str = Field(min_length=1, max_length=32)
    status: ProgramVersionStatus = ProgramVersionStatus.draft
    effective_from: datetime
    effective_to: datetime | None = None


class ProgramVersionUpdate(BaseModel):
    version: str | None = Field(default=None, min_length=1, max_length=32)
    status: ProgramVersionStatus | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None


class ProgramVersionActivateRequest(BaseModel):
    force: bool = False


class ProgramVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    program_id: UUID
    version: str
    status: ProgramVersionStatus
    effective_from: datetime
    effective_to: datetime | None
    created_at: datetime


class RuleGroupCreate(BaseModel):
    program_version_id: UUID
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=2, max_length=160)
    description: str | None = None
    priority: int = 100
    match_operator: RuleGroupMatchOperator = RuleGroupMatchOperator.all


class RuleGroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = None
    priority: int | None = None
    match_operator: RuleGroupMatchOperator | None = None
    is_active: bool | None = None


class RuleGroupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    program_version_id: UUID
    code: str
    name: str
    description: str | None
    priority: int
    match_operator: RuleGroupMatchOperator
    is_active: bool
    created_at: datetime


class RuleConditionCreate(BaseModel):
    rule_group_id: UUID
    field_key: str = Field(min_length=1, max_length=120)
    operator: RuleOperator
    value_json: dict
    condition_order: int = 1
    is_required: bool = True


class RuleConditionUpdate(BaseModel):
    field_key: str | None = Field(default=None, min_length=1, max_length=120)
    operator: RuleOperator | None = None
    value_json: dict | None = None
    condition_order: int | None = None
    is_required: bool | None = None


class RuleConditionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rule_group_id: UUID
    field_key: str
    operator: RuleOperator
    value_json: dict
    condition_order: int
    is_required: bool
    created_at: datetime


class RuleOutcomeCreate(BaseModel):
    rule_group_id: UUID
    score_delta: Decimal = Decimal("0")
    is_blocking: bool = False
    explanation_message: str
    outcome_code: str | None = None


class RuleOutcomeUpdate(BaseModel):
    score_delta: Decimal | None = None
    is_blocking: bool | None = None
    explanation_message: str | None = None
    outcome_code: str | None = None


class RuleOutcomeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rule_group_id: UUID
    score_delta: Decimal
    is_blocking: bool
    explanation_message: str
    outcome_code: str | None
    created_at: datetime


class CountryCatalogRead(BaseModel):
    code: str
    name: str
    priority_rank: int | None
    diaspora_population_estimate: int | None
    program_count: int
    rule_coverage_status: str


class ProgramSourceCatalogRead(BaseModel):
    source_key: str | None
    title: str
    source_url: str


class ProgramCatalogRead(BaseModel):
    code: str
    name: str
    description: str | None
    version: str | None
    version_status: ProgramVersionStatus | None
    source_documents: list[ProgramSourceCatalogRead]


class CountryProgramsCatalogRead(BaseModel):
    country_code: str
    country_name: str
    programs: list[ProgramCatalogRead]
