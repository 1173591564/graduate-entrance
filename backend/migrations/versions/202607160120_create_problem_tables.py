"""create problem bank tables

Revision ID: 202607160120
Revises: b99f405ccfb2
Create Date: 2026-07-16 01:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607160120"
down_revision: str | Sequence[str] | None = "b99f405ccfb2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "problems",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("images", sa.JSON(), nullable=False),
        sa.Column("source_ref", sa.String(length=240), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("my_answer_md", sa.Text(), nullable=False),
        sa.Column("cause", sa.String(length=32), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("ef", sa.Float(), nullable=False),
        sa.Column("interval_days", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("reps", sa.Integer(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('wrong', 'hard', 'good')", name="ck_problems_kind"),
        sa.CheckConstraint(
            "cause IN ('', 'concept', 'calculation', 'method', 'memory', 'misread', 'other')",
            name="ck_problems_cause",
        ),
        sa.CheckConstraint("status IN ('draft', 'confirmed')", name="ck_problems_status"),
        sa.CheckConstraint("ef >= 1.3", name="ck_problems_ef"),
        sa.CheckConstraint("interval_days >= 0", name="ck_problems_interval_days"),
        sa.CheckConstraint("reps >= 0", name="ck_problems_reps"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_problems_due_date"), "problems", ["due_date"], unique=False)
    op.create_index(op.f("ix_problems_status"), "problems", ["status"], unique=False)
    op.create_index(op.f("ix_problems_subject_id"), "problems", ["subject_id"], unique=False)
    op.create_table(
        "solutions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("problem_id", sa.Uuid(), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("method_tag", sa.String(length=80), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("source IN ('self', 'answer', 'gpt')", name="ck_solutions_source"),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_solutions_problem_id"), "solutions", ["problem_id"], unique=False)
    op.create_table(
        "problem_knowledge_points",
        sa.Column("problem_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_point_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.CheckConstraint(
            "role IN ('primary', 'secondary')",
            name="ck_problem_knowledge_points_role",
        ),
        sa.CheckConstraint(
            "weight > 0 AND weight <= 1",
            name="ck_problem_knowledge_points_weight",
        ),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["knowledge_point_id"], ["knowledge_points.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("problem_id", "knowledge_point_id"),
    )
    op.create_index(
        op.f("ix_problem_knowledge_points_knowledge_point_id"),
        "problem_knowledge_points",
        ["knowledge_point_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_problem_knowledge_points_knowledge_point_id"),
        table_name="problem_knowledge_points",
    )
    op.drop_table("problem_knowledge_points")
    op.drop_index(op.f("ix_solutions_problem_id"), table_name="solutions")
    op.drop_table("solutions")
    op.drop_index(op.f("ix_problems_subject_id"), table_name="problems")
    op.drop_index(op.f("ix_problems_status"), table_name="problems")
    op.drop_index(op.f("ix_problems_due_date"), table_name="problems")
    op.drop_table("problems")
