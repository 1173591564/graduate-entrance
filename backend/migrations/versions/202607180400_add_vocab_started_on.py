"""add vocab word started_on

Revision ID: 202607180400
Revises: 202607171500
Create Date: 2026-07-18 04:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607180400"
down_revision: str | Sequence[str] | None = "202607171500"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "vocab_words",
        sa.Column("started_on", sa.Date(), nullable=True),
    )
    op.create_index(
        "ix_vocab_words_started_on", "vocab_words", ["started_on"]
    )


def downgrade() -> None:
    op.drop_index("ix_vocab_words_started_on", table_name="vocab_words")
    op.drop_column("vocab_words", "started_on")
