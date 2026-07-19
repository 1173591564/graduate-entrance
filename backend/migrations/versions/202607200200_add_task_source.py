"""add scheduled task source

Revision ID: 202607200200
Revises: 202607200100
Create Date: 2026-07-20 02:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607200200"
down_revision: str | Sequence[str] | None = "202607200100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scheduled_tasks",
        sa.Column(
            "source",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'plan'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("scheduled_tasks", "source")
