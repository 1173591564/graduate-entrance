"""add materials.module_id for module-scoped material binding

Revision ID: 202607200600
Revises: 202607200500
Create Date: 2026-07-20 06:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607200600"
down_revision: str | Sequence[str] | None = "202607200500"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "materials",
        sa.Column("module_id", sa.Uuid(), nullable=True),
    )
    op.create_index("ix_materials_module_id", "materials", ["module_id"])
    op.create_foreign_key(
        "fk_materials_module_id_syllabus_modules",
        "materials",
        "syllabus_modules",
        ["module_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_materials_module_id_syllabus_modules", "materials", type_="foreignkey"
    )
    op.drop_index("ix_materials_module_id", table_name="materials")
    op.drop_column("materials", "module_id")
