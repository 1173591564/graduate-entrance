from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
)
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


class PaperContent(Base):
    __tablename__ = "paper_contents"

    paper_id: Mapped[UUID] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"),
        primary_key=True,
    )
    source: Mapped[str] = mapped_column(String(16), default="pdf")
    blocks: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class PaperAnnotation(Base):
    __tablename__ = "paper_annotations"
    __table_args__ = (
        CheckConstraint("block_index >= 0", name="ck_paper_annotations_block_index"),
        CheckConstraint(
            "color in ('yellow', 'green', 'blue', 'red')",
            name="ck_paper_annotations_color",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    paper_id: Mapped[UUID] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"),
        index=True,
    )
    block_index: Mapped[int] = mapped_column()
    excerpt: Mapped[str] = mapped_column(Text, default="")
    note: Mapped[str] = mapped_column(Text, default="")
    color: Mapped[str] = mapped_column(String(16), default="yellow")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
