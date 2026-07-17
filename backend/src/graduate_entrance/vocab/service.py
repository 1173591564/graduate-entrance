from __future__ import annotations

import json
import re
from datetime import date, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.ai import client as ai_client
from graduate_entrance.models.vocab import VocabWord
from graduate_entrance.problems.service import apply_sm2
from graduate_entrance.schemas.vocab import (
    VocabDictationResponse,
    VocabGrade,
    VocabGradeResult,
    VocabStatsResponse,
    VocabTodayResponse,
    VocabWordRead,
)

DEFAULT_NEW_LIMIT = 50
MASTERED_REPS = 3

ENRICH_PROMPT = (
    "你是考研英语词汇助手。给定一个单词，返回严格的 JSON（不要代码块、不要多余文字），"
    '格式：{"phonetic": "美式音标，含斜杠", "example_en": "一句考研难度的英文例句", '
    '"example_zh": "该例句的中文翻译"}'
)


def _read(word: VocabWord) -> VocabWordRead:
    return VocabWordRead(
        id=word.id,
        word=word.word,
        meaning=word.meaning,
        phonetic=word.phonetic,
        example_en=word.example_en,
        example_zh=word.example_zh,
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


async def vocab_dictation(session: AsyncSession, as_of: date) -> VocabDictationResponse:
    words = (
        (
            await session.execute(
                select(VocabWord)
                .where(VocabWord.last_reviewed_on == as_of)
                .order_by(VocabWord.order_index)
            )
        )
        .scalars()
        .all()
    )
    return VocabDictationResponse(date=as_of, words=[_read(word) for word in words])


def _parse_enrichment(raw: str) -> dict[str, str]:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI 返回格式无法解析",
        )
    try:
        data = json.loads(match.group(0))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI 返回格式无法解析",
        ) from exc
    result: dict[str, str] = {}
    for key in ("phonetic", "example_en", "example_zh"):
        value = data.get(key)
        result[key] = value.strip() if isinstance(value, str) else ""
    return result


async def enrich_word(session: AsyncSession, word_id: UUID) -> VocabWordRead:
    word = await session.get(VocabWord, word_id)
    if word is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="单词不存在")
    if word.phonetic and word.example_en:
        return _read(word)
    raw = await ai_client.complete_chat(
        [
            {"role": "system", "content": ENRICH_PROMPT},
            {"role": "user", "content": f"单词：{word.word}（释义：{word.meaning}）"},
        ]
    )
    data = _parse_enrichment(raw)
    if data["phonetic"]:
        word.phonetic = data["phonetic"][:120]
    if data["example_en"]:
        word.example_en = data["example_en"]
    if data["example_zh"]:
        word.example_zh = data["example_zh"]
    await session.commit()
    await session.refresh(word)
    return _read(word)


async def vocab_stats(session: AsyncSession, as_of: date) -> VocabStatsResponse:
    total, learned, due, mastered = await _counts(session, as_of)
    return VocabStatsResponse(
        total_count=total,
        learned_count=learned,
        due_count=due,
        mastered_count=mastered,
    )
