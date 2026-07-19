from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from graduate_entrance.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class AutomationRun(Base):
    __tablename__ = "automation_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    job_name: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16))
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
