from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AutomationRunRead(BaseModel):
    id: UUID
    job_name: str
    status: str
    detail: dict[str, Any]
    run_at: datetime


class AutomationRunsResponse(BaseModel):
    runs: list[AutomationRunRead]
