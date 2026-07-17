from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

PaperStatus = Literal["unread", "reading", "done"]


class PaperSyncItem(BaseModel):
    rel_path: str = Field(min_length=1, max_length=500)
    title: str = ""
    category: str = ""
    size_bytes: int = Field(default=0, ge=0)


class PaperSyncRequest(BaseModel):
    papers: list[PaperSyncItem]


class PaperSyncResult(BaseModel):
    imported: int
    updated: int
    total_count: int


class PaperRead(BaseModel):
    id: UUID
    rel_path: str
    title: str
    category: str
    size_bytes: int
    status: PaperStatus
    has_file: bool
    started_on: date | None
    finished_on: date | None


class PaperGroup(BaseModel):
    category: str
    papers: list[PaperRead]


class PaperStatsResponse(BaseModel):
    total_count: int
    unread_count: int
    reading_count: int
    done_count: int


class PaperListResponse(BaseModel):
    groups: list[PaperGroup]
    stats: PaperStatsResponse


class PaperTodayResponse(BaseModel):
    date: date
    paper: PaperRead | None
    stats: PaperStatsResponse


class PaperStatusRequest(BaseModel):
    status: PaperStatus
    as_of: date | None = None


class PaperStatusResult(BaseModel):
    paper: PaperRead
