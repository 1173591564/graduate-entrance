from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.db.session import get_session
from graduate_entrance.recitation.service import (
    import_items,
    item_today,
    list_items,
    recitation_stats,
    recite,
)
from graduate_entrance.schemas.recitation import (
    RecitationImportRequest,
    RecitationImportResult,
    RecitationListResponse,
    RecitationStatsResponse,
    RecitationSubject,
    RecitationTodayResponse,
    ReciteRequest,
    ReciteResult,
)

router = APIRouter(tags=["recitation"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.post("/recitations/import", response_model=RecitationImportResult)
async def import_recitations(
    session: Session,
    payload: RecitationImportRequest,
) -> RecitationImportResult:
    return await import_items(session, payload.items)


@router.get("/recitations", response_model=RecitationListResponse)
async def read_recitations(
    session: Session,
    subject: Annotated[RecitationSubject | None, Query()] = None,
) -> RecitationListResponse:
    return await list_items(session, subject, date.today())


@router.get("/recitations/today", response_model=RecitationTodayResponse)
async def read_recitation_today(
    session: Session,
    subject: Annotated[RecitationSubject | None, Query()] = None,
    as_of: Annotated[date | None, Query()] = None,
) -> RecitationTodayResponse:
    return await item_today(session, subject, as_of or date.today())


@router.get("/recitations/stats", response_model=RecitationStatsResponse)
async def read_recitation_stats(
    session: Session,
    subject: Annotated[RecitationSubject | None, Query()] = None,
) -> RecitationStatsResponse:
    return await recitation_stats(session, subject, date.today())


@router.post("/recitations/{item_id}/recite", response_model=ReciteResult)
async def recite_item(
    session: Session,
    item_id: UUID,
    payload: ReciteRequest,
) -> ReciteResult:
    return await recite(
        session,
        item_id,
        payload.as_of or date.today(),
        payload.undo,
        payload.grade,
    )
