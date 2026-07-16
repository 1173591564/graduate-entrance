from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.db.session import get_session
from graduate_entrance.scheduling.ai_week import (
    generate_ai_week_plan,
    get_ai_week_advice,
    next_week_start,
)
from graduate_entrance.scheduling.service import persist_plan, preview_plan, reschedule_plan
from graduate_entrance.schemas.scheduling import (
    AiWeekAdvice,
    AiWeekPlanRequest,
    AiWeekPlanResponse,
    PlanGenerationRequest,
    PlanRescheduleRequest,
    PlanResponse,
)

router = APIRouter(prefix="/plan", tags=["plan"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.post("/preview", response_model=PlanResponse)
async def preview_generated_plan(
    payload: PlanGenerationRequest,
    session: Session,
) -> PlanResponse:
    return await preview_plan(session, payload)


@router.post("/generate", response_model=PlanResponse)
async def generate_plan(
    payload: PlanGenerationRequest,
    session: Session,
) -> PlanResponse:
    return await persist_plan(session, payload)


@router.post("/ai-week", response_model=AiWeekPlanResponse)
async def generate_ai_week(
    payload: AiWeekPlanRequest,
    session: Session,
) -> AiWeekPlanResponse:
    start_date = payload.start_date or next_week_start(date.today())
    return await generate_ai_week_plan(session, start_date)


@router.get("/ai-week", response_model=AiWeekAdvice)
async def read_ai_week(
    session: Session,
    week_start: Annotated[date | None, Query()] = None,
) -> AiWeekAdvice:
    advice = await get_ai_week_advice(
        session, week_start or next_week_start(date.today())
    )
    if advice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No AI week plan for the requested week",
        )
    return advice


@router.post("/reschedule", response_model=PlanResponse)
async def reschedule_generated_plan(
    payload: PlanRescheduleRequest,
    session: Session,
) -> PlanResponse:
    return await reschedule_plan(session, payload)
