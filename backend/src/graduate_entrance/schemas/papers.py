from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

PaperStatus = Literal["unread", "reading", "done"]
PaperContentSource = Literal["ar5iv", "pdf"]
AnnotationColor = Literal["yellow", "green", "blue", "red"]


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
    has_content: bool = False
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


class PaperBlock(BaseModel):
    type: Literal["heading", "paragraph"]
    md: str
    level: int = Field(default=0, ge=0, le=6)


class PaperContentUpload(BaseModel):
    source: PaperContentSource
    blocks: list[PaperBlock] = Field(min_length=1)


class PaperTocEntry(BaseModel):
    title: str
    level: int
    block_index: int


class PaperContentResponse(BaseModel):
    paper: PaperRead
    source: PaperContentSource
    blocks: list[PaperBlock]
    toc: list[PaperTocEntry]


class PaperAnnotationCreate(BaseModel):
    block_index: int = Field(ge=0)
    excerpt: str = ""
    note: str = ""
    color: AnnotationColor = "yellow"


class PaperAnnotationUpdate(BaseModel):
    note: str | None = None
    color: AnnotationColor | None = None


class PaperAnnotationRead(BaseModel):
    id: UUID
    paper_id: UUID
    block_index: int
    excerpt: str
    note: str
    color: AnnotationColor
    created_at: datetime


class PaperAnnotationList(BaseModel):
    annotations: list[PaperAnnotationRead]
