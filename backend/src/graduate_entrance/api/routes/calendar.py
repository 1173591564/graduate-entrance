from calendar import monthrange
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.db.session import get_session
from graduate_entrance.scheduling.service import get_calendar
from graduate_entrance.schemas.scheduling import CalendarResponse

router = APIRouter(tags=["calendar"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/calendar", response_model=CalendarResponse)
async def read_calendar(
    month: Annotated[str, Query(pattern=r"^\d{4}-\d{2}$")],
    session: Session,
) -> CalendarResponse:
    try:
        month_start = date.fromisoformat(f"{month}-01")
    except ValueError as exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="month must identify a valid calendar month",
        ) from exception
    month_end = date(
        month_start.year,
        month_start.month,
        monthrange(month_start.year, month_start.month)[1],
    )
    return await get_calendar(session, month, month_start, month_end)
