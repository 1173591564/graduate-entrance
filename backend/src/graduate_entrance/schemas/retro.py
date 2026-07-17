from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from graduate_entrance.schemas.scheduling import AiWeekPlanResponse


class RetroMessageRead(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime


class RetroSubjectSnapshot(BaseModel):
    subject_name: str
    mastery: float
    coverage: float
    target_score: int | None
    estimated_score: float | None


class RetroGapSuggestion(BaseModel):
    knowledge_point_id: UUID
    knowledge_point_name: str
    subject_name: str
    mastery: float
    target: float
    gap: float
    suggestion: str


class RetroContext(BaseModel):
    week_start: date
    week_end: date
    planned_minutes: int
    completed_minutes: int
    total_tasks: int
    completed_tasks: int
    execution_rate: float
    days_to_exam: int
    subjects: list[RetroSubjectSnapshot]
    weak_points: list[str]
    gap_suggestions: list[RetroGapSuggestion] = []


class RetroSessionResponse(BaseModel):
    context: RetroContext
    messages: list[RetroMessageRead]


class RetroChatRequest(BaseModel):
    week_start: date | None = None
    content: str = Field(min_length=1, max_length=4000)


class RetroChatResponse(BaseModel):
    messages: list[RetroMessageRead]


class RetroConfirmRequest(BaseModel):
    week_start: date | None = None


class RetroConfirmResponse(BaseModel):
    plan: AiWeekPlanResponse
