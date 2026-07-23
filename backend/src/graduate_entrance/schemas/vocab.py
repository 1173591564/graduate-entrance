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
    phonetic: str
    example_en: str
    example_zh: str
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
    reviewed_today_count: int = Field(
        default=0, description="last_reviewed_on == date 的词数"
    )
    dictation_total_today: int = Field(default=0, description="当日默写总词数")
    dictation_correct_today: int = Field(default=0, description="当日默写写对词数")


class VocabGradeRequest(BaseModel):
    grade: VocabGrade
    as_of: date | None = None


class VocabGradeResult(BaseModel):
    word: VocabWordRead
    grade: VocabGrade
    due_date: date


class VocabDictationResponse(BaseModel):
    date: date
    words: list[VocabWordRead]


class VocabDictationResultRequest(BaseModel):
    correct_word_ids: list[UUID] = Field(default_factory=list)
    wrong_word_ids: list[UUID] = Field(default_factory=list)
    as_of: date | None = None


class VocabDictationResultRead(BaseModel):
    date: date
    total: int
    correct: int


class VocabBulkEnrichStatus(BaseModel):
    running: bool
    processed: int
    failed: int
    remaining: int


class VocabStatsResponse(BaseModel):
    total_count: int
    learned_count: int
    due_count: int
    mastered_count: int = Field(description="reps >= 3 的词数")
    dictation_total_today: int = Field(default=0, description="当日默写总词数")
    dictation_correct_today: int = Field(default=0, description="当日默写写对词数")
