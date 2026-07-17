"""expand recitation subjects

Revision ID: 202607171500
Revises: 202607171400
Create Date: 2026-07-17 15:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "202607171500"
down_revision: str | Sequence[str] | None = "202607171400"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_recitation_subject", "recitation_items", type_="check")
    op.create_check_constraint(
        "ck_recitation_subject",
        "recitation_items",
        "subject in ('politics', 'english', 'math', 'cs408')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_recitation_subject", "recitation_items", type_="check")
    op.create_check_constraint(
        "ck_recitation_subject",
        "recitation_items",
        "subject in ('politics', 'english')",
    )
