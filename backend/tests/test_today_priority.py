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
from graduate_entrance.mastery.service import task_priority
from graduate_entrance.models.problems import Problem
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
TASK_STUDIED = uuid4()
TASK_UNTOUCHED = uuid4()
TODAY = date(2026, 7, 20)


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


def _planned(
    task_id: Any, kp_id: Any, name: str, minutes: int, order: int
) -> ScheduledTask:
    return ScheduledTask(
        id=task_id,
        subject_id=MATH_ID,
        knowledge_point_id=kp_id,
        phase_name="基础",
        subject_name="数学一",
        knowledge_point_name=name,
        title=f"学习{name}",
        task_type="reading",
        planned_date=TODAY,
        est_minutes=minutes,
        status="planned",
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
        session.add(_kp(POINT_STUDIED, chapter_id, "重要极限", 1))
        session.add(_kp(POINT_UNTOUCHED, chapter_id, "泰勒公式", 2))
        # A prior completed task lifts POINT_STUDIED mastery (smaller gap).
        session.add(
            ScheduledTask(
                id=uuid4(),
                subject_id=MATH_ID,
                knowledge_point_id=POINT_STUDIED,
                phase_name="基础",
                subject_name="数学一",
                knowledge_point_name="重要极限",
                title="学习重要极限(旧)",
                task_type="reading",
                planned_date=date(2026, 7, 10),
                est_minutes=60,
                status="completed",
                actual_minutes=60,
            )
        )
        # Today's two planned tasks. The studied KP has a LONGER task, so if
        # ordering were by mastery gap alone vs time it still must lose.
        session.add(_planned(TASK_STUDIED, POINT_STUDIED, "重要极限", 30, order=0))
        session.add(_planned(TASK_UNTOUCHED, POINT_UNTOUCHED, "泰勒公式", 30, order=1))
        # A confirmed problem due today -> due_review_count.
        session.add(
            Problem(
                id=uuid4(),
                subject_id=MATH_ID,
                content_md="复习题",
                kind="wrong",
                status="confirmed",
                due_date=TODAY,
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


def test_task_priority_rewards_gap_and_penalises_time() -> None:
    # bigger gap -> higher priority
    assert task_priority(1.0, 20.0, 90.0, 30) > task_priority(1.0, 70.0, 90.0, 30)
    # same gap, shorter task -> higher priority
    assert task_priority(1.0, 20.0, 90.0, 15) > task_priority(1.0, 20.0, 90.0, 60)
    # already at target -> zero
    assert task_priority(1.0, 95.0, 90.0, 30) == 0.0


@pytest.mark.asyncio
async def test_today_ranks_by_priority_and_counts_due_reviews(client: AsyncClient) -> None:
    # The prior completed task would have written back mastery via its signal;
    # recompute here stands in for that so POINT_STUDIED has the smaller gap.
    await client.post("/api/mastery/recompute")

    response = await client.get("/api/today?date=2026-07-20")
    assert response.status_code == 200
    body = response.json()

    assert body["due_review_count"] == 1
    tasks = body["tasks"]
    assert len(tasks) == 2

    # The untouched KP has the larger gap (same 30-min cost) -> ranks first.
    assert tasks[0]["knowledge_point_id"] == str(POINT_UNTOUCHED)
    assert tasks[0]["priority_score"] > tasks[1]["priority_score"]
    assert tasks[1]["knowledge_point_id"] == str(POINT_STUDIED)


@pytest.mark.asyncio
async def test_completed_tasks_sink_below_planned(client: AsyncClient) -> None:
    done = await client.post(
        f"/api/tasks/{TASK_UNTOUCHED}/done", json={"actual_minutes": 25}
    )
    assert done.status_code == 200

    response = await client.get("/api/today?date=2026-07-20")
    tasks = response.json()["tasks"]
    # planned task stays on top, completed one drops to the bottom
    assert tasks[0]["status"] == "planned"
    assert tasks[0]["knowledge_point_id"] == str(POINT_STUDIED)
    assert tasks[-1]["status"] == "completed"
