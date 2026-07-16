from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class EssayCategory(StrEnum):
    phrase = "phrase"
    sentence = "sentence"
    paragraph = "paragraph"
    template = "template"
    quote = "quote"


class ReciteResult(StrEnum):
    remembered = "remembered"
    forgot = "forgot"


class EssayMaterialCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    category: EssayCategory = EssayCategory.sentence
    topic: str = Field(default="", max_length=120)
    content_md: str = Field(min_length=1)
    translation_md: str = ""
    source: str = Field(default="", max_length=240)


class EssayMaterialUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    category: EssayCategory | None = None
    topic: str | None = Field(default=None, max_length=120)
    content_md: str | None = Field(default=None, min_length=1)
    translation_md: str | None = None
    source: str | None = Field(default=None, max_length=240)


class EssayMaterialRead(BaseModel):
    id: UUID
    title: str
    category: EssayCategory
    topic: str
    content_md: str
    translation_md: str
    source: str
    due_date: date | None
    interval_days: int
    recite_count: int
    created_at: datetime
    updated_at: datetime


class EssayMaterialListResponse(BaseModel):
    total: int
    materials: list[EssayMaterialRead]


class ReciteRequest(BaseModel):
    result: ReciteResult


class ReciteResponse(BaseModel):
    material: EssayMaterialRead
    next_due: date
