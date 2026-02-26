"""mvp country catalog seed support

Revision ID: 20260225_0007
Revises: 20260225_0006
Create Date: 2026-02-25 15:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260225_0007"
down_revision: str | None = "20260225_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("countries", sa.Column("priority_rank", sa.Integer(), nullable=True))
    op.add_column(
        "countries", sa.Column("diaspora_population_estimate", sa.Integer(), nullable=True)
    )
    op.add_column("countries", sa.Column("prioritization_source_url", sa.Text(), nullable=True))
    op.create_index("ix_countries_priority_rank", "countries", ["priority_rank"], unique=False)

    op.create_unique_constraint(
        "uq_source_documents_program_version_source_url",
        "source_documents",
        ["program_version_id", "source_url"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_source_documents_program_version_source_url",
        "source_documents",
        type_="unique",
    )

    op.drop_index("ix_countries_priority_rank", table_name="countries")
    op.drop_column("countries", "prioritization_source_url")
    op.drop_column("countries", "diaspora_population_estimate")
    op.drop_column("countries", "priority_rank")
