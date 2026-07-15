from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.db.session import get_session
from graduate_entrance.scheduling.service import complete_task, get_today
from graduate_entrance.schemas.scheduling import (
    PlanTaskRead,
    TaskCompletionRequest,
    TodayResponse,
)

router = APIRouter(tags=["daily"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/today", response_model=TodayResponse)
async def read_today(
    session: Session,
    target_date: Annotated[date | None, Query(alias="date")] = None,
) -> TodayResponse:
    return await get_today(session, target_date or date.today())


@router.post("/tasks/{task_id}/done", response_model=PlanTaskRead)
async def mark_task_done(
    task_id: UUID,
    payload: TaskCompletionRequest,
    session: Session,
) -> PlanTaskRead:
    return await complete_task(session, task_id, payload.actual_minutes)
