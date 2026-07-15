from collections.abc import AsyncIterator
from uuid import UUID, uuid4

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
from graduate_entrance.models.syllabus import Subject

SUBJECT_IDS = {
    "数学一": uuid4(),
    "408": uuid4(),
    "英语一": uuid4(),
    "政治": uuid4(),
}


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    engine = create_async_engine("sqlite+aiosqlite://")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        session.add_all(
            [
                Subject(id=subject_id, code=name, name=name, order=order)
                for order, (name, subject_id) in enumerate(SUBJECT_IDS.items(), start=1)
            ]
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


def phase_payload(name: str = "基础期") -> dict[str, object]:
    return {
        "name": name,
        "start_date": "2026-07-15",
        "end_date": "2026-08-31",
        "description": "完成数学与 408 一轮",
        "milestones": ["王道数据结构完成"],
        "allow_new_tasks": True,
        "order": 1,
        "subject_ratios": [
            {"subject_id": str(SUBJECT_IDS["数学一"]), "percentage": 40},
            {"subject_id": str(SUBJECT_IDS["408"]), "percentage": 35},
            {"subject_id": str(SUBJECT_IDS["英语一"]), "percentage": 15},
            {"subject_id": str(SUBJECT_IDS["政治"]), "percentage": 10},
        ],
    }


@pytest.mark.asyncio
async def test_planning_configuration_crud(client: AsyncClient) -> None:
    initial = await client.get("/api/planning/config")
    assert initial.status_code == 200
    assert len(initial.json()["subjects"]) == 4

    phase_response = await client.post("/api/planning/phases", json=phase_payload())
    assert phase_response.status_code == 201
    phase_id = UUID(phase_response.json()["id"])

    overlap_response = await client.post(
        "/api/planning/phases",
        json=phase_payload("重叠阶段"),
    )
    assert overlap_response.status_code == 409

    rules = [
        {"weekday": weekday, "available_minutes": 600 if weekday < 5 else 660}
        for weekday in range(7)
    ]
    period_response = await client.post(
        "/api/planning/availability-periods",
        json={
            "name": "暑假",
            "start_date": "2026-07-15",
            "end_date": "2026-08-31",
            "weekly_target_minutes": 3300,
            "order": 1,
            "rules": rules,
        },
    )
    assert period_response.status_code == 201
    period_id = UUID(period_response.json()["id"])

    exception_response = await client.post(
        "/api/planning/availability-exceptions",
        json={
            "date": "2026-07-20",
            "available_minutes": 0,
            "reason": "请假",
        },
    )
    assert exception_response.status_code == 201
    exception_id = UUID(exception_response.json()["id"])

    material_response = await client.post(
        "/api/planning/materials",
        json={
            "subject_id": str(SUBJECT_IDS["408"]),
            "name": "王道数据结构",
            "material_type": "textbook",
            "source": "王道",
            "description": "数据结构一轮资料",
            "active": True,
            "order": 1,
        },
    )
    assert material_response.status_code == 201
    material_id = UUID(material_response.json()["id"])

    updated_material_response = await client.put(
        f"/api/planning/materials/{material_id}",
        json={
            "subject_id": str(SUBJECT_IDS["408"]),
            "name": "王道数据结构复习指导",
            "material_type": "textbook",
            "source": "王道",
            "description": "数据结构一轮资料",
            "active": True,
            "order": 1,
        },
    )
    assert updated_material_response.status_code == 200
    assert updated_material_response.json()["name"] == "王道数据结构复习指导"

    template_response = await client.post(
        "/api/planning/task-templates",
        json={
            "subject_id": str(SUBJECT_IDS["408"]),
            "material_id": str(material_id),
            "name": "王道章节学习",
            "task_type": "reading",
            "default_est_minutes": 90,
            "description": "阅读并完成章节例题",
            "active": True,
            "order": 1,
            "phase_ids": [str(phase_id)],
        },
    )
    assert template_response.status_code == 201
    template_id = UUID(template_response.json()["id"])

    config = await client.get("/api/planning/config")
    assert config.status_code == 200
    payload = config.json()
    assert payload["phases"][0]["subject_ratios"][0]["percentage"] in {10, 15, 35, 40}
    assert len(payload["availability_periods"][0]["rules"]) == 7
    assert payload["availability_exceptions"][0]["available_minutes"] == 0
    assert payload["materials"][0]["name"] == "王道数据结构复习指导"
    assert payload["task_templates"][0]["phase_ids"] == [str(phase_id)]

    assert (await client.delete(f"/api/planning/phases/{phase_id}")).status_code == 409
    assert (await client.delete(f"/api/planning/task-templates/{template_id}")).status_code == 204
    assert (await client.delete(f"/api/planning/materials/{material_id}")).status_code == 204
    assert (
        await client.delete(f"/api/planning/availability-exceptions/{exception_id}")
    ).status_code == 204
    assert (
        await client.delete(f"/api/planning/availability-periods/{period_id}")
    ).status_code == 204
    assert (await client.delete(f"/api/planning/phases/{phase_id}")).status_code == 204


@pytest.mark.asyncio
async def test_phase_ratios_must_total_one_hundred(client: AsyncClient) -> None:
    payload = phase_payload()
    ratios = payload["subject_ratios"]
    assert isinstance(ratios, list)
    ratios[0]["percentage"] = 30

    response = await client.post("/api/planning/phases", json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"][0]["location"] == "body"
