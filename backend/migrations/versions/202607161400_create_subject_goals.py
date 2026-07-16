"""create subject goals

Revision ID: 202607161400
Revises: 202607161200
Create Date: 2026-07-16 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607161400"
down_revision: str | Sequence[str] | None = "202607161200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "subject_goals",
        sa.Column(
            "subject_id",
            sa.Uuid(),
            sa.ForeignKey("subjects.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("target_score", sa.Integer(), nullable=False),
        sa.Column("full_score", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("full_score > 0", name="ck_subject_goals_full_score"),
        sa.CheckConstraint(
            "target_score >= 0 AND target_score <= full_score",
            name="ck_subject_goals_target_score",
        ),
    )


def downgrade() -> None:
    op.drop_table("subject_goals")
