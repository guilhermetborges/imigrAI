"""dynamic rules foundation

Revision ID: 20260224_0002
Revises: 20260224_0001
Create Date: 2026-02-24 01:15:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260224_0002"
down_revision: str | None = "20260224_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


program_version_status = sa.Enum("draft", "active", "archived", name="program_version_status")
rule_group_match_operator = sa.Enum("all", "any", name="rule_group_match_operator")
rule_operator = sa.Enum(
    "eq",
    "ne",
    "gt",
    "gte",
    "lt",
    "lte",
    "between",
    "in",
    "not_in",
    "exists",
    name="rule_operator",
)
assessment_status = sa.Enum(
    "pending",
    "running",
    "completed",
    "failed",
    "canceled",
    name="assessment_status",
)
roadmap_status = sa.Enum("draft", "published", "archived", name="roadmap_status")
plan_interval = sa.Enum("month", "year", name="plan_interval")
subscription_status = sa.Enum(
    "trialing",
    "active",
    "past_due",
    "canceled",
    "expired",
    name="subscription_status",
)
entitlement_window = sa.Enum("daily", "monthly", "lifetime", name="entitlement_window")

NOW = sa.text("now()")
EMPTY_JSONB = sa.text("'{}'::jsonb")
SET_NULL = "SET NULL"
USERS_ID = "users.id"
PROGRAM_VERSIONS_ID = "program_versions.id"
RULE_GROUPS_ID = "rule_groups.id"
RULE_CONDITIONS_ID = "rule_conditions.id"
RULE_OUTCOMES_ID = "rule_outcomes.id"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "countries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=2), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=NOW,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_countries_code", "countries", ["code"], unique=True)

    op.create_table(
        "immigration_programs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("country_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=NOW,
        ),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("country_id", "code", name="uq_immigration_programs_country_code"),
    )
    op.create_index(
        "ix_immigration_programs_country_active",
        "immigration_programs",
        ["country_id", "is_active"],
    )

    op.create_table(
        "program_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("program_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("status", program_version_status, nullable=False, server_default="draft"),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "effective_period",
            postgresql.TSTZRANGE(),
            sa.Computed("tstzrange(effective_from, effective_to, '[)')", persisted=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=NOW,
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name="ck_program_versions_effective_range",
        ),
        sa.ForeignKeyConstraint(["program_id"], ["immigration_programs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("program_id", "version", name="uq_program_versions_program_version"),
    )
    op.create_index(
        "ix_program_versions_program_status_effective_from",
        "program_versions",
        ["program_id", "status", "effective_from"],
    )
    op.create_exclude_constraint(
        "ex_program_versions_active_no_overlap",
        "program_versions",
        ("program_id", "="),
        ("effective_period", "&&"),
        where=sa.text("status = 'active'"),
        using="gist",
    )

    op.create_table(
        "rule_groups",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("program_version_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column(
            "match_operator", rule_group_match_operator, nullable=False, server_default="all"
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=NOW,
        ),
        sa.ForeignKeyConstraint(
            ["program_version_id"], ["program_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "program_version_id", "code", name="uq_rule_groups_program_version_code"
        ),
    )
    op.create_index(
        "ix_rule_groups_program_version_priority",
        "rule_groups",
        ["program_version_id", "priority"],
    )

    op.create_table(
        "rule_conditions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("rule_group_id", sa.UUID(), nullable=False),
        sa.Column("field_key", sa.String(length=120), nullable=False),
        sa.Column("operator", rule_operator, nullable=False),
        sa.Column("value_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("condition_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=NOW,
        ),
        sa.ForeignKeyConstraint(["rule_group_id"], [RULE_GROUPS_ID], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_rule_conditions_group_field_operator",
        "rule_conditions",
        ["rule_group_id", "field_key", "operator"],
    )
    op.create_index(
        "ix_rule_conditions_value_json_gin",
        "rule_conditions",
        ["value_json"],
        postgresql_using="gin",
    )

    op.create_table(
        "rule_outcomes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("rule_group_id", sa.UUID(), nullable=False),
        sa.Column(
            "score_delta", sa.Numeric(precision=8, scale=2), nullable=False, server_default="0"
        ),
        sa.Column("is_blocking", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("explanation_message", sa.Text(), nullable=False),
        sa.Column("outcome_code", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=NOW,
        ),
        sa.ForeignKeyConstraint(["rule_group_id"], [RULE_GROUPS_ID], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_rule_outcomes_group_blocking", "rule_outcomes", ["rule_group_id", "is_blocking"]
    )

    op.create_table(
        "source_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("program_version_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("raw_storage_uri", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=EMPTY_JSONB,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=NOW,
        ),
        sa.ForeignKeyConstraint(["program_version_id"], [PROGRAM_VERSIONS_ID], ondelete=SET_NULL),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_source_documents_program_version_published_at",
        "source_documents",
        ["program_version_id", "published_at"],
    )
    op.create_index("ix_source_documents_checksum_sha256", "source_documents", ["checksum_sha256"])

    op.create_table(
        "source_extractions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_document_id", sa.UUID(), nullable=False),
        sa.Column("extraction_version", sa.String(length=32), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column(
            "structured_data_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=EMPTY_JSONB,
        ),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=NOW,
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"], ["source_documents.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_document_id",
            "extraction_version",
            name="uq_source_extractions_document_version",
        ),
    )
    op.create_index(
        "ix_source_extractions_document_created_at",
        "source_extractions",
        ["source_document_id", "created_at"],
    )

    op.create_table(
        "user_profile_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("snapshot_version", sa.Integer(), nullable=False),
        sa.Column("profile_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("profile_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=NOW,
        ),
        sa.ForeignKeyConstraint(["user_id"], [USERS_ID], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "snapshot_version", name="uq_profile_snapshots_user_version"
        ),
    )
    op.create_index(
        "ix_user_profile_snapshots_profile_hash", "user_profile_snapshots", ["profile_hash"]
    )
    op.create_index(
        "ix_user_profile_snapshots_user_created_at",
        "user_profile_snapshots",
        ["user_id", "created_at"],
    )

    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_user_profile_snapshot_update()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'user_profile_snapshots are immutable';
        END;
        $$ LANGUAGE plpgsql;
        """)
    op.execute("""
        CREATE TRIGGER trg_user_profile_snapshots_immutable
        BEFORE UPDATE ON user_profile_snapshots
        FOR EACH ROW EXECUTE FUNCTION prevent_user_profile_snapshot_update();
        """)

    op.create_table(
        "assessments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("program_id", sa.UUID(), nullable=False),
        sa.Column("profile_snapshot_id", sa.UUID(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("status", assessment_status, nullable=False, server_default="pending"),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=NOW,
        ),
        sa.ForeignKeyConstraint(
            ["profile_snapshot_id"], ["user_profile_snapshots.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["program_id"], ["immigration_programs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], [USERS_ID], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "idempotency_key", name="uq_assessments_user_idempotency_key"
        ),
    )
    op.create_index(
        "ix_assessments_user_status_requested_at",
        "assessments",
        ["user_id", "status", "requested_at"],
    )

    op.create_table(
        "assessment_results",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("assessment_id", sa.UUID(), nullable=False),
        sa.Column("program_version_id", sa.UUID(), nullable=False),
        sa.Column("rules_version_hash", sa.String(length=64), nullable=False),
        sa.Column("algorithm_version", sa.String(length=32), nullable=False),
        sa.Column("total_score", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("is_eligible", sa.Boolean(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=NOW,
        ),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["program_version_id"], [PROGRAM_VERSIONS_ID], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assessment_id", name="uq_assessment_results_assessment_id"),
    )
    op.create_index(
        "ix_assessment_results_program_version_hash",
        "assessment_results",
        ["program_version_id", "rules_version_hash"],
    )

    op.create_table(
        "assessment_result_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("assessment_result_id", sa.UUID(), nullable=False),
        sa.Column("rule_group_id", sa.UUID(), nullable=True),
        sa.Column("rule_condition_id", sa.UUID(), nullable=True),
        sa.Column("rule_outcome_id", sa.UUID(), nullable=True),
        sa.Column("applied", sa.Boolean(), nullable=False),
        sa.Column("score_delta", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("explanation_message", sa.Text(), nullable=False),
        sa.Column(
            "audit_payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=EMPTY_JSONB,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=NOW,
        ),
        sa.ForeignKeyConstraint(
            ["assessment_result_id"], ["assessment_results.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["rule_condition_id"], [RULE_CONDITIONS_ID], ondelete=SET_NULL),
        sa.ForeignKeyConstraint(["rule_group_id"], [RULE_GROUPS_ID], ondelete=SET_NULL),
        sa.ForeignKeyConstraint(["rule_outcome_id"], [RULE_OUTCOMES_ID], ondelete=SET_NULL),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_assessment_result_items_result_rule_outcome",
        "assessment_result_items",
        ["assessment_result_id", "rule_outcome_id"],
    )

    op.create_table(
        "roadmaps",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("assessment_result_id", sa.UUID(), nullable=False),
        sa.Column("roadmap_schema_version", sa.String(length=16), nullable=False),
        sa.Column("status", roadmap_status, nullable=False, server_default="draft"),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=NOW,
        ),
        sa.ForeignKeyConstraint(
            ["assessment_result_id"], ["assessment_results.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["user_id"], [USERS_ID], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_roadmaps_user_created_at", "roadmaps", ["user_id", "created_at"])

    op.create_table(
        "roadmap_steps",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("roadmap_id", sa.UUID(), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "related_gap_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=EMPTY_JSONB,
        ),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("eta_weeks", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=NOW,
        ),
        sa.ForeignKeyConstraint(["roadmap_id"], ["roadmaps.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("roadmap_id", "step_order", name="uq_roadmap_steps_order"),
    )

    op.create_table(
        "plans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="BRL"),
        sa.Column("billing_interval", plan_interval, nullable=False, server_default="month"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=NOW,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plans_code", "plans", ["code"], unique=True)

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column("status", subscription_status, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=NOW,
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], [USERS_ID], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscriptions_user_status", "subscriptions", ["user_id", "status"])

    op.create_table(
        "entitlements",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.UUID(), nullable=True),
        sa.Column("subscription_id", sa.UUID(), nullable=True),
        sa.Column("feature_key", sa.String(length=64), nullable=False),
        sa.Column("limit_value", sa.Integer(), nullable=True),
        sa.Column("usage_window", entitlement_window, nullable=False, server_default="monthly"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=NOW,
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete=SET_NULL),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete=SET_NULL),
        sa.ForeignKeyConstraint(["user_id"], [USERS_ID], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "feature_key",
            "usage_window",
            "valid_from",
            name="uq_entitlements_user_feature_window_from",
        ),
    )
    op.create_index(
        "ix_entitlements_user_feature_window",
        "entitlements",
        ["user_id", "feature_key", "usage_window"],
    )


def downgrade() -> None:
    op.drop_index("ix_entitlements_user_feature_window", table_name="entitlements")
    op.drop_table("entitlements")

    op.drop_index("ix_subscriptions_user_status", table_name="subscriptions")
    op.drop_table("subscriptions")

    op.drop_index("ix_plans_code", table_name="plans")
    op.drop_table("plans")

    op.drop_table("roadmap_steps")

    op.drop_index("ix_roadmaps_user_created_at", table_name="roadmaps")
    op.drop_table("roadmaps")

    op.drop_index(
        "ix_assessment_result_items_result_rule_outcome",
        table_name="assessment_result_items",
    )
    op.drop_table("assessment_result_items")

    op.drop_index("ix_assessment_results_program_version_hash", table_name="assessment_results")
    op.drop_table("assessment_results")

    op.drop_index("ix_assessments_user_status_requested_at", table_name="assessments")
    op.drop_table("assessments")

    op.execute(
        "DROP TRIGGER IF EXISTS trg_user_profile_snapshots_immutable ON user_profile_snapshots"
    )
    op.execute("DROP FUNCTION IF EXISTS prevent_user_profile_snapshot_update")

    op.drop_index("ix_user_profile_snapshots_user_created_at", table_name="user_profile_snapshots")
    op.drop_index("ix_user_profile_snapshots_profile_hash", table_name="user_profile_snapshots")
    op.drop_table("user_profile_snapshots")

    op.drop_index("ix_source_extractions_document_created_at", table_name="source_extractions")
    op.drop_table("source_extractions")

    op.drop_index("ix_source_documents_checksum_sha256", table_name="source_documents")
    op.drop_index("ix_source_documents_program_version_published_at", table_name="source_documents")
    op.drop_table("source_documents")

    op.drop_index("ix_rule_outcomes_group_blocking", table_name="rule_outcomes")
    op.drop_table("rule_outcomes")

    op.drop_index("ix_rule_conditions_value_json_gin", table_name="rule_conditions")
    op.drop_index("ix_rule_conditions_group_field_operator", table_name="rule_conditions")
    op.drop_table("rule_conditions")

    op.drop_index("ix_rule_groups_program_version_priority", table_name="rule_groups")
    op.drop_table("rule_groups")

    op.drop_constraint("ex_program_versions_active_no_overlap", "program_versions", type_="exclude")
    op.drop_index(
        "ix_program_versions_program_status_effective_from", table_name="program_versions"
    )
    op.drop_table("program_versions")

    op.drop_index("ix_immigration_programs_country_active", table_name="immigration_programs")
    op.drop_table("immigration_programs")

    op.drop_index("ix_countries_code", table_name="countries")
    op.drop_table("countries")

    entitlement_window.drop(op.get_bind(), checkfirst=True)
    subscription_status.drop(op.get_bind(), checkfirst=True)
    plan_interval.drop(op.get_bind(), checkfirst=True)
    roadmap_status.drop(op.get_bind(), checkfirst=True)
    assessment_status.drop(op.get_bind(), checkfirst=True)
    rule_operator.drop(op.get_bind(), checkfirst=True)
    rule_group_match_operator.drop(op.get_bind(), checkfirst=True)
    program_version_status.drop(op.get_bind(), checkfirst=True)
