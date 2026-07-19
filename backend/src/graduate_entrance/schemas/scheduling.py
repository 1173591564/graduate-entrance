from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from graduate_entrance.schemas.planning import TaskType

TaskStatus = Literal["planned", "completed", "skipped"]
StudyModule = Literal["vocab", "recitation"]


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


class PlanRescheduleRequest(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    leave_dates: list[date] = Field(default_factory=list, max_length=62)

    @model_validator(mode="after")
    def validate_date_range(self) -> "PlanRescheduleRequest":
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError("start_date must not be after end_date")
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
    study_module: StudyModule | None = None
    planned_date: date
    est_minutes: int
    status: TaskStatus
    source: str = "plan"
    actual_minutes: int | None = None
    done_at: datetime | None = None
    carry_count: int = 0
    order: int
    priority_score: float = 0.0


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
    carried_over: int = 0


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
    due_review_count: int = 0
    tasks: list[PlanTaskRead]


class TaskCompletionRequest(BaseModel):
    actual_minutes: int = Field(ge=0, le=1440)


class TaskUpdateRequest(BaseModel):
    est_minutes: int = Field(ge=1, le=1440)


class WeeklyStatRead(BaseModel):
    week_start: date
    week_end: date
    planned_minutes: int
    completed_minutes: int
    target_minutes: int | None
    total_tasks: int
    completed_tasks: int
    execution_rate: float


class WeeklyStatsResponse(BaseModel):
    start_date: date
    end_date: date
    weeks: list[WeeklyStatRead]
    total_planned_minutes: int
    total_completed_minutes: int
    overall_execution_rate: float


class AiDailyFocus(BaseModel):
    date: date
    focus: str


class AiWeekAdvice(BaseModel):
    week_start: date
    status: str = "confirmed"
    summary: str
    daily_focus: list[AiDailyFocus]
    review_suggestions: list[str]
    model: str
    created_at: datetime


class AiWeekPlanRequest(BaseModel):
    start_date: date | None = None


class AiWeekPlanResponse(BaseModel):
    plan: PlanResponse
    advice: AiWeekAdvice
