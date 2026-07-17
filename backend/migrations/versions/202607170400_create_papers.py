"""create papers

Revision ID: 202607170400
Revises: 202607170300
Create Date: 2026-07-17 04:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607170400"
down_revision: str | Sequence[str] | None = "202607170300"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "papers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("rel_path", sa.String(500), nullable=False),
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
        sa.Column("category", sa.String(120), nullable=False, server_default=""),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="unread"),
        sa.Column("stored_filename", sa.String(80), nullable=True),
        sa.Column("started_on", sa.Date(), nullable=True),
        sa.Column("finished_on", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("size_bytes >= 0", name="ck_papers_size_bytes"),
        sa.CheckConstraint(
            "status in ('unread', 'reading', 'done')",
            name="ck_papers_status",
        ),
    )
    op.create_index("ix_papers_rel_path", "papers", ["rel_path"], unique=True)
    op.create_index("ix_papers_category", "papers", ["category"])
    op.create_index("ix_papers_order_index", "papers", ["order_index"])
    op.create_index("ix_papers_status", "papers", ["status"])


def downgrade() -> None:
    op.drop_index("ix_papers_status", table_name="papers")
    op.drop_index("ix_papers_order_index", table_name="papers")
    op.drop_index("ix_papers_category", table_name="papers")
    op.drop_index("ix_papers_rel_path", table_name="papers")
    op.drop_table("papers")
