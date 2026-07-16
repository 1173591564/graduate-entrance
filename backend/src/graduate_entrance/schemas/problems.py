from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

ProblemKind = Literal["wrong", "hard", "good"]
ProblemCause = Literal["", "concept", "calculation", "method", "memory", "misread", "other"]
ProblemStatus = Literal["draft", "confirmed"]
SolutionSource = Literal["self", "answer", "gpt"]
KnowledgePointRole = Literal["primary", "secondary"]
ReviewGrade = Literal["forgot", "vague", "mastered"]


class ProblemKnowledgePointInput(BaseModel):
    knowledge_point_id: UUID
    role: KnowledgePointRole
    weight: float = Field(gt=0, le=1)


class ProblemKnowledgePointRead(BaseModel):
    knowledge_point_id: UUID
    knowledge_point_name: str
    role: KnowledgePointRole
    weight: float


class SolutionCreateRequest(BaseModel):
    content_md: str = Field(min_length=1)
    method_tag: str = ""
    source: SolutionSource = "self"


class SolutionRead(BaseModel):
    id: UUID
    content_md: str
    method_tag: str
    source: SolutionSource
    verified: bool
    created_at: datetime


class ProblemRead(BaseModel):
    id: UUID
    subject_id: UUID | None
    subject_name: str | None
    content_md: str
    images: list[str]
    source_ref: str
    kind: ProblemKind
    my_answer_md: str
    cause: ProblemCause
    note: str
    status: ProblemStatus
    due_date: date | None
    reps: int
    confirmed_at: datetime | None
    ai_score: float | None
    ai_feedback_md: str
    ai_graded_at: datetime | None
    created_at: datetime
    knowledge_points: list[ProblemKnowledgePointRead]
    solutions: list[SolutionRead]


class ProblemPendingResponse(BaseModel):
    total: int
    problems: list[ProblemRead]


class ProblemListResponse(BaseModel):
    total: int
    problems: list[ProblemRead]


class ReviewDueResponse(BaseModel):
    total: int
    as_of: date
    problems: list[ProblemRead]


class ReviewRequest(BaseModel):
    grade: ReviewGrade


class ReviewResult(BaseModel):
    problem: ProblemRead
    grade: ReviewGrade
    ef: float
    interval_days: int
    reps: int
    due_date: date


class ExtractedKnowledgePoint(BaseModel):
    knowledge_point_id: UUID
    knowledge_point_name: str
    role: KnowledgePointRole
    weight: float


class ExtractedSolution(BaseModel):
    content_md: str
    method_tag: str = ""


class ProblemExtractionResult(BaseModel):
    problem_id: UUID
    model: str
    content_md: str
    knowledge_points: list[ExtractedKnowledgePoint]
    solution: ExtractedSolution | None


class BatchExtractionItem(BaseModel):
    problem: ProblemRead
    extraction: ProblemExtractionResult | None
    error: str | None


class BatchExtractionResponse(BaseModel):
    total: int
    extracted: int
    items: list[BatchExtractionItem]


class GradeRequest(BaseModel):
    answer_md: str = ""


class GradeResult(BaseModel):
    problem_id: UUID
    model: str
    score: float = Field(ge=0, le=100)
    feedback_md: str
    suggestions: list[str]
    graded_at: datetime


class KnowledgePointInsight(BaseModel):
    knowledge_point_id: UUID
    knowledge_point_name: str
    problem_count: int
    weighted_errors: float
    forgot_reviews: int
    total_reviews: int
    weakness_score: float


class CauseInsight(BaseModel):
    cause: ProblemCause
    count: int


class SubjectInsight(BaseModel):
    subject_id: UUID | None
    subject_name: str
    problem_count: int
    wrong_count: int


class WeeklyTrendPoint(BaseModel):
    week_start: date
    new_problems: int
    reviews: int
    forgot: int
    vague: int
    mastered: int


class ProblemInsightsResponse(BaseModel):
    as_of: date
    total_problems: int
    confirmed_problems: int
    knowledge_points: list[KnowledgePointInsight]
    causes: list[CauseInsight]
    subjects: list[SubjectInsight]
    weekly_trend: list[WeeklyTrendPoint]


class ProblemConfirmRequest(BaseModel):
    content_md: str = Field(min_length=1)
    kind: ProblemKind
    cause: ProblemCause = ""
    my_answer_md: str = ""
    note: str = ""
    source_ref: str = ""
    knowledge_points: list[ProblemKnowledgePointInput] = Field(min_length=1)
