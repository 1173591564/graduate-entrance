from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.db.session import get_session
from graduate_entrance.problems.insights import get_problem_insights
from graduate_entrance.scheduling.service import get_weekly_stats
from graduate_entrance.schemas.problems import ProblemInsightsResponse
from graduate_entrance.schemas.scheduling import WeeklyStatsResponse

router = APIRouter(tags=["stats"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/stats/insights", response_model=ProblemInsightsResponse)
async def read_problem_insights(
    session: Session,
    as_of: Annotated[date | None, Query()] = None,
) -> ProblemInsightsResponse:
    return await get_problem_insights(session, as_of or date.today())


@router.get("/stats/weekly", response_model=WeeklyStatsResponse)
async def read_weekly_stats(
    session: Session,
    start_date: Annotated[date | None, Query(alias="start")] = None,
    end_date: Annotated[date | None, Query(alias="end")] = None,
) -> WeeklyStatsResponse:
    return await get_weekly_stats(session, start_date, end_date)
