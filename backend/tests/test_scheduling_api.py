from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from graduate_entrance.db.base import Base
from graduate_entrance.db.session import get_session
from graduate_entrance.main import app
from graduate_entrance.models.planning import (
    AvailabilityPeriod,
    AvailabilityRule,
    PlanPhase,
    PlanPhaseSubjectRatio,
    TaskTemplate,
    TaskTemplatePhase,
)
from graduate_entrance.models.scheduling import ScheduledTask
from graduate_entrance.models.syllabus import (
    Chapter,
    KnowledgeDependency,
    KnowledgePoint,
    Subject,
    SyllabusModule,
    SyllabusVersion,
)

PHASE_ID = uuid4()
SUBJECT_IDS = {"数学一": uuid4(), "408": uuid4()}
POINT_IDS = {
    "数学一": [uuid4(), uuid4(), uuid4()],
    "408": [uuid4(), uuid4(), uuid4()],
}


@dataclass(frozen=True)
class SchedulingContext:
    client: AsyncClient
    session_factory: async_sessionmaker[AsyncSession]


@pytest_asyncio.fixture
async def scheduling_context() -> AsyncIterator[SchedulingContext]:
    engine = create_async_engine("sqlite+aiosqlite://")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    version_id = uuid4()
    subjects = [
        Subject(id=subject_id, code=name, name=name, order=order)
        for order, (name, subject_id) in enumerate(SUBJECT_IDS.items(), start=1)
    ]
    modules = [
        SyllabusModule(
            id=uuid4(),
            subject_id=subject.id,
            name=f"{subject.name}模块",
            slug=f"{subject.code}-module",
            order=1,
        )
        for subject in subjects
    ]
    chapters = [
        Chapter(
            id=uuid4(),
            module_id=module.id,
            name=f"{subject.name}章节",
            slug=f"{subject.code}-chapter",
            order=1,
        )
        for subject, module in zip(subjects, modules, strict=True)
    ]
    points = [
        KnowledgePoint(
            id=point_id,
            chapter_id=chapter.id,
            section_id=None,
            syllabus_version_id=version_id,
            name=f"{subject.name}知识点{order}",
            slug=f"{subject.code}-point-{order}",
            requirement_raw="掌握",
            requirement_level="mastery",
            requirement_actions=["solve"],
            common_exam_style="",
            note="",
            weight=Decimal("1.0"),
            est_minutes=60,
            order=order,
        )
        for subject, chapter in zip(subjects, chapters, strict=True)
        for order, point_id in enumerate(POINT_IDS[subject.name], start=1)
    ]
    phase = PlanPhase(
        id=PHASE_ID,
        name="基础期",
        start_date=datetime(2026, 7, 20, tzinfo=UTC).date(),
        end_date=datetime(2026, 7, 26, tzinfo=UTC).date(),
        description="",
        milestones=[],
        allow_new_tasks=True,
        order=1,
        subject_ratios=[
            PlanPhaseSubjectRatio(
                subject_id=subject.id,
                percentage=50,
            )
            for subject in subjects
        ],
    )
    period = AvailabilityPeriod(
        id=uuid4(),
        name="测试周",
        start_date=phase.start_date,
        end_date=phase.end_date,
        weekly_target_minutes=240,
        order=1,
        rules=[
            AvailabilityRule(weekday=weekday, available_minutes=120)
            for weekday in range(7)
        ],
    )
    templates = [
        TaskTemplate(
            id=uuid4(),
            subject_id=subject.id,
            material_id=None,
            name=f"{subject.name}学习",
            task_type="reading",
            default_est_minutes=60,
            description="",
            active=True,
            order=1,
            phase_links=[TaskTemplatePhase(phase_id=PHASE_ID)],
        )
        for subject in subjects
    ]
    async with session_factory() as session:
        session.add(
            SyllabusVersion(
                id=version_id,
                source_name="test.csv",
                source_checksum="0" * 64,
                row_count=len(points),
                imported_at=datetime.now(UTC),
            )
        )
        session.add_all([*subjects, *modules, *chapters, *points, phase, period, *templates])
        session.add(
            KnowledgeDependency(
                predecessor_kp_id=POINT_IDS["数学一"][0],
                successor_kp_id=POINT_IDS["数学一"][1],
                dependency_type="prerequisite",
                strength=Decimal("1.0"),
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
    ) as client:
        yield SchedulingContext(client=client, session_factory=session_factory)
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_task_pool_generation_is_idempotent(
    scheduling_context: SchedulingContext,
) -> None:
    first = await scheduling_context.client.post("/api/planning/task-pool/generate")
    second = await scheduling_context.client.post("/api/planning/task-pool/generate")
    page = await scheduling_context.client.get(
        "/api/planning/task-pool",
        params={"limit": 3},
    )

    assert first.status_code == 200
    assert first.json() == {"created": 6, "updated": 0, "deleted": 0, "total": 6}
    assert second.status_code == 200
    assert second.json() == {"created": 0, "updated": 0, "deleted": 0, "total": 6}
    assert page.status_code == 200
    assert page.json()["total"] == 6
    assert len(page.json()["items"]) == 3

    async with scheduling_context.session_factory() as session:
        template = await session.scalar(
            select(TaskTemplate).order_by(TaskTemplate.subject_id)
        )
        assert template is not None
        template.active = False
        await session.commit()

    synchronized = await scheduling_context.client.post(
        "/api/planning/task-pool/generate"
    )
    synchronized_page = await scheduling_context.client.get("/api/planning/task-pool")
    assert synchronized.json() == {
        "created": 0,
        "updated": 0,
        "deleted": 3,
        "total": 3,
    }
    assert synchronized_page.json()["total"] == 3


@pytest.mark.asyncio
async def test_deterministic_plan_honors_capacity_ratios_and_dependencies(
    scheduling_context: SchedulingContext,
) -> None:
    await scheduling_context.client.post("/api/planning/task-pool/generate")
    request = {"start_date": "2026-07-20", "end_date": "2026-07-26"}

    first = await scheduling_context.client.post("/api/plan/preview", json=request)
    second = await scheduling_context.client.post("/api/plan/preview", json=request)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    payload = first.json()
    assert len(payload["tasks"]) == 4
    assert sum(day["planned_minutes"] for day in payload["days"]) == 240
    assert all(
        day["planned_minutes"] <= day["available_minutes"] for day in payload["days"]
    )
    assert {subject["planned_minutes"] for subject in payload["subjects"]} == {120}
    assert payload["warnings"] == ["2 task-pool items did not fit the requested range"]

    task_order = {
        UUID(task["knowledge_point_id"]): (task["planned_date"], task["order"])
        for task in payload["tasks"]
    }
    assert task_order[POINT_IDS["数学一"][0]] < task_order[POINT_IDS["数学一"][1]]


@pytest.mark.asyncio
async def test_persisted_plan_calendar_and_replan_preserve_completed_tasks(
    scheduling_context: SchedulingContext,
) -> None:
    await scheduling_context.client.post("/api/planning/task-pool/generate")
    request = {"start_date": "2026-07-20", "end_date": "2026-07-26"}
    generated = await scheduling_context.client.post("/api/plan/generate", json=request)
    assert generated.status_code == 200
    assert generated.json()["persisted"] is True

    calendar = await scheduling_context.client.get(
        "/api/calendar",
        params={"month": "2026-07"},
    )
    assert calendar.status_code == 200
    assert sum(week["planned_minutes"] for week in calendar.json()["weeks"]) == 240

    async with scheduling_context.session_factory() as session:
        completed = await session.scalar(
            select(ScheduledTask).order_by(
                ScheduledTask.planned_date,
                ScheduledTask.order,
            )
        )
        assert completed is not None
        completed.status = "completed"
        completed.actual_minutes = 55
        completed.done_at = datetime.now(UTC)
        completed_id = completed.id
        completed_date = completed.planned_date
        await session.commit()

    exception = await scheduling_context.client.post(
        "/api/planning/availability-exceptions",
        json={
            "date": completed_date.isoformat(),
            "available_minutes": 0,
            "reason": "已完成任务所在日随后请假",
        },
    )
    assert exception.status_code == 201
    replanned = await scheduling_context.client.post("/api/plan/generate", json=request)
    assert replanned.status_code == 200

    async with scheduling_context.session_factory() as session:
        preserved = await session.get(ScheduledTask, completed_id)
        assert preserved is not None
        assert preserved.status == "completed"
        assert preserved.planned_date == completed_date
        assert preserved.actual_minutes == 55

    refreshed_calendar = await scheduling_context.client.get(
        "/api/calendar",
        params={"month": "2026-07"},
    )
    completed_tasks = [
        task
        for day in refreshed_calendar.json()["days"]
        for task in day["tasks"]
        if task["id"] == str(completed_id)
    ]
    assert len(completed_tasks) == 1
    assert completed_tasks[0]["status"] == "completed"
    assert completed_tasks[0]["actual_minutes"] == 55
