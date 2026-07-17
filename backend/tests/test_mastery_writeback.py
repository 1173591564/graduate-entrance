from collections.abc import AsyncIterator
from datetime import date
from typing import Any
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
from graduate_entrance.models.syllabus import (
    Chapter,
    KnowledgePoint,
    Subject,
    SyllabusModule,
    SyllabusVersion,
)

MATH_ID = uuid4()
VERSION_ID = uuid4()
POINT = uuid4()
POINT_OTHER = uuid4()
TASK_ID = uuid4()


def _kp(kp_id: Any, chapter_id: Any, name: str, order: int) -> KnowledgePoint:
    return KnowledgePoint(
        id=kp_id,
        chapter_id=chapter_id,
        section_id=None,
        syllabus_version_id=VERSION_ID,
        name=name,
        slug=f"kp-{order}-{str(kp_id)[:8]}",
        requirement_raw="掌握",
        requirement_level="mastery",
        requirement_actions=[],
        order=order,
    )


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    engine = create_async_engine("sqlite+aiosqlite://")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        session.add(
            SyllabusVersion(
                id=VERSION_ID,
                source_name="test",
                source_checksum="0" * 64,
                row_count=2,
                imported_at=date(2026, 1, 1),
            )
        )
        session.add(Subject(id=MATH_ID, code="math1", name="数学一", order=1))
        module_id = uuid4()
        chapter_id = uuid4()
        session.add(
            SyllabusModule(id=module_id, subject_id=MATH_ID, name="高数", slug="gs", order=1)
        )
        session.add(Chapter(id=chapter_id, module_id=module_id, name="极限", slug="jx", order=1))
        session.add(_kp(POINT, chapter_id, "重要极限", 1))
        session.add(_kp(POINT_OTHER, chapter_id, "泰勒公式", 2))
        session.add(
            ScheduledTask(
                id=TASK_ID,
                subject_id=MATH_ID,
                knowledge_point_id=POINT,
                phase_name="基础",
                subject_name="数学一",
                knowledge_point_name="重要极限",
                title="学习重要极限",
                task_type="reading",
                planned_date=date(2026, 7, 10),
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
async def test_completing_task_writes_back_mastery(client: AsyncClient) -> None:
    # No signal yet: reading persisted rows without recompute yields nothing.
    empty = await client.get("/api/mastery/gaps?recompute=false")
    assert empty.status_code == 200
    assert empty.json()["knowledge_point_total"] == 0

    done = await client.post(
        f"/api/tasks/{TASK_ID}/done", json={"actual_minutes": 50}
    )
    assert done.status_code == 200

    # The check-in signal wrote back mastery for exactly the task's KP,
    # without any explicit recompute call.
    gaps = await client.get("/api/mastery/gaps?recompute=false")
    body = gaps.json()
    assert body["knowledge_point_total"] == 1
    item = body["items"][0]
    assert item["knowledge_point_id"] == str(POINT)
    assert item["studied"] is True
    assert item["mastery"] > 0.0
