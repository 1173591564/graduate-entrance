from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.models.vocab import VocabWord
from graduate_entrance.problems.service import apply_sm2
from graduate_entrance.schemas.vocab import (
    VocabGrade,
    VocabGradeResult,
    VocabStatsResponse,
    VocabTodayResponse,
    VocabWordRead,
)

DEFAULT_NEW_LIMIT = 50
MASTERED_REPS = 3


def _read(word: VocabWord) -> VocabWordRead:
    return VocabWordRead(
        id=word.id,
        word=word.word,
        meaning=word.meaning,
        book_page=word.book_page,
        ef=word.ef,
        interval_days=word.interval_days,
        due_date=word.due_date,
        reps=word.reps,
    )


async def _counts(session: AsyncSession, as_of: date) -> tuple[int, int, int, int]:
    total = (
        await session.execute(select(func.count()).select_from(VocabWord))
    ).scalar_one()
    learned = (
        await session.execute(
            select(func.count()).select_from(VocabWord).where(VocabWord.reps > 0)
        )
    ).scalar_one()
    due = (
        await session.execute(
            select(func.count())
            .select_from(VocabWord)
            .where(VocabWord.due_date <= as_of)
        )
    ).scalar_one()
    mastered = (
        await session.execute(
            select(func.count())
            .select_from(VocabWord)
            .where(VocabWord.reps >= MASTERED_REPS)
        )
    ).scalar_one()
    return total, learned, due, mastered


async def vocab_today(
    session: AsyncSession,
    as_of: date,
    new_limit: int = DEFAULT_NEW_LIMIT,
) -> VocabTodayResponse:
    due_words = (
        (
            await session.execute(
                select(VocabWord)
                .where(VocabWord.due_date <= as_of)
                .order_by(VocabWord.due_date, VocabWord.order_index)
            )
        )
        .scalars()
        .all()
    )
    new_words = (
        (
            await session.execute(
                select(VocabWord)
                .where(VocabWord.due_date.is_(None))
                .order_by(VocabWord.order_index)
                .limit(new_limit)
            )
        )
        .scalars()
        .all()
    )
    total, learned, due, _ = await _counts(session, as_of)
    return VocabTodayResponse(
        date=as_of,
        due_words=[_read(word) for word in due_words],
        new_words=[_read(word) for word in new_words],
        due_count=due,
        learned_count=learned,
        total_count=total,
    )


async def grade_word(
    session: AsyncSession,
    word_id: UUID,
    grade: VocabGrade,
    as_of: date,
) -> VocabGradeResult:
    word = await session.get(VocabWord, word_id)
    if word is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="单词不存在")
    next_ef, next_interval, next_reps = apply_sm2(
        word.ef, word.interval_days, word.reps, grade
    )
    word.ef = next_ef
    word.interval_days = next_interval
    word.reps = next_reps
    word.due_date = as_of + timedelta(days=next_interval)
    word.last_reviewed_on = as_of
    await session.commit()
    await session.refresh(word)
    return VocabGradeResult(
        word=_read(word),
        grade=grade,
        due_date=word.due_date or as_of,
    )


async def vocab_stats(session: AsyncSession, as_of: date) -> VocabStatsResponse:
    total, learned, due, mastered = await _counts(session, as_of)
    return VocabStatsResponse(
        total_count=total,
        learned_count=learned,
        due_count=due,
        mastered_count=mastered,
    )
