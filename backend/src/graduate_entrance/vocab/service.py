from __future__ import annotations

import json
import re
from datetime import date, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.ai import client as ai_client
from graduate_entrance.models.vocab import VocabDictationLog, VocabWord
from graduate_entrance.schemas.vocab import (
    VocabDictationResponse,
    VocabDictationResultRead,
    VocabDictationResultRequest,
    VocabGrade,
    VocabGradeResult,
    VocabStatsResponse,
    VocabTodayResponse,
    VocabWordRead,
)

DEFAULT_NEW_LIMIT = 20
MASTERED_REPS = 3
MIN_EASE_FACTOR = 1.3
GRADE_QUALITY: dict[VocabGrade, int] = {"forgot": 2, "vague": 3, "mastered": 5}
EBBINGHAUS_INTERVALS = (1, 2, 4, 7, 15)
DICTATION_EF_BONUS = 0.05
MAX_EASE_FACTOR = 3.0


def apply_vocab_srs(
    ef: float, interval_days: int, reps: int, grade: VocabGrade
) -> tuple[float, int, int]:
    """Return updated (ef, interval_days, reps) using Ebbinghaus-style early
    intervals (1/2/4/7/15 days) before switching to EF-based growth.

    Each grade maps to a distinct move on the forgetting curve:
    - forgot: back to the start — reset reps, review again tomorrow.
    - vague: stay in place — keep the ladder position, repeat the current
      interval with an ease penalty.
    - mastered: move forward — climb the ladder, then interval * EF.
    """
    quality = GRADE_QUALITY[grade]
    next_ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    next_ef = max(MIN_EASE_FACTOR, next_ef)
    if grade == "forgot":
        return next_ef, 1, 0
    if grade == "vague":
        return next_ef, max(1, interval_days), reps
    if reps < len(EBBINGHAUS_INTERVALS):
        next_interval = EBBINGHAUS_INTERVALS[reps]
    else:
        next_interval = max(interval_days + 1, round(interval_days * next_ef))
    return next_ef, next_interval, reps + 1


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
    started_today = (
        await session.execute(
            select(func.count())
            .select_from(VocabWord)
            .where(VocabWord.started_on == as_of)
        )
    ).scalar_one()
    new_budget = max(0, new_limit - started_today)
    new_words = (
        (
            await session.execute(
                select(VocabWord)
                .where(VocabWord.due_date.is_(None))
                .order_by(VocabWord.order_index)
                .limit(new_budget)
            )
        )
        .scalars()
        .all()
    )
    total, learned, due, _ = await _counts(session, as_of)
    reviewed_today = (
        await session.execute(
            select(func.count())
            .select_from(VocabWord)
            .where(VocabWord.last_reviewed_on == as_of)
        )
    ).scalar_one()
    dictation_total, dictation_correct = await _dictation_counts(session, as_of)
    return VocabTodayResponse(
        date=as_of,
        due_words=[_read(word) for word in due_words],
        new_words=[_read(word) for word in new_words],
        due_count=due,
        learned_count=learned,
        total_count=total,
        reviewed_today_count=reviewed_today,
        dictation_total_today=dictation_total,
        dictation_correct_today=dictation_correct,
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
    next_ef, next_interval, next_reps = apply_vocab_srs(
        word.ef, word.interval_days, word.reps, grade
    )
    word.ef = next_ef
    word.interval_days = next_interval
    word.reps = next_reps
    word.due_date = as_of + timedelta(days=next_interval)
    if word.last_reviewed_on is None:
        word.started_on = as_of
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


async def _dictation_counts(session: AsyncSession, as_of: date) -> tuple[int, int]:
    row = (
        await session.execute(
            select(
                func.coalesce(func.sum(VocabDictationLog.total), 0),
                func.coalesce(func.sum(VocabDictationLog.correct), 0),
            ).where(VocabDictationLog.dictated_on == as_of)
        )
    ).one()
    return int(row[0]), int(row[1])


async def submit_dictation_result(
    session: AsyncSession,
    payload: VocabDictationResultRequest,
    as_of: date,
) -> VocabDictationResultRead:
    wrong_ids = set(payload.wrong_word_ids)
    correct_ids = set(payload.correct_word_ids) - wrong_ids
    total = len(correct_ids) + len(wrong_ids)
    if total > 0:
        all_ids = correct_ids | wrong_ids
        words = (
            (
                await session.execute(
                    select(VocabWord).where(VocabWord.id.in_(all_ids))
                )
            )
            .scalars()
            .all()
        )
        for word in words:
            if word.id in wrong_ids:
                next_ef, next_interval, next_reps = apply_vocab_srs(
                    word.ef, word.interval_days, word.reps, "forgot"
                )
                word.ef = next_ef
                word.interval_days = next_interval
                word.reps = next_reps
                word.due_date = as_of + timedelta(days=next_interval)
            else:
                word.ef = min(MAX_EASE_FACTOR, word.ef + DICTATION_EF_BONUS)
        session.add(
            VocabDictationLog(
                dictated_on=as_of,
                total=total,
                correct=len(correct_ids),
            )
        )
        await session.commit()
    dictation_total, dictation_correct = await _dictation_counts(session, as_of)
    return VocabDictationResultRead(
        date=as_of,
        total=dictation_total,
        correct=dictation_correct,
    )


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
    dictation_total, dictation_correct = await _dictation_counts(session, as_of)
    return VocabStatsResponse(
        total_count=total,
        learned_count=learned,
        due_count=due,
        mastered_count=mastered,
        dictation_total_today=dictation_total,
        dictation_correct_today=dictation_correct,
    )
