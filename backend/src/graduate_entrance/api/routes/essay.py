from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.db.session import get_session
from graduate_entrance.essay.service import (
    create_material,
    delete_material,
    list_materials,
    recite_material,
    update_material,
)
from graduate_entrance.schemas.essay import (
    EssayCategory,
    EssayMaterialCreateRequest,
    EssayMaterialListResponse,
    EssayMaterialRead,
    EssayMaterialUpdateRequest,
    ReciteRequest,
    ReciteResponse,
)

router = APIRouter(tags=["essay"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/essay/materials", response_model=EssayMaterialListResponse)
async def get_materials(
    session: Session,
    category: Annotated[EssayCategory | None, Query()] = None,
    topic: Annotated[str | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
    due_only: Annotated[bool, Query()] = False,
    as_of: Annotated[date | None, Query()] = None,
) -> EssayMaterialListResponse:
    return await list_materials(session, category, topic, q, due_only, as_of or date.today())


@router.post("/essay/materials", response_model=EssayMaterialRead)
async def post_material(
    payload: EssayMaterialCreateRequest,
    session: Session,
    as_of: Annotated[date | None, Query()] = None,
) -> EssayMaterialRead:
    return await create_material(session, payload, as_of or date.today())


@router.patch("/essay/materials/{material_id}", response_model=EssayMaterialRead)
async def patch_material(
    material_id: UUID,
    payload: EssayMaterialUpdateRequest,
    session: Session,
) -> EssayMaterialRead:
    return await update_material(session, material_id, payload)


@router.delete("/essay/materials/{material_id}", status_code=204)
async def remove_material(material_id: UUID, session: Session) -> None:
    await delete_material(session, material_id)


@router.post("/essay/materials/{material_id}/recite", response_model=ReciteResponse)
async def post_recite(
    material_id: UUID,
    payload: ReciteRequest,
    session: Session,
    as_of: Annotated[date | None, Query()] = None,
) -> ReciteResponse:
    return await recite_material(session, material_id, payload.result, as_of or date.today())
