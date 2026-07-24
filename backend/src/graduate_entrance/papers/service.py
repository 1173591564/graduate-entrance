from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.models.papers import Paper, PaperAnnotation, PaperContent
from graduate_entrance.schemas.papers import (
    PaperAnnotationCreate,
    PaperAnnotationList,
    PaperAnnotationRead,
    PaperAnnotationUpdate,
    PaperContentResponse,
    PaperContentUpload,
    PaperGroup,
    PaperListResponse,
    PaperRead,
    PaperStatsResponse,
    PaperStatus,
    PaperStatusResult,
    PaperSyncItem,
    PaperSyncResult,
    PaperTocEntry,
    PaperTodayResponse,
)

PAPER_NAMESPACE = uuid.UUID("a7d1e6b2-0c44-5f39-9a7e-2b1d8c4f6e30")


def deterministic_paper_id(rel_path: str) -> uuid.UUID:
    return uuid.uuid5(PAPER_NAMESPACE, f"paper:{rel_path.strip()}")


def _title_from_path(rel_path: str) -> str:
    tail = rel_path.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
    if tail.lower().endswith(".pdf"):
        tail = tail[:-4]
    return tail.strip()


def _read(paper: Paper, *, has_content: bool = False) -> PaperRead:
    return PaperRead(
        id=paper.id,
        rel_path=paper.rel_path,
        title=paper.title,
        category=paper.category,
        size_bytes=paper.size_bytes,
        status=paper.status,
        has_file=paper.stored_filename is not None,
        has_content=has_content,
        started_on=paper.started_on,
        finished_on=paper.finished_on,
    )


async def _content_ids(session: AsyncSession) -> set[uuid.UUID]:
    rows = (await session.execute(select(PaperContent.paper_id))).scalars().all()
    return set(rows)


async def _has_content(session: AsyncSession, paper_id: uuid.UUID) -> bool:
    return (
        await session.execute(
            select(PaperContent.paper_id).where(PaperContent.paper_id == paper_id)
        )
    ).scalar_one_or_none() is not None


async def _stats(session: AsyncSession) -> PaperStatsResponse:
    rows = (
        await session.execute(
            select(Paper.status, func.count()).group_by(Paper.status)
        )
    ).all()
    counts = {row[0]: row[1] for row in rows}
    return PaperStatsResponse(
        total_count=sum(counts.values()),
        unread_count=counts.get("unread", 0),
        reading_count=counts.get("reading", 0),
        done_count=counts.get("done", 0),
    )


async def sync_papers(
    session: AsyncSession,
    items: list[PaperSyncItem],
) -> PaperSyncResult:
    existing = {
        paper.rel_path: paper
        for paper in (await session.execute(select(Paper))).scalars().all()
    }
    imported = 0
    updated = 0
    for order_index, item in enumerate(items):
        rel_path = item.rel_path.strip()
        if not rel_path:
            continue
        title = item.title.strip() or _title_from_path(rel_path)
        category = item.category.strip() or "未分类"
        paper = existing.get(rel_path)
        if paper is None:
            session.add(
                Paper(
                    id=deterministic_paper_id(rel_path),
                    rel_path=rel_path,
                    title=title,
                    category=category,
                    size_bytes=item.size_bytes,
                    order_index=order_index,
                )
            )
            imported += 1
        else:
            paper.title = title
            paper.category = category
            paper.size_bytes = item.size_bytes
            paper.order_index = order_index
            updated += 1
    await session.commit()
    total = (
        await session.execute(select(func.count()).select_from(Paper))
    ).scalar_one()
    return PaperSyncResult(imported=imported, updated=updated, total_count=total)


async def list_papers(session: AsyncSession) -> PaperListResponse:
    papers = (
        (
            await session.execute(
                select(Paper).order_by(Paper.category, Paper.order_index, Paper.title)
            )
        )
        .scalars()
        .all()
    )
    content_ids = await _content_ids(session)
    groups: list[PaperGroup] = []
    for paper in papers:
        if not groups or groups[-1].category != paper.category:
            groups.append(PaperGroup(category=paper.category, papers=[]))
        groups[-1].papers.append(_read(paper, has_content=paper.id in content_ids))
    return PaperListResponse(groups=groups, stats=await _stats(session))


async def paper_today(session: AsyncSession, as_of: date) -> PaperTodayResponse:
    reading = (
        await session.execute(
            select(Paper)
            .where(Paper.status == "reading")
            .order_by(Paper.order_index)
            .limit(1)
        )
    ).scalar_one_or_none()
    pick = reading
    if pick is None:
        pick = (
            await session.execute(
                select(Paper)
                .where(Paper.status == "unread")
                .order_by(Paper.order_index)
                .limit(1)
            )
        ).scalar_one_or_none()
    paper_read = None
    if pick is not None:
        paper_read = _read(pick, has_content=await _has_content(session, pick.id))
    return PaperTodayResponse(
        date=as_of,
        paper=paper_read,
        stats=await _stats(session),
    )


async def update_status(
    session: AsyncSession,
    paper_id: uuid.UUID,
    new_status: PaperStatus,
    as_of: date,
) -> PaperStatusResult:
    paper = await session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="论文不存在")
    paper.status = new_status
    if new_status == "reading" and paper.started_on is None:
        paper.started_on = as_of
    if new_status == "done":
        if paper.started_on is None:
            paper.started_on = as_of
        paper.finished_on = as_of
    if new_status == "unread":
        paper.started_on = None
        paper.finished_on = None
    await session.commit()
    await session.refresh(paper)
    return PaperStatusResult(
        paper=_read(paper, has_content=await _has_content(session, paper.id))
    )


async def paper_stats(session: AsyncSession) -> PaperStatsResponse:
    return await _stats(session)


async def get_paper(session: AsyncSession, paper_id: uuid.UUID) -> Paper:
    paper = await session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="论文不存在")
    return paper


async def attach_file(
    session: AsyncSession,
    paper_id: uuid.UUID,
    stored_filename: str,
) -> PaperRead:
    paper = await get_paper(session, paper_id)
    paper.stored_filename = stored_filename
    await session.commit()
    await session.refresh(paper)
    return _read(paper, has_content=await _has_content(session, paper.id))


def _toc(blocks: list[dict[str, Any]]) -> list[PaperTocEntry]:
    return [
        PaperTocEntry(
            title=str(block.get("md", "")),
            level=int(block.get("level", 0) or 0),
            block_index=index,
        )
        for index, block in enumerate(blocks)
        if block.get("type") == "heading"
    ]


async def upload_content(
    session: AsyncSession,
    paper_id: uuid.UUID,
    payload: PaperContentUpload,
) -> PaperContentResponse:
    paper = await get_paper(session, paper_id)
    blocks = [block.model_dump() for block in payload.blocks]
    content = await session.get(PaperContent, paper_id)
    if content is None:
        content = PaperContent(paper_id=paper_id, source=payload.source, blocks=blocks)
        session.add(content)
    else:
        content.source = payload.source
        content.blocks = blocks
    await session.commit()
    await session.refresh(content)
    return PaperContentResponse(
        paper=_read(paper, has_content=True),
        source=payload.source,
        blocks=payload.blocks,
        toc=_toc(blocks),
    )


async def read_content(
    session: AsyncSession,
    paper_id: uuid.UUID,
) -> PaperContentResponse:
    paper = await get_paper(session, paper_id)
    content = await session.get(PaperContent, paper_id)
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="论文正文尚未解析"
        )
    return PaperContentResponse(
        paper=_read(paper, has_content=True),
        source=content.source,
        blocks=content.blocks,
        toc=_toc(content.blocks),
    )


def _annotation_read(annotation: PaperAnnotation) -> PaperAnnotationRead:
    return PaperAnnotationRead(
        id=annotation.id,
        paper_id=annotation.paper_id,
        block_index=annotation.block_index,
        excerpt=annotation.excerpt,
        note=annotation.note,
        color=annotation.color,
        created_at=annotation.created_at,
    )


async def list_annotations(
    session: AsyncSession,
    paper_id: uuid.UUID,
) -> PaperAnnotationList:
    await get_paper(session, paper_id)
    annotations = (
        (
            await session.execute(
                select(PaperAnnotation)
                .where(PaperAnnotation.paper_id == paper_id)
                .order_by(PaperAnnotation.block_index, PaperAnnotation.created_at)
            )
        )
        .scalars()
        .all()
    )
    return PaperAnnotationList(
        annotations=[_annotation_read(annotation) for annotation in annotations]
    )


async def create_annotation(
    session: AsyncSession,
    paper_id: uuid.UUID,
    payload: PaperAnnotationCreate,
) -> PaperAnnotationRead:
    await get_paper(session, paper_id)
    content = await session.get(PaperContent, paper_id)
    if content is None or payload.block_index >= len(content.blocks):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="段落不存在"
        )
    annotation = PaperAnnotation(
        paper_id=paper_id,
        block_index=payload.block_index,
        excerpt=payload.excerpt,
        note=payload.note,
        color=payload.color,
    )
    session.add(annotation)
    await session.commit()
    await session.refresh(annotation)
    return _annotation_read(annotation)


async def update_annotation(
    session: AsyncSession,
    annotation_id: uuid.UUID,
    payload: PaperAnnotationUpdate,
) -> PaperAnnotationRead:
    annotation = await session.get(PaperAnnotation, annotation_id)
    if annotation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="标注不存在"
        )
    if payload.note is not None:
        annotation.note = payload.note
    if payload.color is not None:
        annotation.color = payload.color
    await session.commit()
    await session.refresh(annotation)
    return _annotation_read(annotation)


async def delete_annotation(
    session: AsyncSession,
    annotation_id: uuid.UUID,
) -> None:
    annotation = await session.get(PaperAnnotation, annotation_id)
    if annotation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="标注不存在"
        )
    await session.delete(annotation)
    await session.commit()
