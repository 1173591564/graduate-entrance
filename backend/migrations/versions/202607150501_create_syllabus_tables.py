"""create syllabus tables

Revision ID: 202607150501
Revises:
Create Date: 2026-07-15 05:01:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607150501"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "syllabus_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_name", sa.String(length=160), nullable=False),
        sa.Column("source_checksum", sa.String(length=64), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_name",
            "source_checksum",
            name="uq_syllabus_versions_source_checksum",
        ),
    )
    op.create_table(
        "subjects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "syllabus_modules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        sa.UniqueConstraint("subject_id", "name", name="uq_syllabus_modules_subject_name"),
    )
    op.create_index(
        op.f("ix_syllabus_modules_subject_id"),
        "syllabus_modules",
        ["subject_id"],
        unique=False,
    )
    op.create_table(
        "exam_blueprints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("syllabus_version_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["syllabus_version_id"], ["syllabus_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        sa.UniqueConstraint("subject_id", "name", name="uq_exam_blueprints_subject_name"),
    )
    op.create_index(
        op.f("ix_exam_blueprints_subject_id"),
        "exam_blueprints",
        ["subject_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_exam_blueprints_syllabus_version_id"),
        "exam_blueprints",
        ["syllabus_version_id"],
        unique=False,
    )
    op.create_table(
        "chapters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("module_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["module_id"], ["syllabus_modules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        sa.UniqueConstraint("module_id", "name", name="uq_chapters_module_name"),
    )
    op.create_index(op.f("ix_chapters_module_id"), "chapters", ["module_id"], unique=False)
    op.create_table(
        "exam_sections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("blueprint_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["blueprint_id"], ["exam_blueprints.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("blueprint_id", "name", name="uq_exam_sections_blueprint_name"),
    )
    op.create_index(
        op.f("ix_exam_sections_blueprint_id"),
        "exam_sections",
        ["blueprint_id"],
        unique=False,
    )
    op.create_table(
        "sections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chapter_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        sa.UniqueConstraint("chapter_id", "name", name="uq_sections_chapter_name"),
    )
    op.create_index(op.f("ix_sections_chapter_id"), "sections", ["chapter_id"], unique=False)
    op.create_table(
        "knowledge_points",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chapter_id", sa.Uuid(), nullable=False),
        sa.Column("section_id", sa.Uuid(), nullable=True),
        sa.Column("syllabus_version_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("requirement_raw", sa.String(length=80), nullable=False),
        sa.Column("requirement_level", sa.String(length=32), nullable=False),
        sa.Column("requirement_actions", sa.JSON(), nullable=False),
        sa.Column("common_exam_style", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("weight", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("est_minutes", sa.Integer(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "requirement_level IN ('awareness', 'understanding', 'application', 'mastery')",
            name="ck_knowledge_points_requirement_level",
        ),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["syllabus_version_id"], ["syllabus_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        sa.UniqueConstraint(
            "chapter_id", "section_id", "name", name="uq_knowledge_points_path_name"
        ),
    )
    op.create_index(
        op.f("ix_knowledge_points_chapter_id"), "knowledge_points", ["chapter_id"], unique=False
    )
    op.create_index(
        op.f("ix_knowledge_points_section_id"), "knowledge_points", ["section_id"], unique=False
    )
    op.create_index(
        op.f("ix_knowledge_points_syllabus_version_id"),
        "knowledge_points",
        ["syllabus_version_id"],
        unique=False,
    )
    op.create_table(
        "knowledge_dependencies",
        sa.Column("predecessor_kp_id", sa.Uuid(), nullable=False),
        sa.Column("successor_kp_id", sa.Uuid(), nullable=False),
        sa.Column("dependency_type", sa.String(length=40), nullable=False),
        sa.Column("strength", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.CheckConstraint(
            "strength >= 0 AND strength <= 1", name="ck_knowledge_dependencies_strength"
        ),
        sa.ForeignKeyConstraint(["predecessor_kp_id"], ["knowledge_points.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["successor_kp_id"], ["knowledge_points.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("predecessor_kp_id", "successor_kp_id"),
    )


def downgrade() -> None:
    op.drop_table("knowledge_dependencies")
    op.drop_index(op.f("ix_knowledge_points_syllabus_version_id"), table_name="knowledge_points")
    op.drop_index(op.f("ix_knowledge_points_section_id"), table_name="knowledge_points")
    op.drop_index(op.f("ix_knowledge_points_chapter_id"), table_name="knowledge_points")
    op.drop_table("knowledge_points")
    op.drop_index(op.f("ix_sections_chapter_id"), table_name="sections")
    op.drop_table("sections")
    op.drop_index(op.f("ix_exam_sections_blueprint_id"), table_name="exam_sections")
    op.drop_table("exam_sections")
    op.drop_index(op.f("ix_chapters_module_id"), table_name="chapters")
    op.drop_table("chapters")
    op.drop_index(op.f("ix_exam_blueprints_syllabus_version_id"), table_name="exam_blueprints")
    op.drop_index(op.f("ix_exam_blueprints_subject_id"), table_name="exam_blueprints")
    op.drop_table("exam_blueprints")
    op.drop_index(op.f("ix_syllabus_modules_subject_id"), table_name="syllabus_modules")
    op.drop_table("syllabus_modules")
    op.drop_table("subjects")
    op.drop_table("syllabus_versions")
