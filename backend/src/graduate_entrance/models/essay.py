from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from graduate_entrance.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class EssayMaterial(Base):
    __tablename__ = "essay_materials"
    __table_args__ = (
        CheckConstraint(
            "category IN ('phrase', 'sentence', 'paragraph', 'template', 'quote')",
            name="ck_essay_materials_category",
        ),
        CheckConstraint("interval_days >= 0", name="ck_essay_materials_interval_days"),
        CheckConstraint("recite_count >= 0", name="ck_essay_materials_recite_count"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(240))
    category: Mapped[str] = mapped_column(String(16), default="sentence", index=True)
    topic: Mapped[str] = mapped_column(String(120), default="", index=True)
    content_md: Mapped[str] = mapped_column(Text, default="")
    translation_md: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(240), default="")
    due_date: Mapped[date | None] = mapped_column(Date, index=True)
    interval_days: Mapped[int] = mapped_column(default=0)
    recite_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
