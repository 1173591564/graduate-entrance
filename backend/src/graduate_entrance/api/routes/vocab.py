from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.db.session import get_session
from graduate_entrance.schemas.vocab import (
    VocabDictationResponse,
    VocabGradeRequest,
    VocabGradeResult,
    VocabStatsResponse,
    VocabTodayResponse,
    VocabWordRead,
)
from graduate_entrance.vocab.service import (
    DEFAULT_NEW_LIMIT,
    enrich_word,
    grade_word,
    vocab_dictation,
    vocab_stats,
    vocab_today,
)

router = APIRouter(tags=["vocab"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/vocab/today", response_model=VocabTodayResponse)
async def read_vocab_today(
    session: Session,
    as_of: Annotated[date | None, Query()] = None,
    new_limit: Annotated[int, Query(ge=0, le=200)] = DEFAULT_NEW_LIMIT,
) -> VocabTodayResponse:
    return await vocab_today(session, as_of or date.today(), new_limit=new_limit)


@router.post("/vocab/{word_id}/grade", response_model=VocabGradeResult)
async def grade_vocab_word(
    session: Session,
    word_id: UUID,
    payload: VocabGradeRequest,
) -> VocabGradeResult:
    return await grade_word(session, word_id, payload.grade, payload.as_of or date.today())


@router.get("/vocab/dictation", response_model=VocabDictationResponse)
async def read_vocab_dictation(
    session: Session,
    as_of: Annotated[date | None, Query()] = None,
) -> VocabDictationResponse:
    return await vocab_dictation(session, as_of or date.today())


@router.post("/vocab/{word_id}/enrich", response_model=VocabWordRead)
async def enrich_vocab_word(
    session: Session,
    word_id: UUID,
) -> VocabWordRead:
    return await enrich_word(session, word_id)


@router.get("/vocab/stats", response_model=VocabStatsResponse)
async def read_vocab_stats(
    session: Session,
    as_of: Annotated[date | None, Query()] = None,
) -> VocabStatsResponse:
    return await vocab_stats(session, as_of or date.today())
