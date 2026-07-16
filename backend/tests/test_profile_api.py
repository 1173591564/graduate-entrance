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
from graduate_entrance.models.problems import Problem, ProblemKnowledgePoint, ReviewLog
from graduate_entrance.models.scheduling import ScheduledTask
from graduate_entrance.models.syllabus import (
    Chapter,
    KnowledgePoint,
    Subject,
    SyllabusModule,
    SyllabusVersion,
)

MATH_ID = uuid4()
ENGLISH_ID = uuid4()
VERSION_ID = uuid4()
POINT_STUDIED = uuid4()
POINT_WEAK = uuid4()
POINT_UNTOUCHED = uuid4()


def _knowledge_point(kp_id: Any, chapter_id: Any, name: str, order: int) -> KnowledgePoint:
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
                row_count=3,
                imported_at=date(2026, 1, 1),
            )
        )
        session.add(Subject(id=MATH_ID, code="math1", name="数学一", order=1))
        session.add(Subject(id=ENGLISH_ID, code="english1", name="英语一", order=3))
        module_id = uuid4()
        chapter_id = uuid4()
        session.add(
            SyllabusModule(id=module_id, subject_id=MATH_ID, name="高数", slug="gs", order=1)
        )
        session.add(
            Chapter(id=chapter_id, module_id=module_id, name="极限", slug="jx", order=1)
        )
        session.add(_knowledge_point(POINT_STUDIED, chapter_id, "重要极限", 1))
        session.add(_knowledge_point(POINT_WEAK, chapter_id, "等价无穷小", 2))
        session.add(_knowledge_point(POINT_UNTOUCHED, chapter_id, "泰勒公式", 3))
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
        session.add(
            ScheduledTask(
                id=uuid4(),
                subject_id=MATH_ID,
                knowledge_point_id=POINT_WEAK,
                phase_name="基础",
                subject_name="数学一",
                knowledge_point_name="等价无穷小",
                title="学习等价无穷小",
                task_type="reading",
                planned_date=date(2026, 7, 11),
                est_minutes=60,
                status="completed",
                actual_minutes=65,
            )
        )
        problem_id = uuid4()
        session.add(
            Problem(
                id=problem_id,
                subject_id=MATH_ID,
                content_md="求极限",
                kind="wrong",
                status="confirmed",
                cause="concept",
            )
        )
        await session.commit()
        session.add(
            ProblemKnowledgePoint(
                problem_id=problem_id,
                knowledge_point_id=POINT_WEAK,
                role="primary",
                weight=1.0,
            )
        )
        session.add(
            ReviewLog(
                id=uuid4(),
                problem_id=problem_id,
                grade="forgot",
                reviewed_on=date(2026, 7, 12),
            )
        )
        session.add(
            ReviewLog(
                id=uuid4(),
                problem_id=problem_id,
                grade="vague",
                reviewed_on=date(2026, 7, 14),
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
async def test_goals_upsert_and_list(client: AsyncClient) -> None:
    empty = await client.get("/api/profile/goals")
    assert empty.status_code == 200
    assert empty.json()["goals"] == []

    response = await client.put(
        "/api/profile/goals",
        json={
            "goals": [
                {"subject_id": str(MATH_ID), "target_score": 120, "full_score": 150},
                {
                    "subject_id": str(ENGLISH_ID),
                    "target_score": 70,
                    "full_score": 100,
                    "note": "作文重点",
                },
            ]
        },
    )
    assert response.status_code == 200
    goals = response.json()["goals"]
    assert [entry["subject_name"] for entry in goals] == ["数学一", "英语一"]
    assert goals[0]["target_score"] == 120

    updated = await client.put(
        "/api/profile/goals",
        json={"goals": [{"subject_id": str(MATH_ID), "target_score": 130, "full_score": 150}]},
    )
    math_goal = next(
        entry for entry in updated.json()["goals"] if entry["subject_id"] == str(MATH_ID)
    )
    assert math_goal["target_score"] == 130


@pytest.mark.asyncio
async def test_goals_reject_unknown_subject(client: AsyncClient) -> None:
    response = await client.put(
        "/api/profile/goals",
        json={"goals": [{"subject_id": str(uuid4()), "target_score": 100, "full_score": 150}]},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_goals_reject_target_above_full(client: AsyncClient) -> None:
    response = await client.put(
        "/api/profile/goals",
        json={"goals": [{"subject_id": str(MATH_ID), "target_score": 160, "full_score": 150}]},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_profile_reports_mastery_and_weak_points(client: AsyncClient) -> None:
    await client.put(
        "/api/profile/goals",
        json={"goals": [{"subject_id": str(MATH_ID), "target_score": 120, "full_score": 150}]},
    )

    response = await client.get("/api/profile?as_of=2026-07-16")
    assert response.status_code == 200
    body = response.json()
    assert body["exam_date"] == "2026-12-26"
    assert body["days_to_exam"] == 163

    math = next(entry for entry in body["subjects"] if entry["subject_id"] == str(MATH_ID))
    assert math["knowledge_point_total"] == 3
    assert math["studied_points"] == 2
    assert math["coverage"] == pytest.approx(0.667, abs=0.001)
    assert math["studied_minutes"] == 120
    assert math["problem_count"] == 1
    assert math["wrong_count"] == 1
    assert math["target_score"] == 120
    assert math["estimated_score"] is not None

    weak_ids = [entry["knowledge_point_id"] for entry in math["weak_points"]]
    assert str(POINT_UNTOUCHED) in weak_ids
    assert str(POINT_STUDIED) not in weak_ids
    weak = next(
        entry for entry in math["weak_points"] if entry["knowledge_point_id"] == str(POINT_WEAK)
    )
    assert weak["forgot_reviews"] == 1
    assert weak["problem_count"] == 1

    english = next(
        entry for entry in body["subjects"] if entry["subject_id"] == str(ENGLISH_ID)
    )
    assert english["knowledge_point_total"] == 0
    assert english["mastery"] == 0.0
