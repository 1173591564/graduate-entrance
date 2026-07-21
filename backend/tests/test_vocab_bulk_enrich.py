import json
from pathlib import Path

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from graduate_entrance.db.base import Base
from graduate_entrance.models.vocab import VocabWord
from graduate_entrance.vocab.bulk_enrich import (
    _is_transient,
    parse_bulk_enrichment,
    run_bulk_enrich,
)
from graduate_entrance.vocab.importer import import_vocab

SEED_ENTRIES = [
    {"word": "radiate", "meaning": "vt. 散发", "page": 1, "index": 1},
    {"word": "abandon", "meaning": "vt. 放弃", "page": 1, "index": 2},
    {"word": "vague", "meaning": "adj. 模糊的", "page": 2, "index": 1},
]


def test_parse_bulk_enrichment_maps_by_word() -> None:
    raw = (
        "以下是结果：\n"
        '[{"word": "Radiate", "phonetic": "/x/", "example_en": "A.", "example_zh": "甲。"},'
        ' {"word": "", "phonetic": "/y/"}, "junk",'
        ' {"word": "vague", "phonetic": "/z/", "example_en": "B.", "example_zh": "乙。"}]'
    )
    parsed = parse_bulk_enrichment(raw)
    assert parsed["radiate"] == {
        "phonetic": "/x/",
        "example_en": "A.",
        "example_zh": "甲。",
    }
    assert parsed["vague"]["phonetic"] == "/z/"
    assert len(parsed) == 2


def test_parse_bulk_enrichment_accepts_items_object() -> None:
    raw = (
        '{"items": [{"word": "radiate", "phonetic": "/x/",'
        ' "example_en": "A.", "example_zh": "甲。"}]}'
    )
    parsed = parse_bulk_enrichment(raw)
    assert parsed["radiate"]["phonetic"] == "/x/"


def test_parse_bulk_enrichment_rejects_non_array() -> None:
    with pytest.raises(ValueError):
        parse_bulk_enrichment('{"word": "radiate"}')


def test_is_transient_classification() -> None:
    # complete_chat 把 provider 503/超时包成 HTTPException(502)
    assert _is_transient(HTTPException(status_code=502))
    assert _is_transient(HTTPException(status_code=503))
    assert _is_transient(HTTPException(status_code=429))
    assert _is_transient(httpx.ConnectError("boom"))
    # 非瞬时错误（如格式解析失败、4xx 客户端错误）不重试
    assert not _is_transient(HTTPException(status_code=400))
    assert not _is_transient(ValueError("AI 返回格式无法解析"))


@pytest.mark.asyncio
async def test_run_bulk_enrich_fills_words_and_skips_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    seed_path = tmp_path / "words.json"
    seed_path.write_text(json.dumps(SEED_ENTRIES, ensure_ascii=False), encoding="utf-8")
    async with factory() as session:
        assert await import_vocab(session, seed_path) == 3

    calls: list[str] = []

    async def fake_complete_chat(
        messages: list[dict[str, object]],
        settings: object = None,
        response_format: object = None,
    ) -> str:
        calls.append(str(messages[-1]["content"]))
        return json.dumps(
            [
                {
                    "word": "radiate",
                    "phonetic": "/ˈreɪdieɪt/",
                    "example_en": "Heat radiates from the sun.",
                    "example_zh": "热量从太阳辐射出来。",
                },
                {
                    "word": "abandon",
                    "phonetic": "/əˈbændən/",
                    "example_en": "They abandoned the plan.",
                    "example_zh": "他们放弃了计划。",
                },
                # vague 缺失：应计入 failed 并跳过，不会死循环
            ],
            ensure_ascii=False,
        )

    monkeypatch.setattr(
        "graduate_entrance.ai.client.complete_chat", fake_complete_chat
    )

    status = await run_bulk_enrich(factory)
    # 首批 + 针对未覆盖词（vague）的半批重试
    assert len(calls) == 2
    assert status.running is False
    assert status.processed == 2
    assert status.failed == 1
    assert status.remaining == 1

    async with factory() as session:
        words = (await session.execute(select(VocabWord))).scalars().all()
    by_word = {word.word: word for word in words}
    assert by_word["radiate"].phonetic == "/ˈreɪdieɪt/"
    assert by_word["abandon"].example_zh == "他们放弃了计划。"
    assert by_word["vague"].phonetic == ""
    await engine.dispose()
