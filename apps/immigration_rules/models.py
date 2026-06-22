import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
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


class ProgramVersionStatus(enum.StrEnum):
    draft = "draft"
    active = "active"
    archived = "archived"


class RuleOperator(enum.StrEnum):
    eq = "eq"
    ne = "ne"
    gt = "gt"
    gte = "gte"
    lt = "lt"
    lte = "lte"
    between = "between"
    in_ = "in"
    not_in = "not_in"
    exists = "exists"


class RuleGroupMatchOperator(enum.StrEnum):
    all = "all"
    any = "any"


class Country(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "countries"

    code: Mapped[str] = mapped_column(String(2), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    priority_rank: Mapped[int | None] = mapped_column(Integer, index=True)
    diaspora_population_estimate: Mapped[int | None] = mapped_column(Integer)
    prioritization_source_url: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    programs: Mapped[list["ImmigrationProgram"]] = relationship(back_populates="country")


class ImmigrationProgram(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "immigration_programs"
    __table_args__ = (
        UniqueConstraint("country_id", "code", name="uq_immigration_programs_country_code"),
    )

    country_id: Mapped[UUID] = mapped_column(
        ForeignKey("countries.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    country: Mapped["Country"] = relationship(back_populates="programs")
    versions: Mapped[list["ProgramVersion"]] = relationship(back_populates="program")


class ProgramVersion(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "program_versions"
    __table_args__ = (
        UniqueConstraint("program_id", "version", name="uq_program_versions_program_version"),
        CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name="ck_program_versions_effective_range",
        ),
    )

    program_id: Mapped[UUID] = mapped_column(
        ForeignKey("immigration_programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[ProgramVersionStatus] = mapped_column(
        Enum(ProgramVersionStatus, name="program_version_status"),
        nullable=False,
        default=ProgramVersionStatus.draft,
        index=True,
    )
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    program: Mapped["ImmigrationProgram"] = relationship(back_populates="versions")
    rule_groups: Mapped[list["RuleGroup"]] = relationship(back_populates="program_version")
    source_documents: Mapped[list["SourceDocument"]] = relationship(
        back_populates="program_version"
    )


class RuleGroup(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "rule_groups"
    __table_args__ = (
        UniqueConstraint("program_version_id", "code", name="uq_rule_groups_program_version_code"),
    )

    program_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("program_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    match_operator: Mapped[RuleGroupMatchOperator] = mapped_column(
        Enum(RuleGroupMatchOperator, name="rule_group_match_operator"),
        nullable=False,
        default=RuleGroupMatchOperator.all,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    program_version: Mapped["ProgramVersion"] = relationship(back_populates="rule_groups")
    conditions: Mapped[list["RuleCondition"]] = relationship(back_populates="rule_group")
    outcomes: Mapped[list["RuleOutcome"]] = relationship(back_populates="rule_group")


class RuleCondition(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "rule_conditions"

    rule_group_id: Mapped[UUID] = mapped_column(
        ForeignKey("rule_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_key: Mapped[str] = mapped_column(String(120), nullable=False)
    operator: Mapped[RuleOperator] = mapped_column(
        Enum(RuleOperator, name="rule_operator"),
        nullable=False,
    )
    value_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    condition_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    rule_group: Mapped["RuleGroup"] = relationship(back_populates="conditions")


class RuleOutcome(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "rule_outcomes"

    rule_group_id: Mapped[UUID] = mapped_column(
        ForeignKey("rule_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score_delta: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    is_blocking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    explanation_message: Mapped[str] = mapped_column(Text, nullable=False)
    outcome_code: Mapped[str | None] = mapped_column(String(64))

    rule_group: Mapped["RuleGroup"] = relationship(back_populates="outcomes")


if TYPE_CHECKING:
    from apps.ingestion.models import SourceDocument
