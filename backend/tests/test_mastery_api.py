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
from graduate_entrance.mastery.service import derive_target
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
POINT_STUDIED = uuid4()
POINT_UNTOUCHED = uuid4()


def _knowledge_point(
    kp_id: Any, chapter_id: Any, name: str, order: int, level: str
) -> KnowledgePoint:
    return KnowledgePoint(
        id=kp_id,
        chapter_id=chapter_id,
        section_id=None,
        syllabus_version_id=VERSION_ID,
        name=name,
        slug=f"kp-{order}-{str(kp_id)[:8]}",
        requirement_raw="掌握",
        requirement_level=level,
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
        session.add(_knowledge_point(POINT_STUDIED, chapter_id, "重要极限", 1, "mastery"))
        session.add(_knowledge_point(POINT_UNTOUCHED, chapter_id, "泰勒公式", 2, "mastery"))
        await session.commit()

        session.add(
            ScheduledTask(
                id=uuid4(),
                subject_id=MATH_ID,
                knowledge_point_id=POINT_STUDIED,
                phase_name="基础",
                subject_name="数学一",
                knowledge_point_name="重要极限",
                title="学习重要极限",
                task_type="reading",
                planned_date=date(2026, 7, 10),
                est_minutes=60,
                status="completed",
                actual_minutes=55,
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


def test_derive_target_scales_with_goal_ratio() -> None:
    # mastery requirement, full ambition
    assert derive_target("mastery", 1.0) == 95.0
    # modest goal drags the target down
    assert derive_target("mastery", 0.5) == 47.5
    # unknown level falls back to the default base
    assert derive_target("???", 1.0) == 70.0


@pytest.mark.asyncio
async def test_recompute_and_gaps_rank_by_largest_gap(client: AsyncClient) -> None:
    await client.put(
        "/api/profile/goals",
        json={"goals": [{"subject_id": str(MATH_ID), "target_score": 150, "full_score": 150}]},
    )

    recompute = await client.post("/api/mastery/recompute")
    assert recompute.status_code == 200
    assert recompute.json()["recomputed"] == 2

    response = await client.get("/api/mastery/gaps")
    assert response.status_code == 200
    body = response.json()
    assert body["knowledge_point_total"] == 2
    # both KPs are below a full-ambition mastery target -> both are gaps
    assert body["gap_count"] == 2

    items = body["items"]
    # untouched KP (mastery 0) has the larger gap and must rank first
    assert items[0]["knowledge_point_id"] == str(POINT_UNTOUCHED)
    assert items[0]["target"] == 95.0
    assert items[0]["mastery"] == 0.0
    assert items[0]["gap"] == 95.0
    assert items[0]["studied"] is False

    studied = next(
        item for item in items if item["knowledge_point_id"] == str(POINT_STUDIED)
    )
    assert studied["studied"] is True
    assert studied["mastery"] > 0.0
    assert studied["gap"] < items[0]["gap"]


@pytest.mark.asyncio
async def test_gaps_recompute_flag_defaults_true(client: AsyncClient) -> None:
    # without an explicit recompute call the endpoint still populates rows
    response = await client.get("/api/mastery/gaps?limit=5")
    assert response.status_code == 200
    assert response.json()["knowledge_point_total"] == 2
