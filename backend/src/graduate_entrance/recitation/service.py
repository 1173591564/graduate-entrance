from __future__ import annotations

import uuid
from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.models.recitation import RecitationItem
from graduate_entrance.schemas.recitation import (
    RecitationGroup,
    RecitationImportItem,
    RecitationImportResult,
    RecitationListResponse,
    RecitationRead,
    RecitationStatsResponse,
    RecitationSubject,
    RecitationTodayResponse,
    ReciteGrade,
    ReciteResult,
)
from graduate_entrance.vocab.service import apply_vocab_srs

NEW_QUEUE_LIMIT = 3

RECITATION_NAMESPACE = uuid.UUID("f3b8a2d6-4e17-5c90-8b2a-9d6e1f0c3a55")


def deterministic_item_id(subject: str, title: str) -> uuid.UUID:
    return uuid.uuid5(RECITATION_NAMESPACE, f"recitation:{subject}:{title.strip()}")


def _read(item: RecitationItem, as_of: date) -> RecitationRead:
    return RecitationRead(
        id=item.id,
        subject=item.subject,
        category=item.category,
        title=item.title,
        content_md=item.content_md,
        recite_count=item.recite_count,
        last_recited_on=item.last_recited_on,
        recited_today=item.last_recited_on == as_of,
        ef=item.ef,
        interval_days=item.interval_days,
        reps=item.reps,
        due_date=item.due_date,
    )


async def _stats(
    session: AsyncSession,
    subject: RecitationSubject | None,
    as_of: date,
) -> RecitationStatsResponse:
    query = select(RecitationItem)
    if subject is not None:
        query = query.where(RecitationItem.subject == subject)
    items = (await session.execute(query)).scalars().all()
    return RecitationStatsResponse(
        total_count=len(items),
        recited_today=sum(1 for item in items if item.last_recited_on == as_of),
        never_recited=sum(1 for item in items if item.last_recited_on is None),
        due_count=sum(
            1
            for item in items
            if item.last_recited_on != as_of
            and item.due_date is not None
            and item.due_date <= as_of
        ),
    )


async def import_items(
    session: AsyncSession,
    items: list[RecitationImportItem],
) -> RecitationImportResult:
    existing = {
        (item.subject, item.title): item
        for item in (await session.execute(select(RecitationItem))).scalars().all()
    }
    imported = 0
    updated = 0
    for order_index, entry in enumerate(items):
        title = entry.title.strip()
        if not title:
            continue
        current = existing.get((entry.subject, title))
        if current is None:
            session.add(
                RecitationItem(
                    id=deterministic_item_id(entry.subject, title),
                    subject=entry.subject,
                    category=entry.category.strip() or "未分类",
                    title=title,
                    content_md=entry.content_md,
                    order_index=order_index,
                )
            )
            imported += 1
        else:
            current.category = entry.category.strip() or "未分类"
            current.content_md = entry.content_md
            current.order_index = order_index
            updated += 1
    await session.commit()
    total = (
        await session.execute(select(func.count()).select_from(RecitationItem))
    ).scalar_one()
    return RecitationImportResult(imported=imported, updated=updated, total_count=total)


async def list_items(
    session: AsyncSession,
    subject: RecitationSubject | None,
    as_of: date,
) -> RecitationListResponse:
    query = select(RecitationItem).order_by(
        RecitationItem.category,
        RecitationItem.order_index,
        RecitationItem.title,
    )
    if subject is not None:
        query = query.where(RecitationItem.subject == subject)
    items = (await session.execute(query)).scalars().all()
    groups: list[RecitationGroup] = []
    for item in items:
        if not groups or groups[-1].category != item.category:
            groups.append(RecitationGroup(category=item.category, items=[]))
        groups[-1].items.append(_read(item, as_of))
    return RecitationListResponse(
        groups=groups,
        stats=await _stats(session, subject, as_of),
    )


async def item_today(
    session: AsyncSession,
    subject: RecitationSubject | None,
    as_of: date,
) -> RecitationTodayResponse:
    base = select(RecitationItem)
    if subject is not None:
        base = base.where(RecitationItem.subject == subject)
    due_items = (
        (
            await session.execute(
                base.where(
                    RecitationItem.last_recited_on != as_of,
                    RecitationItem.due_date.is_not(None),
                    RecitationItem.due_date <= as_of,
                ).order_by(RecitationItem.due_date, RecitationItem.order_index)
            )
        )
        .scalars()
        .all()
    )
    new_items = (
        (
            await session.execute(
                base.where(RecitationItem.last_recited_on.is_(None))
                .order_by(RecitationItem.order_index)
                .limit(NEW_QUEUE_LIMIT)
            )
        )
        .scalars()
        .all()
    )
    queue = [_read(item, as_of) for item in [*due_items, *new_items]]
    pick = queue[0] if queue else None
    if pick is None:
        recited = (
            await session.execute(
                base.where(RecitationItem.last_recited_on == as_of)
                .order_by(RecitationItem.order_index)
                .limit(1)
            )
        ).scalar_one_or_none()
        if recited is not None:
            pick = _read(recited, as_of)
    return RecitationTodayResponse(
        date=as_of,
        item=pick,
        queue=queue,
        stats=await _stats(session, subject, as_of),
    )


async def recite(
    session: AsyncSession,
    item_id: uuid.UUID,
    as_of: date,
    undo: bool,
    grade: ReciteGrade | None = None,
) -> ReciteResult:
    item = await session.get(RecitationItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="背诵条目不存在")
    if undo:
        if item.last_recited_on == as_of:
            item.recite_count = max(0, item.recite_count - 1)
            item.last_recited_on = None
            item.due_date = as_of
    else:
        first_today = item.last_recited_on != as_of
        if first_today:
            item.recite_count += 1
        item.last_recited_on = as_of
        if first_today or grade is not None:
            next_ef, next_interval, next_reps = apply_vocab_srs(
                item.ef, item.interval_days, item.reps, grade or "mastered"
            )
            item.ef = next_ef
            item.interval_days = next_interval
            item.reps = next_reps
            item.due_date = as_of + timedelta(days=next_interval)
    await session.commit()
    await session.refresh(item)
    return ReciteResult(item=_read(item, as_of))


async def recitation_stats(
    session: AsyncSession,
    subject: RecitationSubject | None,
    as_of: date,
) -> RecitationStatsResponse:
    return await _stats(session, subject, as_of)
