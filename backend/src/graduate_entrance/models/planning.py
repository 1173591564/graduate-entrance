from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from graduate_entrance.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class PlanPhase(Base):
    __tablename__ = "plan_phases"
    __table_args__ = (
        UniqueConstraint("name", name="uq_plan_phases_name"),
        CheckConstraint("start_date <= end_date", name="ck_plan_phases_date_range"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(80))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(Text, default="")
    milestones: Mapped[list[str]] = mapped_column(JSON, default=list)
    allow_new_tasks: Mapped[bool] = mapped_column(Boolean, default=True)
    order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    subject_ratios: Mapped[list[PlanPhaseSubjectRatio]] = relationship(
        back_populates="phase",
        cascade="all, delete-orphan",
        order_by="PlanPhaseSubjectRatio.subject_id",
    )
    template_links: Mapped[list[TaskTemplatePhase]] = relationship(
        back_populates="phase",
        cascade="all, delete-orphan",
    )


class PlanPhaseSubjectRatio(Base):
    __tablename__ = "plan_phase_subject_ratios"
    __table_args__ = (
        CheckConstraint(
            "percentage >= 0 AND percentage <= 100",
            name="ck_plan_phase_subject_ratios_percentage",
        ),
    )

    phase_id: Mapped[UUID] = mapped_column(
        ForeignKey("plan_phases.id", ondelete="CASCADE"),
        primary_key=True,
    )
    subject_id: Mapped[UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    percentage: Mapped[int]

    phase: Mapped[PlanPhase] = relationship(back_populates="subject_ratios")


class AvailabilityPeriod(Base):
    __tablename__ = "availability_periods"
    __table_args__ = (
        UniqueConstraint("name", name="uq_availability_periods_name"),
        CheckConstraint(
            "start_date <= end_date",
            name="ck_availability_periods_date_range",
        ),
        CheckConstraint(
            "weekly_target_minutes >= 0",
            name="ck_availability_periods_weekly_target",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(80))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    weekly_target_minutes: Mapped[int]
    order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    rules: Mapped[list[AvailabilityRule]] = relationship(
        back_populates="period",
        cascade="all, delete-orphan",
        order_by="AvailabilityRule.weekday",
    )


class AvailabilityRule(Base):
    __tablename__ = "availability_rules"
    __table_args__ = (
        CheckConstraint("weekday >= 0 AND weekday <= 6", name="ck_availability_rules_weekday"),
        CheckConstraint(
            "available_minutes >= 0 AND available_minutes <= 1440",
            name="ck_availability_rules_minutes",
        ),
    )

    period_id: Mapped[UUID] = mapped_column(
        ForeignKey("availability_periods.id", ondelete="CASCADE"),
        primary_key=True,
    )
    weekday: Mapped[int] = mapped_column(primary_key=True)
    available_minutes: Mapped[int]

    period: Mapped[AvailabilityPeriod] = relationship(back_populates="rules")


class AvailabilityException(Base):
    __tablename__ = "availability_exceptions"
    __table_args__ = (
        UniqueConstraint("date", name="uq_availability_exceptions_date"),
        CheckConstraint(
            "available_minutes >= 0 AND available_minutes <= 1440",
            name="ck_availability_exceptions_minutes",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    date: Mapped[date] = mapped_column(Date)
    available_minutes: Mapped[int]
    reason: Mapped[str] = mapped_column(String(240), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class Material(Base):
    __tablename__ = "materials"
    __table_args__ = (
        CheckConstraint(
            "material_type IN "
            "('textbook', 'exercise_book', 'past_paper', 'course', 'vocabulary', 'other')",
            name="ck_materials_type",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    subject_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("subjects.id", ondelete="SET NULL"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120))
    material_type: Mapped[str] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(240), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class TaskTemplate(Base):
    __tablename__ = "task_templates"
    __table_args__ = (
        CheckConstraint(
            "task_type IN "
            "('reading', 'practice', 'dictation', 'past_paper', 'memorization', 'review')",
            name="ck_task_templates_type",
        ),
        CheckConstraint(
            "default_est_minutes > 0",
            name="ck_task_templates_est_minutes",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    subject_id: Mapped[UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"),
        index=True,
    )
    material_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("materials.id", ondelete="SET NULL"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120))
    task_type: Mapped[str] = mapped_column(String(32))
    default_est_minutes: Mapped[int]
    description: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    phase_links: Mapped[list[TaskTemplatePhase]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
    )


class TaskTemplatePhase(Base):
    __tablename__ = "task_template_phases"

    task_template_id: Mapped[UUID] = mapped_column(
        ForeignKey("task_templates.id", ondelete="CASCADE"),
        primary_key=True,
    )
    phase_id: Mapped[UUID] = mapped_column(
        ForeignKey("plan_phases.id", ondelete="CASCADE"),
        primary_key=True,
    )

    template: Mapped[TaskTemplate] = relationship(back_populates="phase_links")
    phase: Mapped[PlanPhase] = relationship(back_populates="template_links")
