from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class SubjectGoalInput(BaseModel):
    subject_id: UUID
    target_score: int = Field(ge=0)
    full_score: int = Field(gt=0)
    note: str = ""

    @model_validator(mode="after")
    def check_target_within_full(self) -> "SubjectGoalInput":
        if self.target_score > self.full_score:
            raise ValueError("target_score must not exceed full_score")
        return self


class SubjectGoalRead(BaseModel):
    subject_id: UUID
    subject_name: str
    target_score: int
    full_score: int
    note: str
    updated_at: datetime


class GoalsUpdateRequest(BaseModel):
    goals: list[SubjectGoalInput] = Field(min_length=1)


class GoalsResponse(BaseModel):
    goals: list[SubjectGoalRead]


class WeakKnowledgePoint(BaseModel):
    knowledge_point_id: UUID
    knowledge_point_name: str
    mastery: float
    problem_count: int
    forgot_reviews: int


class SubjectMastery(BaseModel):
    subject_id: UUID
    subject_name: str
    target_score: int | None
    full_score: int | None
    knowledge_point_total: int
    studied_points: int
    coverage: float
    mastery: float
    estimated_score: float | None
    studied_minutes: int
    problem_count: int
    wrong_count: int
    weak_points: list[WeakKnowledgePoint]


class StudyProfileResponse(BaseModel):
    as_of: date
    exam_date: date
    days_to_exam: int
    overall_mastery: float
    overall_coverage: float
    subjects: list[SubjectMastery]
