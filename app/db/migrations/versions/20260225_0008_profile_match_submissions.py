"""profile match submissions

Revision ID: 20260225_0008
Revises: 20260225_0007
Create Date: 2026-02-25 16:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260225_0008"
down_revision: str | None = "20260225_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "profile_match_submissions",
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("guest_session_id", sa.String(length=64), nullable=False),
        sa.Column("algorithm_version", sa.String(length=32), nullable=False),
        sa.Column("profile_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_profile_match_submissions_guest_session_id"),
        "profile_match_submissions",
        ["guest_session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_profile_match_submissions_user_id"),
        "profile_match_submissions",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_profile_match_submissions_user_id"),
        table_name="profile_match_submissions",
    )
    op.drop_index(
        op.f("ix_profile_match_submissions_guest_session_id"),
        table_name="profile_match_submissions",
    )
    op.drop_table("profile_match_submissions")
