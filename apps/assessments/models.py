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
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from apps.common.models import CreatedAtMixin, UUIDPrimaryKeyMixin


class AssessmentStatus(enum.StrEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    canceled = "canceled"


class UserProfileSnapshot(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "user_profile_snapshots"
    __table_args__ = (
        UniqueConstraint("user_id", "snapshot_version", name="uq_profile_snapshots_user_version"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshot_version: Mapped[int] = mapped_column(Integer, nullable=False)
    profile_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    profile_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    user: Mapped["User"] = relationship()
    assessments: Mapped[list["Assessment"]] = relationship(back_populates="profile_snapshot")


class Assessment(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "assessments"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_assessments_user_idempotency_key"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id: Mapped[UUID] = mapped_column(
        ForeignKey("immigration_programs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    profile_snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_profile_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[AssessmentStatus] = mapped_column(
        Enum(AssessmentStatus, name="assessment_status"),
        nullable=False,
        default=AssessmentStatus.pending,
        index=True,
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship()
    program: Mapped["ImmigrationProgram"] = relationship()
    profile_snapshot: Mapped["UserProfileSnapshot"] = relationship(back_populates="assessments")
    result: Mapped["AssessmentResult | None"] = relationship(back_populates="assessment")


class AssessmentResult(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "assessment_results"
    __table_args__ = (
        UniqueConstraint("assessment_id", name="uq_assessment_results_assessment_id"),
    )

    assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("program_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    rules_version_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    algorithm_version: Mapped[str] = mapped_column(String(32), nullable=False)
    total_score: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    is_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    assessment: Mapped["Assessment"] = relationship(back_populates="result")
    program_version: Mapped["ProgramVersion"] = relationship()
    items: Mapped[list["AssessmentResultItem"]] = relationship(back_populates="assessment_result")


class AssessmentResultItem(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "assessment_result_items"

    assessment_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessment_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_group_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("rule_groups.id", ondelete="SET NULL"),
        index=True,
    )
    rule_condition_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("rule_conditions.id", ondelete="SET NULL"),
        index=True,
    )
    rule_outcome_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("rule_outcomes.id", ondelete="SET NULL"),
        index=True,
    )
    applied: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score_delta: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    explanation_message: Mapped[str] = mapped_column(Text, nullable=False)
    audit_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    assessment_result: Mapped["AssessmentResult"] = relationship(back_populates="items")


if TYPE_CHECKING:
    from apps.accounts.models import User
    from apps.immigration_rules.models import ImmigrationProgram, ProgramVersion
