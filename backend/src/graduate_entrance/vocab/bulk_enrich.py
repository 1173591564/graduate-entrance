"""批量预生成词汇音标与例句：一次 LLM 调用处理一批单词，后台跑完全库。"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from graduate_entrance.ai import client as ai_client
from graduate_entrance.db import session as db_session
from graduate_entrance.models.vocab import VocabWord
from graduate_entrance.schemas.vocab import VocabBulkEnrichStatus

logger = logging.getLogger(__name__)

BATCH_SIZE = 20

BULK_ENRICH_PROMPT = (
    "你是考研英语词汇助手。给定多个单词（每行一个，含释义），返回严格的 JSON 对象"
    "（不要代码块、不要多余文字），格式："
    '{"items": [{"word": "原单词", "phonetic": "美式音标，含斜杠", '
    '"example_en": "一句考研难度的英文例句", "example_zh": "该例句的中文翻译"}, ...]}。'
    "items 必须覆盖输入的所有单词。"
)


@dataclass
class _BulkState:
    running: bool = False
    processed: int = 0
    failed: int = 0
    remaining: int = 0


_state = _BulkState()
_task: asyncio.Task[None] | None = None


def _status() -> VocabBulkEnrichStatus:
    return VocabBulkEnrichStatus(
        running=_state.running,
        processed=_state.processed,
        failed=_state.failed,
        remaining=_state.remaining,
    )


def parse_bulk_enrichment(raw: str) -> dict[str, dict[str, str]]:
    """Parse the LLM JSON (array or {\"items\": [...]}) keyed by casefolded word."""
    match = re.search(r"\[.*\]", raw, re.DOTALL) or re.search(
        r"\{.*\}", raw, re.DOTALL
    )
    if match is None:
        raise ValueError("AI 返回格式无法解析")
    try:
        data = json.loads(match.group(0))
    except ValueError as exc:
        raise ValueError("AI 返回格式无法解析") from exc
    if isinstance(data, dict):
        data = data.get("items")
    if not isinstance(data, list):
        raise ValueError("AI 返回格式无法解析")
    result: dict[str, dict[str, str]] = {}
    for entry in data:
        if not isinstance(entry, dict):
            continue
        word = entry.get("word")
        if not isinstance(word, str) or not word.strip():
            continue
        fields: dict[str, str] = {}
        for key in ("phonetic", "example_en", "example_zh"):
            value = entry.get(key)
            fields[key] = value.strip() if isinstance(value, str) else ""
        result[word.strip().casefold()] = fields
    return result


def _pending_filter() -> ColumnElement[bool]:
    return or_(VocabWord.phonetic == "", VocabWord.example_en == "")


async def _count_pending(session: AsyncSession) -> int:
    return (
        await session.execute(
            select(func.count()).select_from(VocabWord).where(_pending_filter())
        )
    ).scalar_one()


async def enrich_batch(session: AsyncSession, words: list[VocabWord]) -> int:
    """Enrich one batch of words with a single LLM call; returns updated count."""
    lines = "\n".join(f"{word.word}（释义：{word.meaning}）" for word in words)
    raw = await ai_client.complete_chat(
        [
            {"role": "system", "content": BULK_ENRICH_PROMPT},
            {"role": "user", "content": lines},
        ],
        response_format={"type": "json_object"},
    )
    parsed = parse_bulk_enrichment(raw)
    updated = 0
    for word in words:
        fields = parsed.get(word.word.strip().casefold())
        if fields is None:
            continue
        if fields["phonetic"] and not word.phonetic:
            word.phonetic = fields["phonetic"][:120]
        if fields["example_en"] and not word.example_en:
            word.example_en = fields["example_en"]
        if fields["example_zh"] and not word.example_zh:
            word.example_zh = fields["example_zh"]
        if word.phonetic and word.example_en:
            updated += 1
    await session.commit()
    return updated


async def run_bulk_enrich(
    factory: async_sessionmaker[AsyncSession] | None = None,
) -> VocabBulkEnrichStatus:
    """Loop through all words missing phonetic/example, one batch per LLM call."""
    factory = factory or db_session.session_factory
    skipped: set[UUID] = set()
    _state.processed = 0
    _state.failed = 0
    try:
        while True:
            async with factory() as session:
                _state.remaining = await _count_pending(session)
                words = (
                    (
                        await session.execute(
                            select(VocabWord)
                            .where(_pending_filter())
                            .where(VocabWord.id.not_in(skipped))
                            .order_by(VocabWord.order_index)
                            .limit(BATCH_SIZE)
                        )
                    )
                    .scalars()
                    .all()
                )
                if not words:
                    break
                try:
                    updated = await enrich_batch(session, list(words))
                except Exception:
                    logger.exception("bulk enrich batch failed")
                    updated = 0
                pending = [
                    word for word in words if not (word.phonetic and word.example_en)
                ]
                if pending and len(words) > 1:
                    # 整批/部分失败时按半批重试一次，降低单次格式错误的影响面
                    half = max(1, len(pending) // 2)
                    for chunk in (pending[:half], pending[half:]):
                        if not chunk:
                            continue
                        try:
                            updated += await enrich_batch(session, chunk)
                        except Exception:
                            logger.exception("bulk enrich retry failed")
                    pending = [
                        word
                        for word in words
                        if not (word.phonetic and word.example_en)
                    ]
                skipped.update(word.id for word in pending)
                _state.processed += updated
                _state.failed += len(pending)
        async with factory() as session:
            _state.remaining = await _count_pending(session)
    finally:
        _state.running = False
    return _status()


def start_bulk_enrich() -> VocabBulkEnrichStatus:
    """Start the background bulk enrichment if not already running."""
    global _task
    if _state.running:
        return _status()
    _state.running = True
    _task = asyncio.create_task(_run_in_background())
    return _status()


async def _run_in_background() -> None:
    try:
        await run_bulk_enrich()
    except Exception:
        logger.exception("bulk enrich task crashed")


def bulk_enrich_status() -> VocabBulkEnrichStatus:
    return _status()
