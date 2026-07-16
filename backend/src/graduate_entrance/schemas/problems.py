from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

ProblemKind = Literal["wrong", "hard", "good"]
ProblemCause = Literal["", "concept", "calculation", "method", "memory", "misread", "other"]
ProblemStatus = Literal["draft", "confirmed"]
SolutionSource = Literal["self", "answer", "gpt"]
KnowledgePointRole = Literal["primary", "secondary"]


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
    created_at: datetime
    knowledge_points: list[ProblemKnowledgePointRead]
    solutions: list[SolutionRead]


class ProblemPendingResponse(BaseModel):
    total: int
    problems: list[ProblemRead]


class ProblemListResponse(BaseModel):
    total: int
    problems: list[ProblemRead]


class ProblemConfirmRequest(BaseModel):
    content_md: str = Field(min_length=1)
    kind: ProblemKind
    cause: ProblemCause = ""
    my_answer_md: str = ""
    note: str = ""
    source_ref: str = ""
    knowledge_points: list[ProblemKnowledgePointInput] = Field(min_length=1)
