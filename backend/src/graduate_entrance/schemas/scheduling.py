from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from graduate_entrance.schemas.planning import TaskType

TaskStatus = Literal["planned", "completed", "skipped"]


class TaskPoolGenerationResponse(BaseModel):
    created: int
    updated: int
    deleted: int
    total: int


class TaskPoolItemRead(BaseModel):
    id: UUID
    phase_id: UUID
    phase_name: str
    subject_id: UUID
    subject_name: str
    knowledge_point_id: UUID
    knowledge_point_name: str
    task_template_id: UUID
    task_template_name: str
    material_id: UUID | None
    material_name: str | None
    title: str
    task_type: TaskType
    est_minutes: int
    priority: int


class TaskPoolPage(BaseModel):
    items: list[TaskPoolItemRead]
    total: int
    offset: int
    limit: int


class PlanGenerationRequest(BaseModel):
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_date_range(self) -> "PlanGenerationRequest":
        if self.start_date > self.end_date:
            raise ValueError("start_date must not be after end_date")
        if (self.end_date - self.start_date).days > 366:
            raise ValueError("date range must not exceed 367 days")
        return self


class PlanTaskRead(BaseModel):
    id: UUID
    pool_item_id: UUID | None
    phase_id: UUID | None
    phase_name: str
    subject_id: UUID | None
    subject_name: str
    knowledge_point_id: UUID | None
    knowledge_point_name: str
    material_id: UUID | None
    material_name: str | None
    title: str
    task_type: TaskType
    planned_date: date
    est_minutes: int
    status: TaskStatus
    actual_minutes: int | None = None
    done_at: datetime | None = None
    carry_count: int = 0
    order: int


class PlanDaySummary(BaseModel):
    date: date
    available_minutes: int
    planned_minutes: int
    remaining_minutes: int


class PlanSubjectSummary(BaseModel):
    phase_id: UUID
    phase_name: str
    subject_id: UUID
    subject_name: str
    target_percentage: int = Field(ge=0, le=100)
    planned_minutes: int


class PlanResponse(BaseModel):
    start_date: date
    end_date: date
    persisted: bool
    tasks: list[PlanTaskRead]
    days: list[PlanDaySummary]
    subjects: list[PlanSubjectSummary]
    warnings: list[str]


class CalendarDayRead(BaseModel):
    date: date
    planned_minutes: int
    completed_minutes: int
    tasks: list[PlanTaskRead]


class CalendarWeekRead(BaseModel):
    week_start: date
    week_end: date
    planned_minutes: int
    completed_minutes: int


class CalendarResponse(BaseModel):
    month: str
    days: list[CalendarDayRead]
    weeks: list[CalendarWeekRead]


class TodayResponse(BaseModel):
    date: date
    planned_minutes: int
    completed_minutes: int
    remaining_minutes: int
    tasks: list[PlanTaskRead]


class TaskCompletionRequest(BaseModel):
    actual_minutes: int = Field(ge=0, le=1440)
