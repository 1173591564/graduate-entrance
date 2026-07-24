from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from graduate_entrance.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class RecitationItem(Base):
    __tablename__ = "recitation_items"
    __table_args__ = (
        UniqueConstraint("subject", "title", name="uq_recitation_subject_title"),
        CheckConstraint("recite_count >= 0", name="ck_recitation_recite_count"),
        CheckConstraint(
            "subject in ('politics', 'english', 'math', 'cs408')",
            name="ck_recitation_subject",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(16), index=True)
    category: Mapped[str] = mapped_column(String(120), default="", index=True)
    title: Mapped[str] = mapped_column(Text)
    content_md: Mapped[str] = mapped_column(Text, default="")
    order_index: Mapped[int] = mapped_column(default=0, index=True)
    recite_count: Mapped[int] = mapped_column(default=0)
    last_recited_on: Mapped[date | None] = mapped_column(Date)
    ef: Mapped[float] = mapped_column(default=2.5)
    interval_days: Mapped[int] = mapped_column(default=0)
    reps: Mapped[int] = mapped_column(default=0)
    due_date: Mapped[date | None] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
