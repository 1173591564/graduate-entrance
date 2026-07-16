from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from graduate_entrance.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class Problem(Base):
    __tablename__ = "problems"
    __table_args__ = (
        CheckConstraint("kind IN ('wrong', 'hard', 'good')", name="ck_problems_kind"),
        CheckConstraint(
            "cause IN ('', 'concept', 'calculation', 'method', 'memory', 'misread', 'other')",
            name="ck_problems_cause",
        ),
        CheckConstraint("status IN ('draft', 'confirmed')", name="ck_problems_status"),
        CheckConstraint("ef >= 1.3", name="ck_problems_ef"),
        CheckConstraint("interval_days >= 0", name="ck_problems_interval_days"),
        CheckConstraint("reps >= 0", name="ck_problems_reps"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    subject_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("subjects.id", ondelete="SET NULL"),
        index=True,
    )
    content_md: Mapped[str] = mapped_column(Text, default="")
    images: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_ref: Mapped[str] = mapped_column(String(240), default="")
    kind: Mapped[str] = mapped_column(String(16), default="wrong")
    my_answer_md: Mapped[str] = mapped_column(Text, default="")
    cause: Mapped[str] = mapped_column(String(32), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)
    ef: Mapped[float] = mapped_column(Float, default=2.5)
    interval_days: Mapped[int] = mapped_column(default=0)
    due_date: Mapped[date | None] = mapped_column(Date, index=True)
    reps: Mapped[int] = mapped_column(default=0)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    kp_links: Mapped[list[ProblemKnowledgePoint]] = relationship(
        back_populates="problem",
        cascade="all, delete-orphan",
        order_by="ProblemKnowledgePoint.knowledge_point_id",
    )
    solutions: Mapped[list[Solution]] = relationship(
        back_populates="problem",
        cascade="all, delete-orphan",
        order_by="Solution.created_at",
    )


class ReviewLog(Base):
    __tablename__ = "review_logs"
    __table_args__ = (
        CheckConstraint(
            "grade IN ('forgot', 'vague', 'mastered')",
            name="ck_review_logs_grade",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    problem_id: Mapped[UUID] = mapped_column(
        ForeignKey("problems.id", ondelete="CASCADE"),
        index=True,
    )
    grade: Mapped[str] = mapped_column(String(16))
    reviewed_on: Mapped[date] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Solution(Base):
    __tablename__ = "solutions"
    __table_args__ = (
        CheckConstraint("source IN ('self', 'answer', 'gpt')", name="ck_solutions_source"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    problem_id: Mapped[UUID] = mapped_column(
        ForeignKey("problems.id", ondelete="CASCADE"),
        index=True,
    )
    content_md: Mapped[str] = mapped_column(Text)
    method_tag: Mapped[str] = mapped_column(String(80), default="")
    source: Mapped[str] = mapped_column(String(16), default="self")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    problem: Mapped[Problem] = relationship(back_populates="solutions")


class ProblemKnowledgePoint(Base):
    __tablename__ = "problem_knowledge_points"
    __table_args__ = (
        CheckConstraint(
            "role IN ('primary', 'secondary')",
            name="ck_problem_knowledge_points_role",
        ),
        CheckConstraint(
            "weight > 0 AND weight <= 1",
            name="ck_problem_knowledge_points_weight",
        ),
    )

    problem_id: Mapped[UUID] = mapped_column(
        ForeignKey("problems.id", ondelete="CASCADE"),
        primary_key=True,
    )
    knowledge_point_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(16))
    weight: Mapped[float] = mapped_column(Float)

    problem: Mapped[Problem] = relationship(back_populates="kp_links")
