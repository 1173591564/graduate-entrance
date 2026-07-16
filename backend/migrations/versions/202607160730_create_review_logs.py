"""create review logs table

Revision ID: 202607160730
Revises: 202607160120
Create Date: 2026-07-16 07:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607160730"
down_revision: str | Sequence[str] | None = "202607160120"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "review_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("problem_id", sa.Uuid(), nullable=False),
        sa.Column("grade", sa.String(length=16), nullable=False),
        sa.Column("reviewed_on", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "grade IN ('forgot', 'vague', 'mastered')",
            name="ck_review_logs_grade",
        ),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_review_logs_problem_id"), "review_logs", ["problem_id"], unique=False)
    op.create_index(
        op.f("ix_review_logs_reviewed_on"), "review_logs", ["reviewed_on"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_review_logs_reviewed_on"), table_name="review_logs")
    op.drop_index(op.f("ix_review_logs_problem_id"), table_name="review_logs")
    op.drop_table("review_logs")
