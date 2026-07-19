"""add chat conversation rolling summary

Revision ID: 202607200400
Revises: 202607200300
Create Date: 2026-07-20 04:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607200400"
down_revision: str | Sequence[str] | None = "202607200300"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chat_conversations",
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "chat_conversations",
        sa.Column("summary_upto_message_id", sa.Uuid(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_conversations", "summary_upto_message_id")
    op.drop_column("chat_conversations", "summary")
