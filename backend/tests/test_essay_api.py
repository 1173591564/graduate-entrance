from collections.abc import AsyncIterator

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
    await engine.dispose()


async def create_material(client: AsyncClient, title: str = "环保话题金句") -> dict:
    response = await client.post(
        "/api/essay/materials?as_of=2026-07-16",
        json={
            "title": title,
            "category": "sentence",
            "topic": "environment",
            "content_md": "Only by acting now can we protect the environment.",
            "translation_md": "只有现在行动才能保护环境。",
            "source": "范文 2024",
        },
    )
    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio
async def test_material_crud_and_filters(client: AsyncClient) -> None:
    material = await create_material(client)
    assert material["due_date"] == "2026-07-16"
    assert material["recite_count"] == 0

    other = await client.post(
        "/api/essay/materials",
        json={
            "title": "科技模板",
            "category": "template",
            "topic": "technology",
            "content_md": "With the rapid development of ...",
        },
    )
    assert other.status_code == 200

    listing = await client.get("/api/essay/materials")
    assert listing.status_code == 200
    assert listing.json()["total"] == 2

    filtered = await client.get("/api/essay/materials?category=template")
    assert filtered.json()["total"] == 1
    assert filtered.json()["materials"][0]["title"] == "科技模板"

    searched = await client.get("/api/essay/materials?q=environment")
    assert searched.json()["total"] == 1

    updated = await client.patch(
        f"/api/essay/materials/{material['id']}",
        json={"topic": "green", "translation_md": "只有立即行动。"},
    )
    assert updated.status_code == 200
    assert updated.json()["topic"] == "green"
    assert updated.json()["translation_md"] == "只有立即行动。"

    deleted = await client.delete(f"/api/essay/materials/{material['id']}")
    assert deleted.status_code == 204
    remaining = await client.get("/api/essay/materials")
    assert remaining.json()["total"] == 1


@pytest.mark.asyncio
async def test_recite_schedule_and_due_filter(client: AsyncClient) -> None:
    material = await create_material(client)

    due = await client.get("/api/essay/materials?due_only=true&as_of=2026-07-16")
    assert due.json()["total"] == 1

    first = await client.post(
        f"/api/essay/materials/{material['id']}/recite?as_of=2026-07-16",
        json={"result": "remembered"},
    )
    assert first.status_code == 200
    assert first.json()["next_due"] == "2026-07-18"
    assert first.json()["material"]["interval_days"] == 2
    assert first.json()["material"]["recite_count"] == 1

    not_due = await client.get("/api/essay/materials?due_only=true&as_of=2026-07-17")
    assert not_due.json()["total"] == 0

    second = await client.post(
        f"/api/essay/materials/{material['id']}/recite?as_of=2026-07-18",
        json={"result": "remembered"},
    )
    assert second.json()["material"]["interval_days"] == 4
    assert second.json()["next_due"] == "2026-07-22"

    forgot = await client.post(
        f"/api/essay/materials/{material['id']}/recite?as_of=2026-07-22",
        json={"result": "forgot"},
    )
    assert forgot.json()["material"]["interval_days"] == 1
    assert forgot.json()["next_due"] == "2026-07-23"


@pytest.mark.asyncio
async def test_recite_missing_material_returns_404(client: AsyncClient) -> None:
    response = await client.post(
        "/api/essay/materials/00000000-0000-0000-0000-000000000000/recite",
        json={"result": "remembered"},
    )
    assert response.status_code == 404
