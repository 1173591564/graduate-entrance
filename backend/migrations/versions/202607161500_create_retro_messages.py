"""create retro messages

Revision ID: 202607161500
Revises: 202607161400
Create Date: 2026-07-16 15:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607161500"
down_revision: str | Sequence[str] | None = "202607161400"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "retro_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_retro_messages_role"),
    )
    op.create_index("ix_retro_messages_week_start", "retro_messages", ["week_start"])


def downgrade() -> None:
    op.drop_index("ix_retro_messages_week_start", table_name="retro_messages")
    op.drop_table("retro_messages")
