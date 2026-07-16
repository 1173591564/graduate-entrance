"""create ai week plans table

Revision ID: 202607160830
Revises: 202607160730
Create Date: 2026-07-16 08:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607160830"
down_revision: str | Sequence[str] | None = "202607160730"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_week_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("daily_focus", sa.JSON(), nullable=False),
        sa.Column("review_suggestions", sa.JSON(), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("week_start", name="uq_ai_week_plans_week_start"),
    )
    op.create_index(op.f("ix_ai_week_plans_week_start"), "ai_week_plans", ["week_start"])


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_week_plans_week_start"), table_name="ai_week_plans")
    op.drop_table("ai_week_plans")
