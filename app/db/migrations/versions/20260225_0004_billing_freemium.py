"""billing freemium foundation

Revision ID: 20260225_0004
Revises: 20260225_0003
Create Date: 2026-02-25 01:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260225_0004"
down_revision: str | None = "20260225_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


billing_provider = postgresql.ENUM("stripe", name="billing_provider", create_type=False)
billing_event_status = postgresql.ENUM(
    "received", "processed", "ignored", "failed", name="billing_event_status", create_type=False
)


def upgrade() -> None:
    billing_provider.create(op.get_bind(), checkfirst=True)
    billing_event_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "plans", sa.Column("provider", billing_provider, nullable=False, server_default="stripe")
    )
    op.add_column("plans", sa.Column("stripe_price_id", sa.String(length=120), nullable=True))
    op.add_column("plans", sa.Column("stripe_product_id", sa.String(length=120), nullable=True))
    op.add_column(
        "plans", sa.Column("is_free", sa.Boolean(), nullable=False, server_default=sa.text("false"))
    )
    op.create_index("ix_plans_stripe_price_id", "plans", ["stripe_price_id"], unique=True)

    op.add_column(
        "subscriptions",
        sa.Column("provider", billing_provider, nullable=False, server_default="stripe"),
    )
    op.add_column(
        "subscriptions", sa.Column("provider_customer_id", sa.String(length=120), nullable=True)
    )
    op.add_column(
        "subscriptions",
        sa.Column("provider_subscription_id", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column(
            "cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    op.create_index(
        "ix_subscriptions_provider_subscription_id",
        "subscriptions",
        ["provider_subscription_id"],
        unique=True,
    )
    op.create_index(
        "ix_subscriptions_provider_customer_id",
        "subscriptions",
        ["provider_customer_id"],
    )

    op.create_table(
        "usage_counters",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("feature_key", sa.String(length=64), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "feature_key",
            "window_start",
            name="uq_usage_counters_user_feature_window_start",
        ),
    )
    op.create_index("ix_usage_counters_user_id", "usage_counters", ["user_id"])

    op.create_table(
        "billing_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("provider", billing_provider, nullable=False),
        sa.Column("provider_event_id", sa.String(length=120), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("status", billing_event_status, nullable=False, server_default="received"),
        sa.Column(
            "payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "provider_event_id",
            name="uq_billing_events_provider_event_id",
        ),
    )
    op.create_index("ix_billing_events_provider", "billing_events", ["provider"])
    op.create_index("ix_billing_events_status", "billing_events", ["status"])


def downgrade() -> None:
    op.drop_index("ix_billing_events_status", table_name="billing_events")
    op.drop_index("ix_billing_events_provider", table_name="billing_events")
    op.drop_table("billing_events")

    op.drop_index("ix_usage_counters_user_id", table_name="usage_counters")
    op.drop_table("usage_counters")

    op.drop_index("ix_subscriptions_provider_customer_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_provider_subscription_id", table_name="subscriptions")
    op.drop_column("subscriptions", "cancel_at_period_end")
    op.drop_column("subscriptions", "provider_subscription_id")
    op.drop_column("subscriptions", "provider_customer_id")
    op.drop_column("subscriptions", "provider")

    op.drop_index("ix_plans_stripe_price_id", table_name="plans")
    op.drop_column("plans", "is_free")
    op.drop_column("plans", "stripe_product_id")
    op.drop_column("plans", "stripe_price_id")
    op.drop_column("plans", "provider")

    billing_event_status.drop(op.get_bind(), checkfirst=True)
    billing_provider.drop(op.get_bind(), checkfirst=True)
