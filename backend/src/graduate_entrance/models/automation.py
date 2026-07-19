from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Date, DateTime, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from graduate_entrance.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class AutomationRun(Base):
    __tablename__ = "automation_runs"
    # A job may only succeed once per logical target date; failed/skipped rows
    # stay unconstrained so retries and audit history are preserved.
    __table_args__ = (
        Index(
            "uq_automation_runs_success",
            "job_name",
            "run_date",
            unique=True,
            postgresql_where=text("status = 'success'"),
            sqlite_where=text("status = 'success'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    job_name: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16))
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    run_date: Mapped[date | None] = mapped_column(Date, index=True, default=None)
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
