from __future__ import annotations

import json
from pathlib import Path

import anyio.to_thread
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.core.config import get_settings
from graduate_entrance.db.session import session_factory
from graduate_entrance.models.recitation import RecitationItem
from graduate_entrance.recitation.service import deterministic_item_id


def _load_entries(seed_path: Path) -> list[dict[str, str]]:
    if not seed_path.is_file():
        return []
    entries: list[dict[str, str]] = json.loads(seed_path.read_text(encoding="utf-8"))
    return entries


async def import_recitations(session: AsyncSession, seed_path: Path) -> int:
    entries = await anyio.to_thread.run_sync(_load_entries, seed_path)
    if not entries:
        return 0
    existing = {
        (item.subject, item.title): item
        for item in (await session.execute(select(RecitationItem))).scalars().all()
    }
    imported = 0
    for order_index, entry in enumerate(entries):
        subject = str(entry.get("subject", "politics")).strip()
        title = str(entry.get("title", "")).strip()
        if not title or (subject, title) in existing:
            continue
        session.add(
            RecitationItem(
                id=deterministic_item_id(subject, title),
                subject=subject,
                category=str(entry.get("category", "")).strip() or "未分类",
                title=title,
                content_md=str(entry.get("content_md", "")),
                order_index=order_index,
            )
        )
        imported += 1
    await session.commit()
    return imported


async def import_configured_recitations() -> tuple[int, int]:
    async with session_factory() as session:
        imported = await import_recitations(session, get_settings().recitation_seed_path)
        total = (
            await session.execute(select(func.count()).select_from(RecitationItem))
        ).scalar_one()
        return imported, total


def main() -> None:
    import asyncio

    imported, total = asyncio.run(import_configured_recitations())
    print(f"Imported {imported} new recitation items, {total} total.")


if __name__ == "__main__":
    main()
