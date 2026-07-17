from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

VocabGrade = Literal["forgot", "vague", "mastered"]


class VocabWordRead(BaseModel):
    id: UUID
    word: str
    meaning: str
    book_page: int
    ef: float
    interval_days: int
    due_date: date | None
    reps: int


class VocabTodayResponse(BaseModel):
    date: date
    due_words: list[VocabWordRead]
    new_words: list[VocabWordRead]
    due_count: int
    learned_count: int
    total_count: int


class VocabGradeRequest(BaseModel):
    grade: VocabGrade
    as_of: date | None = None


class VocabGradeResult(BaseModel):
    word: VocabWordRead
    grade: VocabGrade
    due_date: date


class VocabStatsResponse(BaseModel):
    total_count: int
    learned_count: int
    due_count: int
    mastered_count: int = Field(description="reps >= 3 的词数")
