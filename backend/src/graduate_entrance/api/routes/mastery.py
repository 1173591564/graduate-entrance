from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.db.session import get_session
from graduate_entrance.mastery.service import list_mastery_gaps, recompute_kp_mastery
from graduate_entrance.schemas.mastery import MasteryGapResponse, MasteryRecomputeResponse

router = APIRouter(tags=["mastery"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/mastery/gaps", response_model=MasteryGapResponse)
async def read_mastery_gaps(
    session: Session,
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
    recompute: Annotated[bool, Query()] = True,
) -> MasteryGapResponse:
    return await list_mastery_gaps(session, limit=limit, recompute=recompute)


@router.post("/mastery/recompute", response_model=MasteryRecomputeResponse)
async def trigger_recompute(session: Session) -> MasteryRecomputeResponse:
    recomputed = await recompute_kp_mastery(session)
    return MasteryRecomputeResponse(recomputed=recomputed)
