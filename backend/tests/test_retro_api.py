from collections.abc import AsyncIterator
from datetime import date
from uuid import uuid4

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
from graduate_entrance.models.scheduling import ScheduledTask
from graduate_entrance.models.syllabus import Subject

MATH_ID = uuid4()
WEEK_START = date(2026, 7, 13)


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    engine = create_async_engine("sqlite+aiosqlite://")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        session.add(Subject(id=MATH_ID, code="math1", name="数学一", order=1))
        session.add(
            ScheduledTask(
                id=uuid4(),
                subject_id=MATH_ID,
                phase_name="基础",
                subject_name="数学一",
                knowledge_point_name="重要极限",
                title="学习重要极限",
                task_type="reading",
                planned_date=date(2026, 7, 14),
                est_minutes=60,
                status="completed",
                actual_minutes=50,
            )
        )
        session.add(
            ScheduledTask(
                id=uuid4(),
                subject_id=MATH_ID,
                phase_name="基础",
                subject_name="数学一",
                knowledge_point_name="等价无穷小",
                title="学习等价无穷小",
                task_type="reading",
                planned_date=date(2026, 7, 15),
                est_minutes=60,
                status="planned",
            )
        )
        await session.commit()

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
async def test_retro_session_returns_week_context(client: AsyncClient) -> None:
    response = await client.get("/api/retro?week_start=2026-07-16")
    assert response.status_code == 200
    body = response.json()
    assert body["context"]["week_start"] == "2026-07-13"
    assert body["context"]["week_end"] == "2026-07-19"
    assert body["context"]["total_tasks"] == 2
    assert body["context"]["completed_tasks"] == 1
    assert body["context"]["completed_minutes"] == 50
    assert body["messages"] == []
    subject_names = [entry["subject_name"] for entry in body["context"]["subjects"]]
    assert "数学一" in subject_names


@pytest.mark.asyncio
async def test_retro_chat_persists_history(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: list[list[dict[str, str]]] = []

    async def fake_complete_chat(messages: list[dict[str, str]], settings: object) -> str:
        captured.append(messages)
        return "本周执行率不错，下周建议加大等价无穷小的练习量。"

    monkeypatch.setattr("graduate_entrance.ai.client.complete_chat", fake_complete_chat)

    response = await client.post(
        "/api/retro/messages",
        json={"week_start": "2026-07-16", "content": "这周数学有点吃力，下周想多留点时间"},
    )
    assert response.status_code == 200
    messages = response.json()["messages"]
    assert [entry["role"] for entry in messages] == ["user", "assistant"]
    assert "等价无穷小" in messages[1]["content"]

    sent = captured[0]
    assert sent[0]["role"] == "system"
    assert "执行数据" in sent[1]["content"]
    assert sent[-1]["content"] == "这周数学有点吃力，下周想多留点时间"

    followup = await client.post(
        "/api/retro/messages",
        json={"week_start": "2026-07-16", "content": "好，那政治怎么办"},
    )
    followup_messages = followup.json()["messages"]
    assert len(followup_messages) == 4
    assert "这周数学有点吃力" in str(captured[1])

    reloaded = await client.get("/api/retro?week_start=2026-07-16")
    assert len(reloaded.json()["messages"]) == 4


@pytest.mark.asyncio
async def test_retro_chat_rejects_empty_content(client: AsyncClient) -> None:
    response = await client.post(
        "/api/retro/messages",
        json={"week_start": "2026-07-16", "content": ""},
    )
    assert response.status_code == 422
