"""create planning configuration tables

Revision ID: 202607150702
Revises: 202607150501
Create Date: 2026-07-15 07:02:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607150702"
down_revision: str | Sequence[str] | None = "202607150501"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plan_phases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("milestones", sa.JSON(), nullable=False),
        sa.Column("allow_new_tasks", sa.Boolean(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("start_date <= end_date", name="ck_plan_phases_date_range"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_plan_phases_name"),
    )
    op.create_table(
        "availability_periods",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("weekly_target_minutes", sa.Integer(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "start_date <= end_date",
            name="ck_availability_periods_date_range",
        ),
        sa.CheckConstraint(
            "weekly_target_minutes >= 0",
            name="ck_availability_periods_weekly_target",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_availability_periods_name"),
    )
    op.create_table(
        "availability_exceptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("available_minutes", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=240), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "available_minutes >= 0 AND available_minutes <= 1440",
            name="ck_availability_exceptions_minutes",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("date", name="uq_availability_exceptions_date"),
    )
    op.create_table(
        "materials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("material_type", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "material_type IN "
            "('textbook', 'exercise_book', 'past_paper', 'course', 'vocabulary', 'other')",
            name="ck_materials_type",
        ),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_materials_subject_id"), "materials", ["subject_id"], unique=False)
    op.create_table(
        "plan_phase_subject_ratios",
        sa.Column("phase_id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("percentage", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "percentage >= 0 AND percentage <= 100",
            name="ck_plan_phase_subject_ratios_percentage",
        ),
        sa.ForeignKeyConstraint(["phase_id"], ["plan_phases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("phase_id", "subject_id"),
    )
    op.create_table(
        "availability_rules",
        sa.Column("period_id", sa.Uuid(), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("available_minutes", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "available_minutes >= 0 AND available_minutes <= 1440",
            name="ck_availability_rules_minutes",
        ),
        sa.CheckConstraint(
            "weekday >= 0 AND weekday <= 6",
            name="ck_availability_rules_weekday",
        ),
        sa.ForeignKeyConstraint(
            ["period_id"],
            ["availability_periods.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("period_id", "weekday"),
    )
    op.create_table(
        "task_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("material_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("task_type", sa.String(length=32), nullable=False),
        sa.Column("default_est_minutes", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "default_est_minutes > 0",
            name="ck_task_templates_est_minutes",
        ),
        sa.CheckConstraint(
            "task_type IN "
            "('reading', 'practice', 'dictation', 'past_paper', 'memorization', 'review')",
            name="ck_task_templates_type",
        ),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_task_templates_material_id"),
        "task_templates",
        ["material_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_task_templates_subject_id"),
        "task_templates",
        ["subject_id"],
        unique=False,
    )
    op.create_table(
        "task_template_phases",
        sa.Column("task_template_id", sa.Uuid(), nullable=False),
        sa.Column("phase_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["phase_id"], ["plan_phases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["task_template_id"],
            ["task_templates.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("task_template_id", "phase_id"),
    )


def downgrade() -> None:
    op.drop_table("task_template_phases")
    op.drop_index(op.f("ix_task_templates_subject_id"), table_name="task_templates")
    op.drop_index(op.f("ix_task_templates_material_id"), table_name="task_templates")
    op.drop_table("task_templates")
    op.drop_table("availability_rules")
    op.drop_table("plan_phase_subject_ratios")
    op.drop_index(op.f("ix_materials_subject_id"), table_name="materials")
    op.drop_table("materials")
    op.drop_table("availability_exceptions")
    op.drop_table("availability_periods")
    op.drop_table("plan_phases")
