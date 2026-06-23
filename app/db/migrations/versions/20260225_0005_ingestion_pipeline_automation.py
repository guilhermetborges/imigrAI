"""ingestion pipeline automation and audit trail

Revision ID: 20260225_0005
Revises: 20260225_0004
Create Date: 2026-02-25 11:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260225_0005"
down_revision: str | None = "20260225_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


source_type = sa.Enum("html", "pdf", "api", name="source_type")
ingestion_run_trigger = sa.Enum("scheduled", "manual", "reprocess", name="ingestion_run_trigger")
ingestion_run_status = sa.Enum(
    "pending", "running", "completed", "failed", "quarantined", name="ingestion_run_status"
)
ingestion_run_item_status = sa.Enum(
    "pending",
    "running",
    "skipped",
    "completed",
    "failed",
    "manual_review",
    "quarantined",
    name="ingestion_run_item_status",
)
ingestion_parser_mode = sa.Enum("deterministic", "llm_fallback", name="ingestion_parser_mode")

NOW = sa.text("now()")
EMPTY_JSONB = sa.text("'{}'::jsonb")


def upgrade() -> None:

    op.create_table(
        "source_registry",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_key", sa.String(length=120), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("country_name", sa.String(length=120), nullable=False),
        sa.Column("program_code", sa.String(length=64), nullable=False),
        sa.Column("program_name", sa.String(length=160), nullable=False),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("robots_url", sa.Text(), nullable=True),
        sa.Column("terms_url", sa.Text(), nullable=True),
        sa.Column("schedule_cron", sa.String(length=64), nullable=True),
        sa.Column(
            "parser_name", sa.String(length=64), nullable=False, server_default="deterministic-v1"
        ),
        sa.Column("parser_version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column(
            "confidence_threshold",
            sa.Numeric(precision=5, scale=4),
            nullable=False,
            server_default="0.8000",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("quarantine_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quarantine_reason", sa.Text(), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_key", name="uq_source_registry_source_key"),
    )
    op.create_index("ix_source_registry_source_key", "source_registry", ["source_key"])
    op.create_index("ix_source_registry_country_code", "source_registry", ["country_code"])
    op.create_index("ix_source_registry_program_code", "source_registry", ["program_code"])

    op.create_table(
        "ingestion_run",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "trigger_type", ingestion_run_trigger, nullable=False, server_default="scheduled"
        ),
        sa.Column("status", ingestion_run_status, nullable=False, server_default="pending"),
        sa.Column("requested_by", sa.String(length=120), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingestion_run_status", "ingestion_run", ["status"])
    op.create_index("ix_ingestion_run_trace_id", "ingestion_run", ["trace_id"])

    op.create_table(
        "ingestion_run_item",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("ingestion_run_id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("status", ingestion_run_item_status, nullable=False, server_default="pending"),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetch_etag", sa.String(length=120), nullable=True),
        sa.Column("fetch_last_modified", sa.String(length=120), nullable=True),
        sa.Column("raw_hash_sha256", sa.String(length=64), nullable=True),
        sa.Column("semantic_hash_sha256", sa.String(length=64), nullable=True),
        sa.Column("parser_used", sa.String(length=64), nullable=True),
        sa.Column(
            "parser_mode", ingestion_parser_mode, nullable=False, server_default="deterministic"
        ),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column(
            "manual_review_required", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "diff_summary_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=EMPTY_JSONB,
        ),
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
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["ingestion_run.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["source_registry.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ingestion_run_id", "source_id", name="uq_ingestion_run_item_source_once"
        ),
    )
    op.create_index(
        "ix_ingestion_run_item_ingestion_run_id", "ingestion_run_item", ["ingestion_run_id"]
    )
    op.create_index("ix_ingestion_run_item_source_id", "ingestion_run_item", ["source_id"])
    op.create_index("ix_ingestion_run_item_status", "ingestion_run_item", ["status"])
    op.create_index(
        "ix_ingestion_run_item_raw_hash_sha256", "ingestion_run_item", ["raw_hash_sha256"]
    )
    op.create_index(
        "ix_ingestion_run_item_semantic_hash_sha256",
        "ingestion_run_item",
        ["semantic_hash_sha256"],
    )

    op.create_table(
        "bronze_document",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("ingestion_run_item_id", sa.UUID(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("content_length", sa.Integer(), nullable=True),
        sa.Column(
            "storage_bucket",
            sa.String(length=120),
            nullable=False,
            server_default="immigration-bronze",
        ),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("storage_uri", sa.Text(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["ingestion_run_item_id"], ["ingestion_run_item.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["source_id"], ["source_registry.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ingestion_run_item_id", name="uq_bronze_document_run_item"),
    )
    op.create_index("ix_bronze_document_source_id", "bronze_document", ["source_id"])
    op.create_index("ix_bronze_document_checksum_sha256", "bronze_document", ["checksum_sha256"])

    op.create_table(
        "silver_section",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("ingestion_run_item_id", sa.UUID(), nullable=False),
        sa.Column("section_key", sa.String(length=64), nullable=False),
        sa.Column("heading", sa.String(length=255), nullable=True),
        sa.Column("section_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column("semantic_hash_sha256", sa.String(length=64), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["ingestion_run_item_id"], ["ingestion_run_item.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ingestion_run_item_id", "section_key", name="uq_silver_section_item_key"
        ),
    )
    op.create_index(
        "ix_silver_section_ingestion_run_item_id", "silver_section", ["ingestion_run_item_id"]
    )
    op.create_index(
        "ix_silver_section_semantic_hash_sha256", "silver_section", ["semantic_hash_sha256"]
    )

    op.add_column("source_documents", sa.Column("source_id", sa.UUID(), nullable=True))
    op.add_column("source_documents", sa.Column("ingestion_run_item_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_source_documents_source_id",
        "source_documents",
        "source_registry",
        ["source_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_source_documents_ingestion_run_item_id",
        "source_documents",
        "ingestion_run_item",
        ["ingestion_run_item_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_source_documents_source_id", "source_documents", ["source_id"])
    op.create_index(
        "ix_source_documents_ingestion_run_item_id",
        "source_documents",
        ["ingestion_run_item_id"],
    )

    op.add_column(
        "source_extractions", sa.Column("parser_used", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "source_extractions",
        sa.Column(
            "parser_mode", ingestion_parser_mode, nullable=False, server_default="deterministic"
        ),
    )
    op.add_column(
        "source_extractions",
        sa.Column(
            "manual_review_required", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    op.add_column(
        "source_extractions", sa.Column("semantic_hash_sha256", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "source_extractions",
        sa.Column(
            "extraction_metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index(
        "ix_source_extractions_semantic_hash_sha256", "source_extractions", ["semantic_hash_sha256"]
    )

    _apply_rls_policies()


def downgrade() -> None:
    _drop_rls_policies()

    op.drop_index("ix_source_extractions_semantic_hash_sha256", table_name="source_extractions")
    op.drop_column("source_extractions", "extraction_metadata_json")
    op.drop_column("source_extractions", "semantic_hash_sha256")
    op.drop_column("source_extractions", "manual_review_required")
    op.drop_column("source_extractions", "parser_mode")
    op.drop_column("source_extractions", "parser_used")

    op.drop_index("ix_source_documents_ingestion_run_item_id", table_name="source_documents")
    op.drop_index("ix_source_documents_source_id", table_name="source_documents")
    op.drop_constraint(
        "fk_source_documents_ingestion_run_item_id", "source_documents", type_="foreignkey"
    )
    op.drop_constraint("fk_source_documents_source_id", "source_documents", type_="foreignkey")
    op.drop_column("source_documents", "ingestion_run_item_id")
    op.drop_column("source_documents", "source_id")

    op.drop_index("ix_silver_section_semantic_hash_sha256", table_name="silver_section")
    op.drop_index("ix_silver_section_ingestion_run_item_id", table_name="silver_section")
    op.drop_table("silver_section")

    op.drop_index("ix_bronze_document_checksum_sha256", table_name="bronze_document")
    op.drop_index("ix_bronze_document_source_id", table_name="bronze_document")
    op.drop_table("bronze_document")

    op.drop_index("ix_ingestion_run_item_semantic_hash_sha256", table_name="ingestion_run_item")
    op.drop_index("ix_ingestion_run_item_raw_hash_sha256", table_name="ingestion_run_item")
    op.drop_index("ix_ingestion_run_item_status", table_name="ingestion_run_item")
    op.drop_index("ix_ingestion_run_item_source_id", table_name="ingestion_run_item")
    op.drop_index("ix_ingestion_run_item_ingestion_run_id", table_name="ingestion_run_item")
    op.drop_table("ingestion_run_item")

    op.drop_index("ix_ingestion_run_trace_id", table_name="ingestion_run")
    op.drop_index("ix_ingestion_run_status", table_name="ingestion_run")
    op.drop_table("ingestion_run")

    op.drop_index("ix_source_registry_program_code", table_name="source_registry")
    op.drop_index("ix_source_registry_country_code", table_name="source_registry")
    op.drop_index("ix_source_registry_source_key", table_name="source_registry")
    op.drop_table("source_registry")

    ingestion_parser_mode.drop(op.get_bind(), checkfirst=True)
    ingestion_run_item_status.drop(op.get_bind(), checkfirst=True)
    ingestion_run_status.drop(op.get_bind(), checkfirst=True)
    ingestion_run_trigger.drop(op.get_bind(), checkfirst=True)
    source_type.drop(op.get_bind(), checkfirst=True)


def _apply_rls_policies() -> None:
    # Exposed app tables with permissive app policy (compatible with local dev and Supabase).
    exposed_tables = [
        "countries",
        "immigration_programs",
        "program_versions",
        "rule_groups",
        "rule_conditions",
        "rule_outcomes",
    ]
    for table in exposed_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_policies
                    WHERE schemaname = 'public'
                    AND tablename = '{table}'
                    AND policyname = '{table}_app_rw'
                ) THEN
                    EXECUTE 'CREATE POLICY {table}_app_rw ON {table}
                    FOR ALL USING (true) WITH CHECK (true)';
                END IF;
            END $$;
            """)

    # Internal ingestion tables: deny by default for non-owner roles.
    internal_tables = [
        "source_registry",
        "ingestion_run",
        "ingestion_run_item",
        "bronze_document",
        "silver_section",
    ]
    for table in internal_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_policies
                    WHERE schemaname = 'public'
                    AND tablename = '{table}'
                    AND policyname = '{table}_internal_block'
                ) THEN
                    EXECUTE 'CREATE POLICY {table}_internal_block ON {table}
                    FOR ALL USING (false) WITH CHECK (false)';
                END IF;
            END $$;
            """)


def _drop_rls_policies() -> None:
    tables = [
        "countries",
        "immigration_programs",
        "program_versions",
        "rule_groups",
        "rule_conditions",
        "rule_outcomes",
        "source_registry",
        "ingestion_run",
        "ingestion_run_item",
        "bronze_document",
        "silver_section",
    ]
    for table in tables:
        op.execute(f"DROP POLICY IF EXISTS {table}_app_rw ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_internal_block ON {table}")
