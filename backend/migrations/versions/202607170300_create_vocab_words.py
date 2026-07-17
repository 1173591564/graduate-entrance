"""create vocab words

Revision ID: 202607170300
Revises: 202607170001
Create Date: 2026-07-17 03:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607170300"
down_revision: str | Sequence[str] | None = "202607170001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vocab_words",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("word", sa.String(80), nullable=False),
        sa.Column("meaning", sa.Text(), nullable=False, server_default=""),
        sa.Column("book_page", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ef", sa.Float(), nullable=False, server_default="2.5"),
        sa.Column("interval_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("reps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_reviewed_on", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("ef >= 1.3", name="ck_vocab_words_ef"),
        sa.CheckConstraint("interval_days >= 0", name="ck_vocab_words_interval_days"),
        sa.CheckConstraint("reps >= 0", name="ck_vocab_words_reps"),
    )
    op.create_index("ix_vocab_words_word", "vocab_words", ["word"], unique=True)
    op.create_index("ix_vocab_words_order_index", "vocab_words", ["order_index"])
    op.create_index("ix_vocab_words_due_date", "vocab_words", ["due_date"])


def downgrade() -> None:
    op.drop_index("ix_vocab_words_due_date", table_name="vocab_words")
    op.drop_index("ix_vocab_words_order_index", table_name="vocab_words")
    op.drop_index("ix_vocab_words_word", table_name="vocab_words")
    op.drop_table("vocab_words")
