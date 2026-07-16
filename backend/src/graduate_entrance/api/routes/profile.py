from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.db.session import get_session
from graduate_entrance.profile.service import get_study_profile, list_goals, upsert_goals
from graduate_entrance.schemas.profile import (
    GoalsResponse,
    GoalsUpdateRequest,
    StudyProfileResponse,
)

router = APIRouter(tags=["profile"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/profile", response_model=StudyProfileResponse)
async def read_study_profile(
    session: Session,
    as_of: Annotated[date | None, Query()] = None,
) -> StudyProfileResponse:
    return await get_study_profile(session, as_of or date.today())


@router.get("/profile/goals", response_model=GoalsResponse)
async def read_goals(session: Session) -> GoalsResponse:
    return await list_goals(session)


@router.put("/profile/goals", response_model=GoalsResponse)
async def update_goals(payload: GoalsUpdateRequest, session: Session) -> GoalsResponse:
    return await upsert_goals(session, payload.goals)
