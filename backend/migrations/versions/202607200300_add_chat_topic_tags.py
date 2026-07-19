"""add chat topic tags

Revision ID: 202607200300
Revises: 202607200200
Create Date: 2026-07-20 03:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607200300"
down_revision: str | Sequence[str] | None = "202607200200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_topic_tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("subject", sa.String(length=80), nullable=False),
        sa.Column("topic", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["message_id"], ["chat_messages.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_topic_tags_message_id", "chat_topic_tags", ["message_id"])
    op.create_index("ix_chat_topic_tags_created_at", "chat_topic_tags", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_chat_topic_tags_created_at", table_name="chat_topic_tags")
    op.drop_index("ix_chat_topic_tags_message_id", table_name="chat_topic_tags")
    op.drop_table("chat_topic_tags")
