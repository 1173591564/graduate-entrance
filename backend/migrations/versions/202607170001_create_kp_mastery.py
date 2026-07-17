"""create kp mastery

Revision ID: 202607170001
Revises: 202607161500
Create Date: 2026-07-17 00:01:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607170001"
down_revision: str | Sequence[str] | None = "202607161500"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "kp_mastery",
        sa.Column(
            "knowledge_point_id",
            sa.Uuid(),
            sa.ForeignKey("knowledge_points.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "subject_id",
            sa.Uuid(),
            sa.ForeignKey("subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("mastery", sa.Numeric(5, 1), nullable=False, server_default="0"),
        sa.Column("target", sa.Numeric(5, 1), nullable=False, server_default="0"),
        sa.Column("studied", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_signal_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("mastery >= 0 AND mastery <= 100", name="ck_kp_mastery_mastery"),
        sa.CheckConstraint("target >= 0 AND target <= 100", name="ck_kp_mastery_target"),
    )
    op.create_index("ix_kp_mastery_subject_id", "kp_mastery", ["subject_id"])


def downgrade() -> None:
    op.drop_index("ix_kp_mastery_subject_id", table_name="kp_mastery")
    op.drop_table("kp_mastery")
