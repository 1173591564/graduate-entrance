from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from graduate_entrance.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class SubjectGoal(Base):
    __tablename__ = "subject_goals"
    __table_args__ = (
        CheckConstraint("full_score > 0", name="ck_subject_goals_full_score"),
        CheckConstraint(
            "target_score >= 0 AND target_score <= full_score",
            name="ck_subject_goals_target_score",
        ),
    )

    subject_id: Mapped[UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    target_score: Mapped[int]
    full_score: Mapped[int]
    note: Mapped[str] = mapped_column(String(240), default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
