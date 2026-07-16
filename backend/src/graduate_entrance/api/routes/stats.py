from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.db.session import get_session
from graduate_entrance.scheduling.service import get_weekly_stats
from graduate_entrance.schemas.scheduling import WeeklyStatsResponse

router = APIRouter(tags=["stats"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/stats/weekly", response_model=WeeklyStatsResponse)
async def read_weekly_stats(
    session: Session,
    start_date: Annotated[date | None, Query(alias="start")] = None,
    end_date: Annotated[date | None, Query(alias="end")] = None,
) -> WeeklyStatsResponse:
    return await get_weekly_stats(session, start_date, end_date)
