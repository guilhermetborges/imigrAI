from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from apps.common.models import JobStatus, JobType


class JobCreate(BaseModel):
    job_type: JobType
    idempotency_key: str = Field(min_length=1, max_length=128)
    assessment_id: UUID | None = None
    roadmap_id: UUID | None = None
    trace_id: str | None = Field(default=None, max_length=64)


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_type: JobType
    idempotency_key: str
    status: JobStatus
    assessment_id: UUID | None
    roadmap_id: UUID | None
    attempts: int
    last_error: str | None
    trace_id: str | None
    duration_ms: int | None
    queued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
