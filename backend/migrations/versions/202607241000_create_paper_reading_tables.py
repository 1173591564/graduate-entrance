"""create paper content and annotation tables

Revision ID: 202607241000
Revises: 202607240900
Create Date: 2026-07-24 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607241000"
down_revision: str | Sequence[str] | None = "202607240900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "paper_contents",
        sa.Column("paper_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("blocks", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("paper_id"),
    )
    op.create_table(
        "paper_annotations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("paper_id", sa.Uuid(), nullable=False),
        sa.Column("block_index", sa.Integer(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("color", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "block_index >= 0",
            name="ck_paper_annotations_block_index",
        ),
        sa.CheckConstraint(
            "color in ('yellow', 'green', 'blue', 'red')",
            name="ck_paper_annotations_color",
        ),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_paper_annotations_paper_id"),
        "paper_annotations",
        ["paper_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_paper_annotations_paper_id"),
        table_name="paper_annotations",
    )
    op.drop_table("paper_annotations")
    op.drop_table("paper_contents")
