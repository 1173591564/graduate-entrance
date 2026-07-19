from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from graduate_entrance.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class TaskPoolItem(Base):
    __tablename__ = "task_pool_items"
    __table_args__ = (
        UniqueConstraint(
            "phase_id",
            "task_template_id",
            "knowledge_point_id",
            name="uq_task_pool_items_source",
        ),
        CheckConstraint("est_minutes > 0", name="ck_task_pool_items_est_minutes"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    phase_id: Mapped[UUID] = mapped_column(
        ForeignKey("plan_phases.id", ondelete="CASCADE"),
        index=True,
    )
    subject_id: Mapped[UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"),
        index=True,
    )
    knowledge_point_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"),
        index=True,
    )
    task_template_id: Mapped[UUID] = mapped_column(
        ForeignKey("task_templates.id", ondelete="CASCADE"),
        index=True,
    )
    material_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("materials.id", ondelete="SET NULL"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(320))
    task_type: Mapped[str] = mapped_column(String(32))
    est_minutes: Mapped[int]
    priority: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"
    __table_args__ = (
        UniqueConstraint("pool_item_id", name="uq_scheduled_tasks_pool_item"),
        CheckConstraint("est_minutes > 0", name="ck_scheduled_tasks_est_minutes"),
        CheckConstraint(
            "actual_minutes IS NULL OR actual_minutes >= 0",
            name="ck_scheduled_tasks_actual_minutes",
        ),
        CheckConstraint("carry_count >= 0", name="ck_scheduled_tasks_carry_count"),
        CheckConstraint(
            "status IN ('planned', 'completed', 'skipped')",
            name="ck_scheduled_tasks_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    pool_item_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("task_pool_items.id", ondelete="SET NULL"),
        index=True,
    )
    phase_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("plan_phases.id", ondelete="SET NULL"),
        index=True,
    )
    subject_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("subjects.id", ondelete="SET NULL"),
        index=True,
    )
    knowledge_point_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="SET NULL"),
        index=True,
    )
    material_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("materials.id", ondelete="SET NULL"),
        index=True,
    )
    phase_name: Mapped[str] = mapped_column(String(80))
    subject_name: Mapped[str] = mapped_column(String(80))
    knowledge_point_name: Mapped[str] = mapped_column(Text)
    material_name: Mapped[str | None] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(320))
    task_type: Mapped[str] = mapped_column(String(32))
    planned_date: Mapped[date] = mapped_column(Date, index=True)
    est_minutes: Mapped[int]
    status: Mapped[str] = mapped_column(String(24), default="planned", index=True)
    actual_minutes: Mapped[int | None]
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    carry_count: Mapped[int] = mapped_column(default=0)
    order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class AiWeekPlan(Base):
    __tablename__ = "ai_week_plans"
    __table_args__ = (UniqueConstraint("week_start", name="uq_ai_week_plans_week_start"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    week_start: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(16), default="confirmed")
    summary: Mapped[str] = mapped_column(Text)
    daily_focus: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list)
    review_suggestions: Mapped[list[str]] = mapped_column(JSON, default=list)
    model: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
