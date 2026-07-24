"""add srs fields to recitation items

Revision ID: 202607240900
Revises: 202607231500
Create Date: 2026-07-24 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607240900"
down_revision: str | Sequence[str] | None = "202607231500"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "recitation_items",
        sa.Column("ef", sa.Float(), nullable=False, server_default="2.5"),
    )
    op.add_column(
        "recitation_items",
        sa.Column("interval_days", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "recitation_items",
        sa.Column("reps", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "recitation_items",
        sa.Column("due_date", sa.Date(), nullable=True),
    )
    op.create_index(
        op.f("ix_recitation_items_due_date"),
        "recitation_items",
        ["due_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_recitation_items_due_date"), table_name="recitation_items")
    op.drop_column("recitation_items", "due_date")
    op.drop_column("recitation_items", "reps")
    op.drop_column("recitation_items", "interval_days")
    op.drop_column("recitation_items", "ef")
