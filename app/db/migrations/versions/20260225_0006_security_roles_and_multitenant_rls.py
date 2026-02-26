"""security hardening: user roles and multi-tenant rls

Revision ID: 20260225_0006
Revises: 20260225_0005
Create Date: 2026-02-25 12:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260225_0006"
down_revision: str | None = "20260225_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role = sa.Enum("member", "admin", name="user_role")


def upgrade() -> None:
    user_role.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "users",
        sa.Column("role", user_role, nullable=False, server_default="member"),
    )

    op.execute("""
        CREATE OR REPLACE FUNCTION app_current_user_id()
        RETURNS uuid
        LANGUAGE SQL
        STABLE
        AS $$
            SELECT NULLIF(
                COALESCE(
                    current_setting('app.current_user_id', true),
                    current_setting('request.jwt.claim.sub', true)
                ),
                ''
            )::uuid
        $$;
        """)
    op.execute("""
        CREATE OR REPLACE FUNCTION app_current_user_role()
        RETURNS text
        LANGUAGE SQL
        STABLE
        AS $$
            SELECT COALESCE(
                NULLIF(current_setting('app.current_user_role', true), ''),
                NULLIF(current_setting('request.jwt.claim.role', true), ''),
                'member'
            )
        $$;
        """)

    _enable_multitenant_rls()


def downgrade() -> None:
    _disable_multitenant_rls()
    op.execute("DROP FUNCTION IF EXISTS app_current_user_role()")
    op.execute("DROP FUNCTION IF EXISTS app_current_user_id()")
    op.drop_column("users", "role")
    user_role.drop(op.get_bind(), checkfirst=True)


def _enable_multitenant_rls() -> None:
    direct_owner_tables = [
        "user_profile_snapshots",
        "assessments",
        "roadmaps",
        "subscriptions",
        "entitlements",
        "usage_counters",
    ]
    for table in direct_owner_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            DROP POLICY IF EXISTS {table}_tenant_isolation ON {table};
            CREATE POLICY {table}_tenant_isolation ON {table}
            FOR ALL
            USING (app_current_user_role() = 'admin' OR user_id = app_current_user_id())
            WITH CHECK (app_current_user_role() = 'admin' OR user_id = app_current_user_id());
            """)

    op.execute("ALTER TABLE assessment_results ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE assessment_results FORCE ROW LEVEL SECURITY")
    op.execute("""
        DROP POLICY IF EXISTS assessment_results_tenant_isolation ON assessment_results;
        CREATE POLICY assessment_results_tenant_isolation ON assessment_results
        FOR ALL
        USING (
            app_current_user_role() = 'admin'
            OR EXISTS (
                SELECT 1
                FROM assessments a
                WHERE a.id = assessment_results.assessment_id
                AND a.user_id = app_current_user_id()
            )
        )
        WITH CHECK (
            app_current_user_role() = 'admin'
            OR EXISTS (
                SELECT 1
                FROM assessments a
                WHERE a.id = assessment_results.assessment_id
                AND a.user_id = app_current_user_id()
            )
        );
        """)

    op.execute("ALTER TABLE assessment_result_items ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE assessment_result_items FORCE ROW LEVEL SECURITY")
    op.execute("""
        DROP POLICY IF EXISTS assessment_result_items_tenant_isolation ON assessment_result_items;
        CREATE POLICY assessment_result_items_tenant_isolation ON assessment_result_items
        FOR ALL
        USING (
            app_current_user_role() = 'admin'
            OR EXISTS (
                SELECT 1
                FROM assessment_results ar
                JOIN assessments a ON a.id = ar.assessment_id
                WHERE ar.id = assessment_result_items.assessment_result_id
                AND a.user_id = app_current_user_id()
            )
        )
        WITH CHECK (
            app_current_user_role() = 'admin'
            OR EXISTS (
                SELECT 1
                FROM assessment_results ar
                JOIN assessments a ON a.id = ar.assessment_id
                WHERE ar.id = assessment_result_items.assessment_result_id
                AND a.user_id = app_current_user_id()
            )
        );
        """)

    op.execute("ALTER TABLE roadmap_steps ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE roadmap_steps FORCE ROW LEVEL SECURITY")
    op.execute("""
        DROP POLICY IF EXISTS roadmap_steps_tenant_isolation ON roadmap_steps;
        CREATE POLICY roadmap_steps_tenant_isolation ON roadmap_steps
        FOR ALL
        USING (
            app_current_user_role() = 'admin'
            OR EXISTS (
                SELECT 1
                FROM roadmaps r
                WHERE r.id = roadmap_steps.roadmap_id
                AND r.user_id = app_current_user_id()
            )
        )
        WITH CHECK (
            app_current_user_role() = 'admin'
            OR EXISTS (
                SELECT 1
                FROM roadmaps r
                WHERE r.id = roadmap_steps.roadmap_id
                AND r.user_id = app_current_user_id()
            )
        );
        """)

    op.execute("ALTER TABLE jobs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE jobs FORCE ROW LEVEL SECURITY")
    op.execute("""
        DROP POLICY IF EXISTS jobs_tenant_isolation ON jobs;
        CREATE POLICY jobs_tenant_isolation ON jobs
        FOR ALL
        USING (
            app_current_user_role() = 'admin'
            OR EXISTS (
                SELECT 1
                FROM assessments a
                WHERE a.id = jobs.assessment_id
                AND a.user_id = app_current_user_id()
            )
            OR EXISTS (
                SELECT 1
                FROM roadmaps r
                WHERE r.id = jobs.roadmap_id
                AND r.user_id = app_current_user_id()
            )
        )
        WITH CHECK (
            app_current_user_role() = 'admin'
            OR EXISTS (
                SELECT 1
                FROM assessments a
                WHERE a.id = jobs.assessment_id
                AND a.user_id = app_current_user_id()
            )
            OR EXISTS (
                SELECT 1
                FROM roadmaps r
                WHERE r.id = jobs.roadmap_id
                AND r.user_id = app_current_user_id()
            )
        );
        """)

    op.execute("ALTER TABLE billing_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE billing_events FORCE ROW LEVEL SECURITY")
    op.execute("""
        DROP POLICY IF EXISTS billing_events_internal_only ON billing_events;
        CREATE POLICY billing_events_internal_only ON billing_events
        FOR ALL
        USING (app_current_user_role() = 'admin')
        WITH CHECK (app_current_user_role() = 'admin');
        """)


def _disable_multitenant_rls() -> None:
    tables = [
        "user_profile_snapshots",
        "assessments",
        "roadmaps",
        "subscriptions",
        "entitlements",
        "usage_counters",
        "assessment_results",
        "assessment_result_items",
        "roadmap_steps",
        "jobs",
        "billing_events",
    ]
    policies = [
        "user_profile_snapshots_tenant_isolation",
        "assessments_tenant_isolation",
        "roadmaps_tenant_isolation",
        "subscriptions_tenant_isolation",
        "entitlements_tenant_isolation",
        "usage_counters_tenant_isolation",
        "assessment_results_tenant_isolation",
        "assessment_result_items_tenant_isolation",
        "roadmap_steps_tenant_isolation",
        "jobs_tenant_isolation",
        "billing_events_internal_only",
    ]
    for table, policy in zip(tables, policies, strict=False):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
