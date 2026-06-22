import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from apps.common.models import CreatedAtMixin, UUIDPrimaryKeyMixin


class RoadmapStatus(enum.StrEnum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    draft = "draft"
    published = "published"
    archived = "archived"


class Roadmap(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "roadmaps"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assessment_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessment_results.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    roadmap_schema_version: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[RoadmapStatus] = mapped_column(
        Enum(RoadmapStatus, name="roadmap_status"),
        nullable=False,
        default=RoadmapStatus.pending,
        index=True,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    manual_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    llm_provider: Mapped[str | None] = mapped_column(String(32))
    llm_model: Mapped[str | None] = mapped_column(String(64))
    generation_error: Mapped[str | None] = mapped_column(Text)
    trace_id: Mapped[str | None] = mapped_column(String(64), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship()
    assessment_result: Mapped["AssessmentResult"] = relationship()
    steps: Mapped[list["RoadmapStep"]] = relationship(back_populates="roadmap")


class RoadmapStep(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "roadmap_steps"
    __table_args__ = (UniqueConstraint("roadmap_id", "step_order", name="uq_roadmap_steps_order"),)

    roadmap_id: Mapped[UUID] = mapped_column(
        ForeignKey("roadmaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    related_gap_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    eta_weeks: Mapped[int | None] = mapped_column(Integer)
    dependencies_json: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False, default="medio")
    completion_criteria: Mapped[str] = mapped_column(Text, nullable=False, default="")

    roadmap: Mapped["Roadmap"] = relationship(back_populates="steps")


if TYPE_CHECKING:
    from apps.accounts.models import User
    from apps.assessments.models import AssessmentResult
