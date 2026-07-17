from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from graduate_entrance.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class Paper(Base):
    __tablename__ = "papers"
    __table_args__ = (
        CheckConstraint("size_bytes >= 0", name="ck_papers_size_bytes"),
        CheckConstraint(
            "status in ('unread', 'reading', 'done')",
            name="ck_papers_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    rel_path: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    title: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(120), default="", index=True)
    size_bytes: Mapped[int] = mapped_column(default=0)
    order_index: Mapped[int] = mapped_column(default=0, index=True)
    status: Mapped[str] = mapped_column(String(16), default="unread", index=True)
    stored_filename: Mapped[str | None] = mapped_column(String(80))
    started_on: Mapped[date | None] = mapped_column(Date)
    finished_on: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
