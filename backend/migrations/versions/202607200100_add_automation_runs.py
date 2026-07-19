"""add automation runs table and ai week plan status

Revision ID: 202607200100
Revises: 202607190100
Create Date: 2026-07-20 01:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607200100"
down_revision: str | Sequence[str] | None = "202607190100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "automation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_name", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_automation_runs_job_name", "automation_runs", ["job_name"]
    )
    op.create_index("ix_automation_runs_run_at", "automation_runs", ["run_at"])
    op.add_column(
        "ai_week_plans",
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'confirmed'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("ai_week_plans", "status")
    op.drop_index("ix_automation_runs_run_at", table_name="automation_runs")
    op.drop_index("ix_automation_runs_job_name", table_name="automation_runs")
    op.drop_table("automation_runs")
