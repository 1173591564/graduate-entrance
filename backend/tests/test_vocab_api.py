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
