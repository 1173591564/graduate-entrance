from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.db.session import get_session
from graduate_entrance.schemas.syllabus import SyllabusTreeResponse
from graduate_entrance.syllabus.query import get_syllabus_tree

router = APIRouter(tags=["syllabus"])


async def get_syllabus_response(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SyllabusTreeResponse:
    return await get_syllabus_tree(session)


@router.get("/syllabus", response_model=SyllabusTreeResponse)
async def read_syllabus(
    syllabus: Annotated[SyllabusTreeResponse, Depends(get_syllabus_response)],
) -> SyllabusTreeResponse:
    return syllabus
