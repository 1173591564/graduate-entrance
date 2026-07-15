from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from graduate_entrance.db.base import Base


class SyllabusVersion(Base):
    __tablename__ = "syllabus_versions"
    __table_args__ = (
        UniqueConstraint(
            "source_name",
            "source_checksum",
            name="uq_syllabus_versions_source_checksum",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(160))
    source_checksum: Mapped[str] = mapped_column(String(64))
    row_count: Mapped[int]
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    order: Mapped[int]

    modules: Mapped[list[SyllabusModule]] = relationship(
        back_populates="subject",
        cascade="all, delete-orphan",
        order_by="SyllabusModule.order",
    )


class SyllabusModule(Base):
    __tablename__ = "syllabus_modules"
    __table_args__ = (
        UniqueConstraint("subject_id", "name", name="uq_syllabus_modules_subject_name"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    subject_id: Mapped[UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    order: Mapped[int]

    subject: Mapped[Subject] = relationship(back_populates="modules")
    chapters: Mapped[list[Chapter]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="Chapter.order",
    )


class Chapter(Base):
    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("module_id", "name", name="uq_chapters_module_name"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    module_id: Mapped[UUID] = mapped_column(
        ForeignKey("syllabus_modules.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    order: Mapped[int]

    module: Mapped[SyllabusModule] = relationship(back_populates="chapters")
    sections: Mapped[list[Section]] = relationship(
        back_populates="chapter",
        cascade="all, delete-orphan",
        order_by="Section.order",
    )
    knowledge_points: Mapped[list[KnowledgePoint]] = relationship(
        back_populates="chapter",
        cascade="all, delete-orphan",
        order_by="KnowledgePoint.order",
    )


class Section(Base):
    __tablename__ = "sections"
    __table_args__ = (UniqueConstraint("chapter_id", "name", name="uq_sections_chapter_name"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    chapter_id: Mapped[UUID] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    order: Mapped[int]

    chapter: Mapped[Chapter] = relationship(back_populates="sections")
    knowledge_points: Mapped[list[KnowledgePoint]] = relationship(
        back_populates="section",
        order_by="KnowledgePoint.order",
    )


class KnowledgePoint(Base):
    __tablename__ = "knowledge_points"
    __table_args__ = (
        UniqueConstraint("chapter_id", "section_id", "name", name="uq_knowledge_points_path_name"),
        CheckConstraint(
            "requirement_level IN ('awareness', 'understanding', 'application', 'mastery')",
            name="ck_knowledge_points_requirement_level",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    chapter_id: Mapped[UUID] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), index=True
    )
    section_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("sections.id", ondelete="SET NULL"),
        index=True,
    )
    syllabus_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("syllabus_versions.id"), index=True
    )
    name: Mapped[str] = mapped_column(Text)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    requirement_raw: Mapped[str] = mapped_column(String(80))
    requirement_level: Mapped[str] = mapped_column(String(32))
    requirement_actions: Mapped[list[str]] = mapped_column(JSON)
    common_exam_style: Mapped[str] = mapped_column(Text, default="")
    note: Mapped[str] = mapped_column(Text, default="")
    weight: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    est_minutes: Mapped[int | None]
    order: Mapped[int]

    chapter: Mapped[Chapter] = relationship(back_populates="knowledge_points")
    section: Mapped[Section | None] = relationship(back_populates="knowledge_points")
    syllabus_version: Mapped[SyllabusVersion] = relationship()


class KnowledgeDependency(Base):
    __tablename__ = "knowledge_dependencies"
    __table_args__ = (
        CheckConstraint(
            "strength >= 0 AND strength <= 1", name="ck_knowledge_dependencies_strength"
        ),
    )

    predecessor_kp_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"),
        primary_key=True,
    )
    successor_kp_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"),
        primary_key=True,
    )
    dependency_type: Mapped[str] = mapped_column(String(40), default="prerequisite")
    strength: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=Decimal("1.0"))


class ExamBlueprint(Base):
    __tablename__ = "exam_blueprints"
    __table_args__ = (
        UniqueConstraint("subject_id", "name", name="uq_exam_blueprints_subject_name"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    subject_id: Mapped[UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), index=True
    )
    syllabus_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("syllabus_versions.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    total_score: Mapped[int | None]
    duration_minutes: Mapped[int | None]
    description: Mapped[str] = mapped_column(Text, default="")

    subject: Mapped[Subject] = relationship()
    sections: Mapped[list[ExamSection]] = relationship(
        back_populates="blueprint",
        cascade="all, delete-orphan",
        order_by="ExamSection.order",
    )


class ExamSection(Base):
    __tablename__ = "exam_sections"
    __table_args__ = (
        UniqueConstraint("blueprint_id", "name", name="uq_exam_sections_blueprint_name"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    blueprint_id: Mapped[UUID] = mapped_column(
        ForeignKey("exam_blueprints.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    score: Mapped[int | None]
    duration_minutes: Mapped[int | None]
    description: Mapped[str] = mapped_column(Text, default="")
    order: Mapped[int]

    blueprint: Mapped[ExamBlueprint] = relationship(back_populates="sections")
