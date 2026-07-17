from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from graduate_entrance.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class KpMastery(Base):
    """Persisted mastery snapshot for a knowledge point.

    This is the middle layer that turns the isolated features (tasks, reviews,
    problems) into a closed loop: the three signals write ``mastery`` here, the
    exam blueprint / subject goal derive ``target`` here, and planning reads the
    ``target - mastery`` gap from here to decide what to schedule next.
    """

    __tablename__ = "kp_mastery"
    __table_args__ = (
        CheckConstraint("mastery >= 0 AND mastery <= 100", name="ck_kp_mastery_mastery"),
        CheckConstraint("target >= 0 AND target <= 100", name="ck_kp_mastery_target"),
    )

    knowledge_point_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"),
        primary_key=True,
    )
    subject_id: Mapped[UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"),
        index=True,
    )
    mastery: Mapped[Decimal] = mapped_column(Numeric(5, 1), default=Decimal("0.0"))
    target: Mapped[Decimal] = mapped_column(Numeric(5, 1), default=Decimal("0.0"))
    studied: Mapped[bool] = mapped_column(default=False)
    last_signal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
