from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from graduate_entrance.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class RetroMessage(Base):
    __tablename__ = "retro_messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_retro_messages_role"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    week_start: Mapped[date] = mapped_column(Date, index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
