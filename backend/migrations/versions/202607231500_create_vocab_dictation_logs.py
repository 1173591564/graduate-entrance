"""create vocab dictation logs table

Revision ID: 202607231500
Revises: 202607200600
Create Date: 2026-07-23 15:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607231500"
down_revision: str | Sequence[str] | None = "202607200600"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vocab_dictation_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dictated_on", sa.Date(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("correct", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("total >= 0", name="ck_vocab_dictation_logs_total"),
        sa.CheckConstraint(
            "correct >= 0 AND correct <= total",
            name="ck_vocab_dictation_logs_correct",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_vocab_dictation_logs_dictated_on"),
        "vocab_dictation_logs",
        ["dictated_on"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_vocab_dictation_logs_dictated_on"),
        table_name="vocab_dictation_logs",
    )
    op.drop_table("vocab_dictation_logs")
