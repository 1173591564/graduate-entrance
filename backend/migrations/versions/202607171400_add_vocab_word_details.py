"""add vocab word details

Revision ID: 202607171400
Revises: 202607171100
Create Date: 2026-07-17 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607171400"
down_revision: str | Sequence[str] | None = "202607171100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "vocab_words",
        sa.Column("phonetic", sa.String(120), nullable=False, server_default=""),
    )
    op.add_column(
        "vocab_words",
        sa.Column("example_en", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "vocab_words",
        sa.Column("example_zh", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("vocab_words", "example_zh")
    op.drop_column("vocab_words", "example_en")
    op.drop_column("vocab_words", "phonetic")
