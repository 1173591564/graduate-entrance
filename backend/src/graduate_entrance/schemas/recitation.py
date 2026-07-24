from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

RecitationSubject = Literal["politics", "english", "math", "cs408"]
ReciteGrade = Literal["forgot", "vague", "mastered"]


class RecitationImportItem(BaseModel):
    subject: RecitationSubject
    category: str = ""
    title: str = Field(min_length=1)
    content_md: str = ""


class RecitationImportRequest(BaseModel):
    items: list[RecitationImportItem]


class RecitationImportResult(BaseModel):
    imported: int
    updated: int
    total_count: int


class RecitationRead(BaseModel):
    id: UUID
    subject: RecitationSubject
    category: str
    title: str
    content_md: str
    recite_count: int
    last_recited_on: date | None
    recited_today: bool
    ef: float = 2.5
    interval_days: int = 0
    reps: int = 0
    due_date: date | None = None


class RecitationGroup(BaseModel):
    category: str
    items: list[RecitationRead]


class RecitationStatsResponse(BaseModel):
    total_count: int
    recited_today: int
    never_recited: int
    due_count: int = 0


class RecitationListResponse(BaseModel):
    groups: list[RecitationGroup]
    stats: RecitationStatsResponse


class RecitationTodayResponse(BaseModel):
    date: date
    item: RecitationRead | None
    queue: list[RecitationRead] = Field(default_factory=list)
    stats: RecitationStatsResponse


class ReciteRequest(BaseModel):
    as_of: date | None = None
    undo: bool = False
    grade: ReciteGrade | None = None


class ReciteResult(BaseModel):
    item: RecitationRead
