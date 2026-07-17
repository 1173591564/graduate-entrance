"""create recitation items

Revision ID: 202607170700
Revises: 202607170400
Create Date: 2026-07-17 07:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607170700"
down_revision: str | Sequence[str] | None = "202607170400"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recitation_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("subject", sa.String(16), nullable=False),
        sa.Column("category", sa.String(120), nullable=False, server_default=""),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False, server_default=""),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recite_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_recited_on", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("subject", "title", name="uq_recitation_subject_title"),
        sa.CheckConstraint("recite_count >= 0", name="ck_recitation_recite_count"),
        sa.CheckConstraint(
            "subject in ('politics', 'english')",
            name="ck_recitation_subject",
        ),
    )
    op.create_index("ix_recitation_items_subject", "recitation_items", ["subject"])
    op.create_index("ix_recitation_items_category", "recitation_items", ["category"])
    op.create_index("ix_recitation_items_order_index", "recitation_items", ["order_index"])


def downgrade() -> None:
    op.drop_index("ix_recitation_items_order_index", table_name="recitation_items")
    op.drop_index("ix_recitation_items_category", table_name="recitation_items")
    op.drop_index("ix_recitation_items_subject", table_name="recitation_items")
    op.drop_table("recitation_items")
