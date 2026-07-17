from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

RecitationSubject = Literal["politics", "english"]


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


class RecitationGroup(BaseModel):
    category: str
    items: list[RecitationRead]


class RecitationStatsResponse(BaseModel):
    total_count: int
    recited_today: int
    never_recited: int


class RecitationListResponse(BaseModel):
    groups: list[RecitationGroup]
    stats: RecitationStatsResponse


class RecitationTodayResponse(BaseModel):
    date: date
    item: RecitationRead | None
    stats: RecitationStatsResponse


class ReciteRequest(BaseModel):
    as_of: date | None = None
    undo: bool = False


class ReciteResult(BaseModel):
    item: RecitationRead
