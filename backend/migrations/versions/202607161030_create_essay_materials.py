"""create essay materials table

Revision ID: 202607161030
Revises: 202607160830
Create Date: 2026-07-16 10:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607161030"
down_revision: str | Sequence[str] | None = "202607160830"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "essay_materials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("category", sa.String(length=16), nullable=False),
        sa.Column("topic", sa.String(length=120), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("translation_md", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=240), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("interval_days", sa.Integer(), nullable=False),
        sa.Column("recite_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "category IN ('phrase', 'sentence', 'paragraph', 'template', 'quote')",
            name="ck_essay_materials_category",
        ),
        sa.CheckConstraint("interval_days >= 0", name="ck_essay_materials_interval_days"),
        sa.CheckConstraint("recite_count >= 0", name="ck_essay_materials_recite_count"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_essay_materials_category"), "essay_materials", ["category"])
    op.create_index(op.f("ix_essay_materials_topic"), "essay_materials", ["topic"])
    op.create_index(op.f("ix_essay_materials_due_date"), "essay_materials", ["due_date"])


def downgrade() -> None:
    op.drop_index(op.f("ix_essay_materials_due_date"), table_name="essay_materials")
    op.drop_index(op.f("ix_essay_materials_topic"), table_name="essay_materials")
    op.drop_index(op.f("ix_essay_materials_category"), table_name="essay_materials")
    op.drop_table("essay_materials")
