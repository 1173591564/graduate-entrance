from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.models import EssayMaterial
from graduate_entrance.schemas.essay import (
    EssayCategory,
    EssayMaterialCreateRequest,
    EssayMaterialListResponse,
    EssayMaterialRead,
    EssayMaterialUpdateRequest,
    ReciteResponse,
    ReciteResult,
)

FIRST_INTERVAL_DAYS = 2
MAX_INTERVAL_DAYS = 60


def _read(material: EssayMaterial) -> EssayMaterialRead:
    return EssayMaterialRead(
        id=material.id,
        title=material.title,
        category=EssayCategory(material.category),
        topic=material.topic,
        content_md=material.content_md,
        translation_md=material.translation_md,
        source=material.source,
        due_date=material.due_date,
        interval_days=material.interval_days,
        recite_count=material.recite_count,
        created_at=material.created_at,
        updated_at=material.updated_at,
    )


async def create_material(
    session: AsyncSession,
    payload: EssayMaterialCreateRequest,
    as_of: date,
) -> EssayMaterialRead:
    material = EssayMaterial(
        title=payload.title,
        category=payload.category.value,
        topic=payload.topic,
        content_md=payload.content_md,
        translation_md=payload.translation_md,
        source=payload.source,
        due_date=as_of,
    )
    session.add(material)
    await session.commit()
    await session.refresh(material)
    return _read(material)


async def list_materials(
    session: AsyncSession,
    category: EssayCategory | None,
    topic: str | None,
    query: str | None,
    due_only: bool,
    as_of: date,
) -> EssayMaterialListResponse:
    stmt = select(EssayMaterial)
    if category is not None:
        stmt = stmt.where(EssayMaterial.category == category.value)
    if topic:
        stmt = stmt.where(EssayMaterial.topic == topic)
    if query:
        pattern = f"%{query}%"
        stmt = stmt.where(
            or_(
                EssayMaterial.title.ilike(pattern),
                EssayMaterial.content_md.ilike(pattern),
                EssayMaterial.translation_md.ilike(pattern),
            ),
        )
    if due_only:
        stmt = stmt.where(
            EssayMaterial.due_date.is_not(None),
            EssayMaterial.due_date <= as_of,
        )
    stmt = stmt.order_by(EssayMaterial.created_at.desc())
    materials = (await session.scalars(stmt)).all()
    return EssayMaterialListResponse(
        total=len(materials),
        materials=[_read(material) for material in materials],
    )


async def _get_material(session: AsyncSession, material_id: UUID) -> EssayMaterial:
    material = await session.get(EssayMaterial, material_id)
    if material is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="素材不存在",
        )
    return material


async def update_material(
    session: AsyncSession,
    material_id: UUID,
    payload: EssayMaterialUpdateRequest,
) -> EssayMaterialRead:
    material = await _get_material(session, material_id)
    if payload.title is not None:
        material.title = payload.title
    if payload.category is not None:
        material.category = payload.category.value
    if payload.topic is not None:
        material.topic = payload.topic
    if payload.content_md is not None:
        material.content_md = payload.content_md
    if payload.translation_md is not None:
        material.translation_md = payload.translation_md
    if payload.source is not None:
        material.source = payload.source
    await session.commit()
    await session.refresh(material)
    return _read(material)


async def delete_material(session: AsyncSession, material_id: UUID) -> None:
    material = await _get_material(session, material_id)
    await session.delete(material)
    await session.commit()


async def recite_material(
    session: AsyncSession,
    material_id: UUID,
    result: ReciteResult,
    as_of: date,
) -> ReciteResponse:
    material = await _get_material(session, material_id)
    if result is ReciteResult.forgot:
        material.interval_days = 1
    elif material.interval_days <= 0:
        material.interval_days = FIRST_INTERVAL_DAYS
    else:
        material.interval_days = min(material.interval_days * 2, MAX_INTERVAL_DAYS)
    material.recite_count += 1
    material.due_date = as_of + timedelta(days=material.interval_days)
    await session.commit()
    await session.refresh(material)
    return ReciteResponse(material=_read(material), next_due=material.due_date)


async def due_count(session: AsyncSession, as_of: date) -> int:
    stmt = select(func.count()).select_from(EssayMaterial).where(
        EssayMaterial.due_date.is_not(None),
        EssayMaterial.due_date <= as_of,
    )
    return (await session.scalar(stmt)) or 0
