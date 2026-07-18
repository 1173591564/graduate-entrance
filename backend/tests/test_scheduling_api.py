from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
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


@pytest.mark.asyncio
async def test_reschedule_carries_overdue_tasks_forward(
    scheduling_context: SchedulingContext,
) -> None:
    await scheduling_context.client.post("/api/planning/task-pool/generate")
    request = {"start_date": "2026-07-20", "end_date": "2026-07-26"}
    generated = await scheduling_context.client.post("/api/plan/generate", json=request)
    assert generated.status_code == 200
    original_tasks = generated.json()["tasks"]
    assert len(original_tasks) == 4
    original_pool_ids = {task["pool_item_id"] for task in original_tasks}
    overdue_count = sum(
        1 for task in original_tasks if task["planned_date"] < "2026-07-22"
    )
    assert overdue_count > 0

    rescheduled = await scheduling_context.client.post(
        "/api/plan/reschedule",
        json={"start_date": "2026-07-22", "end_date": "2026-07-26"},
    )
    assert rescheduled.status_code == 200
    payload = rescheduled.json()
    assert payload["persisted"] is True
    assert payload["carried_over"] == overdue_count

    async with scheduling_context.session_factory() as session:
        tasks = (await session.scalars(select(ScheduledTask))).all()
    assert {str(task.pool_item_id) for task in tasks} == original_pool_ids
    assert all(task.planned_date.isoformat() >= "2026-07-22" for task in tasks)
    assert sum(1 for task in tasks if task.carry_count == 1) == overdue_count

    second = await scheduling_context.client.post(
        "/api/plan/reschedule",
        json={"start_date": "2026-07-22", "end_date": "2026-07-26"},
    )
    assert second.status_code == 200
    assert second.json()["carried_over"] == 0
    async with scheduling_context.session_factory() as session:
        retained = (await session.scalars(select(ScheduledTask))).all()
    assert sum(1 for task in retained if task.carry_count == 1) == overdue_count


@pytest.mark.asyncio
async def test_reschedule_preserves_completed_and_unfitted_overdue_tasks(
    scheduling_context: SchedulingContext,
) -> None:
    await scheduling_context.client.post("/api/planning/task-pool/generate")
    request = {"start_date": "2026-07-20", "end_date": "2026-07-26"}
    await scheduling_context.client.post("/api/plan/generate", json=request)

    async with scheduling_context.session_factory() as session:
        ordered = (
            await session.scalars(
                select(ScheduledTask).order_by(
                    ScheduledTask.planned_date,
                    ScheduledTask.order,
                )
            )
        ).all()
        completed = ordered[0]
        completed.status = "completed"
        completed.actual_minutes = 45
        completed.done_at = datetime.now(UTC)
        completed_id = completed.id
        completed_date = completed.planned_date
        overdue_ids = [task.id for task in ordered[1:] if task.status == "planned"]
        await session.commit()

    rescheduled = await scheduling_context.client.post(
        "/api/plan/reschedule",
        json={"start_date": "2026-07-26", "end_date": "2026-07-26"},
    )
    assert rescheduled.status_code == 200

    async with scheduling_context.session_factory() as session:
        preserved = await session.get(ScheduledTask, completed_id)
        assert preserved is not None
        assert preserved.status == "completed"
        assert preserved.planned_date == completed_date
        assert preserved.actual_minutes == 45
        remaining = (
            await session.scalars(
                select(ScheduledTask).where(ScheduledTask.id.in_(overdue_ids))
            )
        ).all()
    assert len(remaining) == len(overdue_ids)
    fitted = [task for task in remaining if task.planned_date.isoformat() == "2026-07-26"]
    unfitted = [task for task in remaining if task.planned_date.isoformat() < "2026-07-26"]
    assert all(task.carry_count == 1 for task in fitted)
    assert all(task.carry_count == 0 for task in unfitted)
    assert len(fitted) + len(unfitted) == len(overdue_ids)


@pytest.mark.asyncio
async def test_reschedule_marks_leave_dates_and_moves_tasks_off_them(
    scheduling_context: SchedulingContext,
) -> None:
    await scheduling_context.client.post("/api/planning/task-pool/generate")
    request = {"start_date": "2026-07-20", "end_date": "2026-07-26"}
    await scheduling_context.client.post("/api/plan/generate", json=request)

    rescheduled = await scheduling_context.client.post(
        "/api/plan/reschedule",
        json={
            "start_date": "2026-07-20",
            "end_date": "2026-07-26",
            "leave_dates": ["2026-07-20"],
        },
    )
    assert rescheduled.status_code == 200
    payload = rescheduled.json()
    leave_day = next(day for day in payload["days"] if day["date"] == "2026-07-20")
    assert leave_day["available_minutes"] == 0
    assert leave_day["planned_minutes"] == 0
    assert all(task["planned_date"] != "2026-07-20" for task in payload["tasks"])

    config = await scheduling_context.client.get("/api/planning/config")
    exceptions = config.json()["availability_exceptions"]
    assert any(
        exception["date"] == "2026-07-20" and exception["available_minutes"] == 0
        for exception in exceptions
    )

    repeated = await scheduling_context.client.post(
        "/api/plan/reschedule",
        json={
            "start_date": "2026-07-20",
            "end_date": "2026-07-26",
            "leave_dates": ["2026-07-20"],
        },
    )
    assert repeated.status_code == 200
    refreshed = await scheduling_context.client.get("/api/planning/config")
    assert (
        len(
            [
                exception
                for exception in refreshed.json()["availability_exceptions"]
                if exception["date"] == "2026-07-20"
            ]
        )
        == 1
    )


@pytest.mark.asyncio
async def test_reschedule_defaults_end_date_to_last_phase(
    scheduling_context: SchedulingContext,
) -> None:
    await scheduling_context.client.post("/api/planning/task-pool/generate")
    request = {"start_date": "2026-07-20", "end_date": "2026-07-26"}
    await scheduling_context.client.post("/api/plan/generate", json=request)

    rescheduled = await scheduling_context.client.post(
        "/api/plan/reschedule",
        json={"start_date": "2026-07-21"},
    )
    assert rescheduled.status_code == 200
    assert rescheduled.json()["end_date"] == "2026-07-26"

    empty_range = await scheduling_context.client.post(
        "/api/plan/reschedule",
        json={"start_date": "2026-08-01"},
    )
    assert empty_range.status_code == 400


@pytest.mark.asyncio
async def test_today_and_check_in_are_idempotent(
    scheduling_context: SchedulingContext,
) -> None:
    await scheduling_context.client.post("/api/planning/task-pool/generate")
    request = {"start_date": "2026-07-20", "end_date": "2026-07-26"}
    await scheduling_context.client.post("/api/plan/generate", json=request)

    today = await scheduling_context.client.get(
        "/api/today",
        params={"date": "2026-07-20"},
    )
    assert today.status_code == 200
    before = today.json()
    assert before["date"] == "2026-07-20"
    assert before["planned_minutes"] == 120
    assert before["completed_minutes"] == 0
    assert before["remaining_minutes"] == 120
    assert len(before["tasks"]) == 2

    task_id = before["tasks"][0]["id"]
    first = await scheduling_context.client.post(
        f"/api/tasks/{task_id}/done",
        json={"actual_minutes": 55},
    )
    second = await scheduling_context.client.post(
        f"/api/tasks/{task_id}/done",
        json={"actual_minutes": 55},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["status"] == "completed"
    assert first.json()["actual_minutes"] == 55
    assert first.json()["done_at"] is not None

    updated = await scheduling_context.client.get(
        "/api/today",
        params={"date": "2026-07-20"},
    )
    assert updated.status_code == 200
    after = updated.json()
    assert after["planned_minutes"] == 120
    assert after["completed_minutes"] == 55
    assert after["remaining_minutes"] == 60


@pytest.mark.asyncio
async def test_weekly_stats_aggregate_minutes_and_execution_rate(
    scheduling_context: SchedulingContext,
) -> None:
    await scheduling_context.client.post("/api/planning/task-pool/generate")
    request = {"start_date": "2026-07-20", "end_date": "2026-07-26"}
    await scheduling_context.client.post("/api/plan/generate", json=request)
    today = await scheduling_context.client.get(
        "/api/today",
        params={"date": "2026-07-20"},
    )
    task_id = today.json()["tasks"][0]["id"]
    await scheduling_context.client.post(
        f"/api/tasks/{task_id}/done",
        json={"actual_minutes": 45},
    )

    stats = await scheduling_context.client.get(
        "/api/stats/weekly",
        params={"start": "2026-07-20", "end": "2026-07-26"},
    )

    assert stats.status_code == 200
    body = stats.json()
    assert body["start_date"] == "2026-07-20"
    assert body["end_date"] == "2026-07-26"
    assert len(body["weeks"]) == 1
    week = body["weeks"][0]
    assert week["week_start"] == "2026-07-20"
    assert week["week_end"] == "2026-07-26"
    assert week["planned_minutes"] == 240
    assert week["completed_minutes"] == 45
    assert week["target_minutes"] == 240
    assert week["total_tasks"] == 4
    assert week["completed_tasks"] == 1
    assert week["execution_rate"] == 0.1875
    assert body["total_planned_minutes"] == 240
    assert body["total_completed_minutes"] == 45
    assert body["overall_execution_rate"] == 0.1875


@pytest.mark.asyncio
async def test_weekly_stats_include_empty_weeks_in_explicit_range(
    scheduling_context: SchedulingContext,
) -> None:
    await scheduling_context.client.post("/api/planning/task-pool/generate")
    request = {"start_date": "2026-07-20", "end_date": "2026-07-26"}
    await scheduling_context.client.post("/api/plan/generate", json=request)

    stats = await scheduling_context.client.get(
        "/api/stats/weekly",
        params={"start": "2026-07-20", "end": "2026-08-02"},
    )

    assert stats.status_code == 200
    body = stats.json()
    assert [week["week_start"] for week in body["weeks"]] == [
        "2026-07-20",
        "2026-07-27",
    ]
    empty_week = body["weeks"][1]
    assert empty_week["planned_minutes"] == 0
    assert empty_week["total_tasks"] == 0
    assert empty_week["execution_rate"] == 0.0
    assert empty_week["target_minutes"] is None


@pytest.mark.asyncio
async def test_weekly_stats_handle_empty_database_and_bad_range(
    scheduling_context: SchedulingContext,
) -> None:
    empty = await scheduling_context.client.get("/api/stats/weekly")
    assert empty.status_code == 200
    assert empty.json()["weeks"] == []
    assert empty.json()["overall_execution_rate"] == 0.0

    inverted = await scheduling_context.client.get(
        "/api/stats/weekly",
        params={"start": "2026-08-02", "end": "2026-07-20"},
    )
    assert inverted.status_code == 400


@pytest.mark.asyncio
async def test_update_task_estimate(
    scheduling_context: SchedulingContext,
) -> None:
    await scheduling_context.client.post("/api/planning/task-pool/generate")
    request = {"start_date": "2026-07-20", "end_date": "2026-07-26"}
    await scheduling_context.client.post("/api/plan/generate", json=request)
    today = await scheduling_context.client.get(
        "/api/today",
        params={"date": "2026-07-20"},
    )
    task = today.json()["tasks"][0]
    assert task["status"] == "planned"

    updated = await scheduling_context.client.patch(
        f"/api/tasks/{task['id']}",
        json={"est_minutes": 90},
    )
    assert updated.status_code == 200
    assert updated.json()["est_minutes"] == 90
    assert updated.json()["status"] == "planned"
    assert updated.json()["actual_minutes"] is None

    invalid = await scheduling_context.client.patch(
        f"/api/tasks/{task['id']}",
        json={"est_minutes": 0},
    )
    assert invalid.status_code == 422

    missing = await scheduling_context.client.patch(
        f"/api/tasks/{uuid4()}",
        json={"est_minutes": 60},
    )
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_check_in_rejects_unknown_task(
    scheduling_context: SchedulingContext,
) -> None:
    response = await scheduling_context.client.post(
        f"/api/tasks/{uuid4()}/done",
        json={"actual_minutes": 30},
    )

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Scheduled task not found"


@pytest.mark.asyncio
async def test_ai_week_plan_persists_plan_and_advice(
    scheduling_context: SchedulingContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await scheduling_context.client.post("/api/planning/task-pool/generate")
    captured: dict[str, object] = {}

    async def fake_complete_chat(
        messages: list[dict[str, object]],
        settings: object,
        reasoning_effort: str | None = None,
    ) -> str:
        captured["messages"] = messages
        return (
            '{"summary": "先补数学薄弱点，再推进 408。",'
            ' "daily_focus": [{"date": "2026-07-20", "focus": "上午攻克重要极限"},'
            ' {"date": "2026-07-21", "focus": "408 数据结构复习"},'
            ' {"date": "bad-date", "focus": "忽略"}],'
            ' "review_suggestions": ["每天 20 分钟复盘错题", "周末重做遗忘题"]}'
        )

    monkeypatch.setattr("graduate_entrance.ai.client.complete_chat", fake_complete_chat)

    response = await scheduling_context.client.post(
        "/api/plan/ai-week", json={"start_date": "2026-07-20"}
    )
    assert response.status_code == 200
    payload = response.json()

    plan = payload["plan"]
    assert plan["persisted"] is True
    assert plan["start_date"] == "2026-07-20"
    assert plan["end_date"] == "2026-07-26"
    assert len(plan["tasks"]) == 4

    advice = payload["advice"]
    assert advice["week_start"] == "2026-07-20"
    assert advice["summary"] == "先补数学薄弱点，再推进 408。"
    assert len(advice["daily_focus"]) == 7
    assert advice["daily_focus"][0] == {"date": "2026-07-20", "focus": "上午攻克重要极限"}
    assert advice["daily_focus"][2]["focus"] == "按计划推进当日任务"
    assert advice["review_suggestions"] == ["每天 20 分钟复盘错题", "周末重做遗忘题"]

    messages = captured["messages"]
    assert isinstance(messages, list)
    user_text = messages[1]["content"]
    assert isinstance(user_text, str)
    assert "2026-07-20" in user_text

    stored = await scheduling_context.client.get(
        "/api/plan/ai-week", params={"week_start": "2026-07-22"}
    )
    assert stored.status_code == 200
    assert stored.json()["summary"] == "先补数学薄弱点，再推进 408。"

    tasks = await scheduling_context.client.get(
        "/api/today", params={"date": "2026-07-20"}
    )
    assert tasks.status_code == 200
    assert tasks.json()["tasks"]


@pytest.mark.asyncio
async def test_ai_week_plan_missing_advice_returns_404(
    scheduling_context: SchedulingContext,
) -> None:
    response = await scheduling_context.client.get(
        "/api/plan/ai-week", params={"week_start": "2030-01-07"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_ai_week_plan_unconfigured_returns_503(
    scheduling_context: SchedulingContext,
) -> None:
    response = await scheduling_context.client.post(
        "/api/plan/ai-week", json={"start_date": "2026-07-20"}
    )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_ai_week_plan_without_available_time_returns_409(
    scheduling_context: SchedulingContext,
) -> None:
    response = await scheduling_context.client.post(
        "/api/plan/ai-week", json={"start_date": "2030-01-07"}
    )
    assert response.status_code == 409
    assert "可用学习时间" in response.json()["error"]["message"]


async def _seed_completed_history(
    scheduling_context: SchedulingContext,
    count: int,
    actual_minutes: int,
) -> None:
    subject_id = SUBJECT_IDS["数学一"]
    async with scheduling_context.session_factory() as session:
        for index in range(count):
            session.add(
                ScheduledTask(
                    id=uuid4(),
                    phase_id=PHASE_ID,
                    subject_id=subject_id,
                    phase_name="基础阶段",
                    subject_name="数学一",
                    knowledge_point_name="历史知识点",
                    material_name=None,
                    title=f"历史任务{index}",
                    task_type="reading",
                    planned_date=date(2026, 7, 13),
                    est_minutes=60,
                    status="completed",
                    actual_minutes=actual_minutes,
                    done_at=datetime.now(UTC),
                    order=index,
                )
            )
        await session.commit()


@pytest.mark.asyncio
async def test_plan_estimates_corrected_by_completion_history(
    scheduling_context: SchedulingContext,
) -> None:
    await _seed_completed_history(scheduling_context, count=5, actual_minutes=90)
    await scheduling_context.client.post("/api/planning/task-pool/generate")
    preview = await scheduling_context.client.post(
        "/api/plan/preview",
        json={"start_date": "2026-07-20", "end_date": "2026-07-26"},
    )
    assert preview.status_code == 200
    est_by_subject = {
        task["subject_name"]: task["est_minutes"] for task in preview.json()["tasks"]
    }
    assert est_by_subject["数学一"] == 90
    assert est_by_subject["408"] == 60


@pytest.mark.asyncio
async def test_plan_estimates_unchanged_with_insufficient_samples(
    scheduling_context: SchedulingContext,
) -> None:
    await _seed_completed_history(scheduling_context, count=4, actual_minutes=90)
    await scheduling_context.client.post("/api/planning/task-pool/generate")
    preview = await scheduling_context.client.post(
        "/api/plan/preview",
        json={"start_date": "2026-07-20", "end_date": "2026-07-26"},
    )
    assert preview.status_code == 200
    assert all(task["est_minutes"] == 60 for task in preview.json()["tasks"])


@pytest.mark.asyncio
async def test_plan_estimate_ratio_is_clamped(
    scheduling_context: SchedulingContext,
) -> None:
    await _seed_completed_history(scheduling_context, count=5, actual_minutes=300)
    await scheduling_context.client.post("/api/planning/task-pool/generate")
    preview = await scheduling_context.client.post(
        "/api/plan/preview",
        json={"start_date": "2026-07-20", "end_date": "2026-07-26"},
    )
    assert preview.status_code == 200
    est_values = {
        task["est_minutes"]
        for task in preview.json()["tasks"]
        if task["subject_name"] == "数学一"
    }
    assert est_values == {120}
