from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from graduate_entrance.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class VocabWord(Base):
    __tablename__ = "vocab_words"
    __table_args__ = (
        CheckConstraint("ef >= 1.3", name="ck_vocab_words_ef"),
        CheckConstraint("interval_days >= 0", name="ck_vocab_words_interval_days"),
        CheckConstraint("reps >= 0", name="ck_vocab_words_reps"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    word: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    meaning: Mapped[str] = mapped_column(Text, default="")
    book_page: Mapped[int] = mapped_column(default=0)
    order_index: Mapped[int] = mapped_column(default=0, index=True)
    ef: Mapped[float] = mapped_column(Float, default=2.5)
    interval_days: Mapped[int] = mapped_column(default=0)
    due_date: Mapped[date | None] = mapped_column(Date, index=True)
    reps: Mapped[int] = mapped_column(default=0)
    last_reviewed_on: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
