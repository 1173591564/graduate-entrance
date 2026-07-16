"""add ai grading columns to problems

Revision ID: 202607161200
Revises: 202607161030
Create Date: 2026-07-16 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607161200"
down_revision: str | Sequence[str] | None = "202607161030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("problems", sa.Column("ai_score", sa.Float(), nullable=True))
    op.add_column(
        "problems",
        sa.Column("ai_feedback_md", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "problems",
        sa.Column("ai_graded_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("problems", "ai_graded_at")
    op.drop_column("problems", "ai_feedback_md")
    op.drop_column("problems", "ai_score")
