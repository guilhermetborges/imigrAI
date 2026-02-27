"""async jobs and roadmap pipeline fields

Revision ID: 20260225_0003
Revises: 20260224_0002
Create Date: 2026-02-25 00:15:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260225_0003"
down_revision: str | None = "20260224_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


job_type = sa.Enum("score_job", "roadmap_job", name="job_type")
job_status = sa.Enum("pending", "running", "completed", "failed", "dead_letter", name="job_status")


def upgrade() -> None:
    op.execute("ALTER TYPE roadmap_status ADD VALUE IF NOT EXISTS 'pending'")
    op.execute("ALTER TYPE roadmap_status ADD VALUE IF NOT EXISTS 'completed'")
    op.execute("ALTER TYPE roadmap_status ADD VALUE IF NOT EXISTS 'failed'")
    op.alter_column("roadmaps", "status", server_default="pending")

    op.create_table(
        "jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("job_type", job_type, nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("status", job_status, nullable=False, server_default="pending"),
        sa.Column("assessment_id", sa.UUID(), nullable=True),
        sa.Column("roadmap_id", sa.UUID(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "queued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["roadmap_id"], ["roadmaps.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_type", "idempotency_key", name="uq_jobs_type_idempotency"),
    )
    op.create_index("ix_jobs_job_type", "jobs", ["job_type"])
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_assessment_id", "jobs", ["assessment_id"])
    op.create_index("ix_jobs_roadmap_id", "jobs", ["roadmap_id"])
    op.create_index("ix_jobs_trace_id", "jobs", ["trace_id"])

    op.add_column(
        "roadmaps",
        sa.Column(
            "manual_review_required", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    op.add_column("roadmaps", sa.Column("llm_provider", sa.String(length=32), nullable=True))
    op.add_column("roadmaps", sa.Column("llm_model", sa.String(length=64), nullable=True))
    op.add_column("roadmaps", sa.Column("generation_error", sa.Text(), nullable=True))
    op.add_column("roadmaps", sa.Column("trace_id", sa.String(length=64), nullable=True))
    op.add_column("roadmaps", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_roadmaps_trace_id", "roadmaps", ["trace_id"])

    op.add_column(
        "roadmap_steps",
        sa.Column(
            "dependencies_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "roadmap_steps",
        sa.Column("risk_level", sa.String(length=16), nullable=False, server_default="medio"),
    )
    op.add_column(
        "roadmap_steps",
        sa.Column("completion_criteria", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.alter_column("roadmaps", "status", server_default="draft")

    op.drop_column("roadmap_steps", "completion_criteria")
    op.drop_column("roadmap_steps", "risk_level")
    op.drop_column("roadmap_steps", "dependencies_json")

    op.drop_index("ix_roadmaps_trace_id", table_name="roadmaps")
    op.drop_column("roadmaps", "completed_at")
    op.drop_column("roadmaps", "trace_id")
    op.drop_column("roadmaps", "generation_error")
    op.drop_column("roadmaps", "llm_model")
    op.drop_column("roadmaps", "llm_provider")
    op.drop_column("roadmaps", "manual_review_required")

    op.drop_index("ix_jobs_trace_id", table_name="jobs")
    op.drop_index("ix_jobs_roadmap_id", table_name="jobs")
    op.drop_index("ix_jobs_assessment_id", table_name="jobs")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_index("ix_jobs_job_type", table_name="jobs")
    op.drop_table("jobs")

    job_status.drop(op.get_bind(), checkfirst=True)
    job_type.drop(op.get_bind(), checkfirst=True)
