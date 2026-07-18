"""add task template chapter scope

Revision ID: 202607180500
Revises: 202607180400
Create Date: 2026-07-18 05:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607180500"
down_revision: str | Sequence[str] | None = "202607180400"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "task_templates",
        sa.Column("chapter_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_task_templates_chapter_id", "task_templates", ["chapter_id"]
    )
    op.create_foreign_key(
        "fk_task_templates_chapter_id",
        "task_templates",
        "chapters",
        ["chapter_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_task_templates_chapter_id", "task_templates", type_="foreignkey"
    )
    op.drop_index("ix_task_templates_chapter_id", table_name="task_templates")
    op.drop_column("task_templates", "chapter_id")
