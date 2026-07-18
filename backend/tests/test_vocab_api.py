import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from graduate_entrance.db.base import Base
from graduate_entrance.db.session import get_session
from graduate_entrance.main import app
from graduate_entrance.vocab.importer import import_vocab
from graduate_entrance.vocab.service import apply_vocab_srs

SEED_ENTRIES = [
    {"word": "radiate", "meaning": "vt. 散发", "page": 1, "index": 1},
    {"word": "abandon", "meaning": "vt. 放弃", "page": 1, "index": 2},
    {"word": "vague", "meaning": "adj. 模糊的", "page": 2, "index": 1},
]


@pytest_asyncio.fixture
async def client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    engine = create_async_engine("sqlite+aiosqlite://")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    seed_path = tmp_path / "words.json"
    seed_path.write_text(json.dumps(SEED_ENTRIES, ensure_ascii=False), encoding="utf-8")
    async with session_factory() as session:
        imported = await import_vocab(session, seed_path)
        assert imported == 3
        # importing again is a no-op
        assert await import_vocab(session, seed_path) == 0

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": "Bearer local-development-only"},
    ) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_vocab_today_lists_new_words_in_book_order(client: AsyncClient) -> None:
    response = await client.get("/api/vocab/today", params={"as_of": "2026-07-20"})
    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 3
    assert body["learned_count"] == 0
    assert body["due_count"] == 0
    assert body["due_words"] == []
    assert [word["word"] for word in body["new_words"]] == ["radiate", "abandon", "vague"]


@pytest.mark.asyncio
async def test_vocab_today_respects_new_limit(client: AsyncClient) -> None:
    response = await client.get(
        "/api/vocab/today", params={"as_of": "2026-07-20", "new_limit": 1}
    )
    assert response.status_code == 200
    body = response.json()
    assert [word["word"] for word in body["new_words"]] == ["radiate"]


@pytest.mark.asyncio
async def test_grading_schedules_review_and_moves_word_out_of_new(
    client: AsyncClient,
) -> None:
    today = await client.get("/api/vocab/today", params={"as_of": "2026-07-20"})
    word_id = today.json()["new_words"][0]["id"]

    graded = await client.post(
        f"/api/vocab/{word_id}/grade",
        json={"grade": "mastered", "as_of": "2026-07-20"},
    )
    assert graded.status_code == 200
    body = graded.json()
    assert body["grade"] == "mastered"
    assert body["due_date"] == "2026-07-21"
    assert body["word"]["reps"] == 1

    refreshed = await client.get("/api/vocab/today", params={"as_of": "2026-07-20"})
    refreshed_body = refreshed.json()
    assert refreshed_body["learned_count"] == 1
    assert refreshed_body["reviewed_today_count"] == 1
    assert word_id not in [word["id"] for word in refreshed_body["new_words"]]

    next_day = await client.get("/api/vocab/today", params={"as_of": "2026-07-21"})
    next_body = next_day.json()
    assert next_body["due_count"] == 1
    assert [word["id"] for word in next_body["due_words"]] == [word_id]


@pytest.mark.asyncio
async def test_forgot_resets_reps(client: AsyncClient) -> None:
    today = await client.get("/api/vocab/today", params={"as_of": "2026-07-20"})
    word_id = today.json()["new_words"][0]["id"]

    await client.post(
        f"/api/vocab/{word_id}/grade",
        json={"grade": "mastered", "as_of": "2026-07-20"},
    )
    forgot = await client.post(
        f"/api/vocab/{word_id}/grade",
        json={"grade": "forgot", "as_of": "2026-07-21"},
    )
    body = forgot.json()
    assert body["word"]["reps"] == 0
    assert body["due_date"] == "2026-07-22"


def test_srs_mastered_climbs_ebbinghaus_ladder() -> None:
    ef, interval, reps = 2.5, 0, 0
    intervals = []
    for _ in range(6):
        ef, interval, reps = apply_vocab_srs(ef, interval, reps, "mastered")
        intervals.append(interval)
    assert intervals[:5] == [1, 2, 4, 7, 15]
    assert intervals[5] > 15


def test_srs_vague_grows_slowly() -> None:
    ef, interval, reps = apply_vocab_srs(2.5, 0, 0, "vague")
    assert (interval, reps) == (1, 1)
    ef, interval, reps = apply_vocab_srs(ef, 10, 3, "vague")
    assert interval == 12
    assert reps == 4


def test_srs_forgot_resets() -> None:
    ef, interval, reps = apply_vocab_srs(2.5, 15, 5, "forgot")
    assert (interval, reps) == (1, 0)
    assert ef < 2.5


@pytest.mark.asyncio
async def test_grade_unknown_word_returns_404(client: AsyncClient) -> None:
    response = await client.post(
        "/api/vocab/00000000-0000-0000-0000-000000000000/grade",
        json={"grade": "mastered"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_vocab_stats(client: AsyncClient) -> None:
    response = await client.get("/api/vocab/stats", params={"as_of": "2026-07-20"})
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "total_count": 3,
        "learned_count": 0,
        "due_count": 0,
        "mastered_count": 0,
    }


@pytest.mark.asyncio
async def test_dictation_lists_words_reviewed_that_day(client: AsyncClient) -> None:
    today = await client.get("/api/vocab/today", params={"as_of": "2026-07-20"})
    word_id = today.json()["new_words"][0]["id"]
    await client.post(
        f"/api/vocab/{word_id}/grade",
        json={"grade": "mastered", "as_of": "2026-07-20"},
    )

    response = await client.get("/api/vocab/dictation", params={"as_of": "2026-07-20"})
    assert response.status_code == 200
    body = response.json()
    assert body["date"] == "2026-07-20"
    assert [word["id"] for word in body["words"]] == [word_id]

    empty = await client.get("/api/vocab/dictation", params={"as_of": "2026-07-21"})
    assert empty.json()["words"] == []


@pytest.mark.asyncio
async def test_enrich_generates_and_caches(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[object] = []

    async def fake_complete_chat(
        messages: list[dict[str, object]], settings: object = None
    ) -> str:
        calls.append(messages)
        return (
            '{"phonetic": "/ˈreɪdieɪt/", "example_en": "Heat radiates from the sun.",'
            ' "example_zh": "热量从太阳辐射出来。"}'
        )

    monkeypatch.setattr("graduate_entrance.ai.client.complete_chat", fake_complete_chat)

    today = await client.get("/api/vocab/today", params={"as_of": "2026-07-20"})
    word_id = today.json()["new_words"][0]["id"]

    first = await client.post(f"/api/vocab/{word_id}/enrich")
    assert first.status_code == 200
    body = first.json()
    assert body["phonetic"] == "/ˈreɪdieɪt/"
    assert body["example_en"] == "Heat radiates from the sun."
    assert body["example_zh"] == "热量从太阳辐射出来。"
    assert len(calls) == 1

    second = await client.post(f"/api/vocab/{word_id}/enrich")
    assert second.status_code == 200
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_enrich_unknown_word_returns_404(client: AsyncClient) -> None:
    response = await client.post(
        "/api/vocab/00000000-0000-0000-0000-000000000000/enrich"
    )
    assert response.status_code == 404
