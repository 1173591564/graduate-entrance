from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.db.session import get_session
from graduate_entrance.retro.service import (
    confirm_next_week_plan,
    get_retro_session,
    send_retro_message,
)
from graduate_entrance.schemas.retro import (
    RetroChatRequest,
    RetroChatResponse,
    RetroConfirmRequest,
    RetroConfirmResponse,
    RetroSessionResponse,
)

router = APIRouter(tags=["retro"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/retro", response_model=RetroSessionResponse)
async def read_retro_session(
    session: Session,
    week_start: Annotated[date | None, Query()] = None,
) -> RetroSessionResponse:
    return await get_retro_session(session, week_start or date.today())


@router.post("/retro/messages", response_model=RetroChatResponse)
async def post_retro_message(
    payload: RetroChatRequest,
    session: Session,
) -> RetroChatResponse:
    return await send_retro_message(
        session, payload.week_start or date.today(), payload.content
    )


@router.post("/retro/confirm", response_model=RetroConfirmResponse)
async def post_retro_confirm(
    payload: RetroConfirmRequest,
    session: Session,
) -> RetroConfirmResponse:
    return await confirm_next_week_plan(session, payload.week_start or date.today())
