from __future__ import annotations

import json
import uuid
from pathlib import Path

import anyio.to_thread
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.core.config import get_settings
from graduate_entrance.db.session import session_factory
from graduate_entrance.models.vocab import VocabWord

VOCAB_NAMESPACE = uuid.UUID("6c2f9d34-9b1e-5a80-b0d3-6f4f2f0e9a11")


def deterministic_word_id(word: str) -> uuid.UUID:
    return uuid.uuid5(VOCAB_NAMESPACE, f"word:{word.strip().lower()}")


def _load_entries(seed_path: Path) -> list[dict[str, str | int]]:
    entries: list[dict[str, str | int]] = json.loads(seed_path.read_text(encoding="utf-8"))
    return entries


async def import_vocab(session: AsyncSession, seed_path: Path) -> int:
    entries = await anyio.to_thread.run_sync(_load_entries, seed_path)
    existing = set(
        (await session.execute(select(VocabWord.word))).scalars().all()
    )
    imported = 0
    for entry in entries:
        word = str(entry["word"]).strip()
        if not word or word in existing:
            continue
        existing.add(word)
        session.add(
            VocabWord(
                id=deterministic_word_id(word),
                word=word,
                meaning=str(entry.get("meaning", "")).strip(),
                book_page=int(entry.get("page", 0)),
                order_index=int(entry.get("page", 0)) * 100 + int(entry.get("index", 0)),
            )
        )
        imported += 1
    await session.commit()
    return imported


async def import_configured_vocab() -> tuple[int, int]:
    async with session_factory() as session:
        imported = await import_vocab(session, get_settings().vocab_seed_path)
        total = (
            await session.execute(select(func.count()).select_from(VocabWord))
        ).scalar_one()
        return imported, total


def main() -> None:
    import asyncio

    imported, total = asyncio.run(import_configured_vocab())
    print(f"Imported {imported} new vocab words, {total} total.")


if __name__ == "__main__":
    main()
