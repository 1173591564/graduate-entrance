from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.db.session import get_session
from graduate_entrance.scheduling.service import persist_plan, preview_plan, reschedule_plan
from graduate_entrance.schemas.scheduling import (
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


@router.post("/reschedule", response_model=PlanResponse)
async def reschedule_generated_plan(
    payload: PlanRescheduleRequest,
    session: Session,
) -> PlanResponse:
    return await reschedule_plan(session, payload)
