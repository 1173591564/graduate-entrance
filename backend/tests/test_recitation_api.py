from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from graduate_entrance.core.config import get_settings
from graduate_entrance.db.base import Base
from graduate_entrance.db.session import get_session
from graduate_entrance.main import app

IMPORT_PAYLOAD = {
    "items": [
        {
            "subject": "politics",
            "category": "马原·辩证法",
            "title": "对立统一规律",
            "content_md": "矛盾是事物发展的根本动力。",
        },
        {
            "subject": "politics",
            "category": "马原·认识论",
            "title": "实践与认识",
            "content_md": "实践是认识的基础。",
        },
        {
            "subject": "english",
            "category": "作文模板",
            "title": "图表作文开头",
            "content_md": "As is vividly depicted...",
        },
    ]
}


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    engine = create_async_engine("sqlite+aiosqlite://")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

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
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_import_is_idempotent(client: AsyncClient) -> None:
    first = await client.post("/api/recitations/import", json=IMPORT_PAYLOAD)
    assert first.status_code == 200
    assert first.json() == {"imported": 3, "updated": 0, "total_count": 3}

    second = await client.post("/api/recitations/import", json=IMPORT_PAYLOAD)
    assert second.json() == {"imported": 0, "updated": 3, "total_count": 3}


@pytest.mark.asyncio
async def test_list_filters_by_subject(client: AsyncClient) -> None:
    await client.post("/api/recitations/import", json=IMPORT_PAYLOAD)

    politics = (await client.get("/api/recitations", params={"subject": "politics"})).json()
    assert politics["stats"]["total_count"] == 2
    categories = [group["category"] for group in politics["groups"]]
    assert categories == sorted(categories)

    english = (await client.get("/api/recitations", params={"subject": "english"})).json()
    assert english["stats"]["total_count"] == 1


@pytest.mark.asyncio
async def test_today_returns_queue_of_pending_items(client: AsyncClient) -> None:
    await client.post("/api/recitations/import", json=IMPORT_PAYLOAD)

    today = (
        await client.get(
            "/api/recitations/today",
            params={"subject": "politics", "as_of": "2026-07-17"},
        )
    ).json()
    assert [item["title"] for item in today["queue"]] == ["对立统一规律", "实践与认识"]
    assert today["item"]["title"] == "对立统一规律"

    first_id = today["queue"][0]["id"]
    await client.post(
        f"/api/recitations/{first_id}/recite",
        json={"as_of": "2026-07-17", "grade": "mastered"},
    )
    today_after = (
        await client.get(
            "/api/recitations/today",
            params={"subject": "politics", "as_of": "2026-07-17"},
        )
    ).json()
    assert [item["title"] for item in today_after["queue"]] == ["实践与认识"]
    assert today_after["item"]["title"] == "实践与认识"
    assert today_after["stats"]["recited_today"] == 1

    await client.post(
        f"/api/recitations/{today_after['queue'][0]['id']}/recite",
        json={"as_of": "2026-07-17", "grade": "mastered"},
    )
    today_done = (
        await client.get(
            "/api/recitations/today",
            params={"subject": "politics", "as_of": "2026-07-17"},
        )
    ).json()
    assert today_done["queue"] == []
    assert today_done["item"]["recited_today"] is True


@pytest.mark.asyncio
async def test_grades_drive_srs_schedule(client: AsyncClient) -> None:
    await client.post("/api/recitations/import", json=IMPORT_PAYLOAD)
    listing = (await client.get("/api/recitations", params={"subject": "politics"})).json()
    items = [item for group in listing["groups"] for item in group["items"]]
    mastered_id, forgot_id = items[0]["id"], items[1]["id"]

    mastered = (
        await client.post(
            f"/api/recitations/{mastered_id}/recite",
            json={"as_of": "2026-07-17", "grade": "mastered"},
        )
    ).json()["item"]
    assert mastered["reps"] == 1
    assert mastered["interval_days"] == 1
    assert mastered["due_date"] == "2026-07-18"

    forgot = (
        await client.post(
            f"/api/recitations/{forgot_id}/recite",
            json={"as_of": "2026-07-17", "grade": "forgot"},
        )
    ).json()["item"]
    assert forgot["reps"] == 0
    assert forgot["due_date"] == "2026-07-18"
    assert forgot["ef"] < mastered["ef"]

    # 到期后重新进入队列，到期条目排在新条目前
    next_day = (
        await client.get(
            "/api/recitations/today",
            params={"subject": "politics", "as_of": "2026-07-18"},
        )
    ).json()
    assert {item["id"] for item in next_day["queue"]} == {mastered_id, forgot_id}
    assert next_day["stats"]["due_count"] == 2


@pytest.mark.asyncio
async def test_recite_and_undo(client: AsyncClient) -> None:
    await client.post("/api/recitations/import", json=IMPORT_PAYLOAD)
    listing = (await client.get("/api/recitations", params={"subject": "english"})).json()
    item = listing["groups"][0]["items"][0]

    recited = (
        await client.post(
            f"/api/recitations/{item['id']}/recite",
            json={"as_of": "2026-07-17"},
        )
    ).json()
    assert recited["item"]["recite_count"] == 1
    assert recited["item"]["last_recited_on"] == "2026-07-17"

    again = (
        await client.post(
            f"/api/recitations/{item['id']}/recite",
            json={"as_of": "2026-07-17"},
        )
    ).json()
    assert again["item"]["recite_count"] == 1

    undone = (
        await client.post(
            f"/api/recitations/{item['id']}/recite",
            json={"as_of": "2026-07-17", "undo": True},
        )
    ).json()
    assert undone["item"]["recite_count"] == 0
    assert undone["item"]["last_recited_on"] is None
    assert undone["item"]["due_date"] == "2026-07-17"


@pytest.mark.asyncio
async def test_recite_unknown_item_returns_404(client: AsyncClient) -> None:
    response = await client.post(
        "/api/recitations/00000000-0000-0000-0000-000000000000/recite",
        json={},
    )
    assert response.status_code == 404
