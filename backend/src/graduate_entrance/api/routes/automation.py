from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.db.session import get_session
from graduate_entrance.models.automation import AutomationRun
from graduate_entrance.schemas.automation import (
    AutomationRunRead,
    AutomationRunsResponse,
)

router = APIRouter(prefix="/automation", tags=["automation"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/runs", response_model=AutomationRunsResponse)
async def list_automation_runs(
    session: Session,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AutomationRunsResponse:
    runs = (
        await session.scalars(
            select(AutomationRun)
            .order_by(AutomationRun.run_at.desc())
            .limit(limit)
        )
    ).all()
    return AutomationRunsResponse(
        runs=[
            AutomationRunRead(
                id=run.id,
                job_name=run.job_name,
                status=run.status,
                detail=run.detail,
                run_at=run.run_at,
            )
            for run in runs
        ]
    )
