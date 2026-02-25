from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from apps.roadmaps.models import RoadmapStatus

ROADMAP_SCHEMA_VERSION_V1 = "roadmap.v1"


class RoadmapStepContract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    step_order: int = Field(ge=1)
    titulo: str = Field(min_length=3, max_length=180)
    descricao: str = Field(min_length=10)
    prazo_estimado_semanas: int = Field(ge=1)
    dependencias: list[int] = Field(default_factory=list)
    risco: Literal["baixo", "medio", "alto"]
    criterio_conclusao: str = Field(min_length=10)
    gap_relacionado: str | None = None
    is_required: bool = True

    @field_validator("dependencias")
    @classmethod
    def validate_dependencias(cls, value: list[int]) -> list[int]:
        return sorted({item for item in value if item >= 1})


class RoadmapContract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    roadmap_schema_version: str = Field(min_length=1, max_length=16)
    objetivo: str = Field(min_length=10)
    manual_review_required: bool = False
    passos_priorizados: list[RoadmapStepContract] = Field(min_length=1)


class RoadmapCreate(BaseModel):
    assessment_id: UUID
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=128)


class RoadmapQueuedRead(BaseModel):
    roadmap_id: UUID
    status: RoadmapStatus
    roadmap_schema_version: str
    job_id: UUID


class RoadmapStatusRead(BaseModel):
    roadmap_id: UUID
    status: RoadmapStatus
    completed_at: datetime | None
    error: str | None
    job_id: UUID | None


class RoadmapRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    assessment_result_id: UUID
    roadmap_schema_version: str
    status: RoadmapStatus
    summary: str
    manual_review_required: bool
    llm_provider: str | None
    llm_model: str | None
    generation_error: str | None
    trace_id: str | None
    completed_at: datetime | None
    created_at: datetime


class RoadmapStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    roadmap_id: UUID
    step_order: int
    title: str
    description: str
    related_gap_json: dict
    is_required: bool
    eta_weeks: int | None
    dependencies_json: list[int]
    risk_level: str
    completion_criteria: str
    created_at: datetime


class RoadmapDetailRead(BaseModel):
    roadmap: RoadmapRead
    steps: list[RoadmapStepRead]
