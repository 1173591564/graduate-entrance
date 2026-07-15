from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

MaterialType = Literal[
    "textbook",
    "exercise_book",
    "past_paper",
    "course",
    "vocabulary",
    "other",
]
TaskType = Literal[
    "reading",
    "practice",
    "dictation",
    "past_paper",
    "memorization",
    "review",
]


class PlanningSubjectRead(BaseModel):
    id: UUID
    code: str
    name: str
    order: int


class PhaseSubjectRatioInput(BaseModel):
    subject_id: UUID
    percentage: int = Field(ge=0, le=100)


class PlanPhaseInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    start_date: date
    end_date: date
    description: str = Field(default="", max_length=4000)
    milestones: list[str] = Field(default_factory=list, max_length=20)
    allow_new_tasks: bool = True
    order: int = Field(default=0, ge=0)
    subject_ratios: list[PhaseSubjectRatioInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_phase(self) -> "PlanPhaseInput":
        if self.start_date > self.end_date:
            raise ValueError("start_date must not be after end_date")
        subject_ids = [ratio.subject_id for ratio in self.subject_ratios]
        if len(subject_ids) != len(set(subject_ids)):
            raise ValueError("subject ratios must contain unique subjects")
        total = sum(ratio.percentage for ratio in self.subject_ratios)
        if self.allow_new_tasks and total != 100:
            raise ValueError("subject ratios must total 100 when new tasks are allowed")
        if not self.allow_new_tasks and total not in (0, 100):
            raise ValueError("subject ratios must be empty or total 100")
        return self


class PlanPhaseRead(PlanPhaseInput):
    id: UUID


class AvailabilityRuleInput(BaseModel):
    weekday: int = Field(ge=0, le=6)
    available_minutes: int = Field(ge=0, le=1440)


class AvailabilityPeriodInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    start_date: date
    end_date: date
    weekly_target_minutes: int = Field(ge=0, le=10080)
    order: int = Field(default=0, ge=0)
    rules: list[AvailabilityRuleInput]

    @model_validator(mode="after")
    def validate_period(self) -> "AvailabilityPeriodInput":
        if self.start_date > self.end_date:
            raise ValueError("start_date must not be after end_date")
        weekdays = [rule.weekday for rule in self.rules]
        if sorted(weekdays) != list(range(7)):
            raise ValueError("availability rules must contain weekdays 0 through 6 exactly once")
        return self


class AvailabilityPeriodRead(AvailabilityPeriodInput):
    id: UUID


class AvailabilityExceptionInput(BaseModel):
    date: date
    available_minutes: int = Field(ge=0, le=1440)
    reason: str = Field(default="", max_length=240)


class AvailabilityExceptionRead(AvailabilityExceptionInput):
    id: UUID


class MaterialInput(BaseModel):
    subject_id: UUID | None = None
    name: str = Field(min_length=1, max_length=120)
    material_type: MaterialType
    source: str = Field(default="", max_length=240)
    description: str = Field(default="", max_length=4000)
    active: bool = True
    order: int = Field(default=0, ge=0)


class MaterialRead(MaterialInput):
    id: UUID


class TaskTemplateInput(BaseModel):
    subject_id: UUID
    material_id: UUID | None = None
    name: str = Field(min_length=1, max_length=120)
    task_type: TaskType
    default_est_minutes: int = Field(gt=0, le=1440)
    description: str = Field(default="", max_length=4000)
    active: bool = True
    order: int = Field(default=0, ge=0)
    phase_ids: list[UUID] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_phase_ids(self) -> "TaskTemplateInput":
        if len(self.phase_ids) != len(set(self.phase_ids)):
            raise ValueError("phase_ids must be unique")
        return self


class TaskTemplateRead(TaskTemplateInput):
    id: UUID


class PlanningConfigResponse(BaseModel):
    subjects: list[PlanningSubjectRead]
    phases: list[PlanPhaseRead]
    availability_periods: list[AvailabilityPeriodRead]
    availability_exceptions: list[AvailabilityExceptionRead]
    materials: list[MaterialRead]
    task_templates: list[TaskTemplateRead]
