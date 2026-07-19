"""add automation_runs.run_date and success dedup index

Revision ID: 202607200500
Revises: 202607200400
Create Date: 2026-07-20 05:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607200500"
down_revision: str | Sequence[str] | None = "202607200400"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "automation_runs",
        sa.Column("run_date", sa.Date(), nullable=True),
    )
    op.create_index(
        "ix_automation_runs_run_date", "automation_runs", ["run_date"]
    )
    op.create_index(
        "uq_automation_runs_success",
        "automation_runs",
        ["job_name", "run_date"],
        unique=True,
        postgresql_where=sa.text("status = 'success'"),
        sqlite_where=sa.text("status = 'success'"),
    )


def downgrade() -> None:
    op.drop_index("uq_automation_runs_success", table_name="automation_runs")
    op.drop_index("ix_automation_runs_run_date", table_name="automation_runs")
    op.drop_column("automation_runs", "run_date")
