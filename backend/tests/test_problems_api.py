from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

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
from graduate_entrance.models.syllabus import (
    Chapter,
    KnowledgePoint,
    Subject,
    SyllabusModule,
    SyllabusVersion,
)

SUBJECT_ID = uuid4()
POINT_IDS = [uuid4(), uuid4()]

PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d4944415478da63f8ffff3f0300050001ff8f7ad10000000049454e"
    "44ae426082"
)


@pytest_asyncio.fixture
async def client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    get_settings().problem_images_dir = tmp_path / "problem-images"
    engine = create_async_engine("sqlite+aiosqlite://")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    version_id = uuid4()
    module_id = uuid4()
    chapter_id = uuid4()
    async with session_factory() as session:
        session.add(Subject(id=SUBJECT_ID, code="math1", name="数学一", order=1))
        session.add(
            SyllabusVersion(
                id=version_id,
                source_name="test.csv",
                source_checksum="0" * 64,
                row_count=2,
                imported_at=datetime.now(UTC),
            )
        )
        await session.flush()
        session.add(
            SyllabusModule(
                id=module_id, subject_id=SUBJECT_ID, name="高数", slug="module", order=1
            )
        )
        await session.flush()
        session.add(Chapter(id=chapter_id, module_id=module_id, name="极限", slug="ch", order=1))
        await session.flush()
        session.add_all(
            [
                KnowledgePoint(
                    id=point_id,
                    chapter_id=chapter_id,
                    section_id=None,
                    syllabus_version_id=version_id,
                    name=f"知识点{order}",
                    slug=f"point-{order}",
                    requirement_raw="掌握",
                    requirement_level="mastery",
                    requirement_actions=["solve"],
                    common_exam_style="",
                    note="",
                    weight=Decimal("1.0"),
                    est_minutes=60,
                    order=order,
                )
                for order, point_id in enumerate(POINT_IDS, start=1)
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


async def submit_draft(client: AsyncClient) -> dict[str, object]:
    response = await client.post(
        "/api/problems",
        data={
            "subject_id": str(SUBJECT_ID),
            "kind": "wrong",
            "content_md": "求 $\\lim_{x\\to 0} \\frac{\\sin x}{x}$",
            "source_ref": "真题 2020-3",
        },
        files=[("images", ("photo.png", PNG_BYTES, "image/png"))],
    )
    assert response.status_code == 201
    body: dict[str, object] = response.json()
    return body


@pytest.mark.asyncio
async def test_submit_problem_creates_draft_and_stores_image(client: AsyncClient) -> None:
    body = await submit_draft(client)
    assert body["status"] == "draft"
    assert body["subject_name"] == "数学一"
    assert body["due_date"] is not None
    images = body["images"]
    assert isinstance(images, list) and len(images) == 1

    image_response = await client.get(f"/api/problems/images/{images[0]}")
    assert image_response.status_code == 200
    assert image_response.content == PNG_BYTES

    pending = await client.get("/api/problems/pending")
    assert pending.status_code == 200
    assert pending.json()["total"] == 1

    missing = await client.get("/api/problems/images/deadbeef.png")
    assert missing.status_code == 404

    traversal = await client.get("/api/problems/images/..%2fsecret.png")
    assert traversal.status_code == 404


@pytest.mark.asyncio
async def test_submit_problem_requires_content_or_image(client: AsyncClient) -> None:
    response = await client.post("/api/problems", data={"kind": "wrong"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_confirm_problem_validates_mappings_and_finalizes(client: AsyncClient) -> None:
    body = await submit_draft(client)
    problem_id = body["id"]

    no_primary = await client.post(
        f"/api/problems/{problem_id}/confirm",
        json={
            "content_md": "题面",
            "kind": "wrong",
            "knowledge_points": [
                {
                    "knowledge_point_id": str(POINT_IDS[0]),
                    "role": "secondary",
                    "weight": 1.0,
                }
            ],
        },
    )
    assert no_primary.status_code == 400

    bad_weights = await client.post(
        f"/api/problems/{problem_id}/confirm",
        json={
            "content_md": "题面",
            "kind": "wrong",
            "knowledge_points": [
                {
                    "knowledge_point_id": str(POINT_IDS[0]),
                    "role": "primary",
                    "weight": 0.5,
                },
                {
                    "knowledge_point_id": str(POINT_IDS[1]),
                    "role": "secondary",
                    "weight": 0.2,
                },
            ],
        },
    )
    assert bad_weights.status_code == 400

    confirmed = await client.post(
        f"/api/problems/{problem_id}/confirm",
        json={
            "content_md": "定稿题面",
            "kind": "wrong",
            "cause": "concept",
            "my_answer_md": "错解",
            "note": "注意等价无穷小",
            "knowledge_points": [
                {
                    "knowledge_point_id": str(POINT_IDS[0]),
                    "role": "primary",
                    "weight": 0.7,
                },
                {
                    "knowledge_point_id": str(POINT_IDS[1]),
                    "role": "secondary",
                    "weight": 0.3,
                },
            ],
        },
    )
    assert confirmed.status_code == 200
    confirmed_body = confirmed.json()
    assert confirmed_body["status"] == "confirmed"
    assert confirmed_body["confirmed_at"] is not None
    assert confirmed_body["content_md"] == "定稿题面"
    mapped = confirmed_body["knowledge_points"]
    assert [entry["role"] for entry in mapped] == ["primary", "secondary"]
    assert mapped[0]["knowledge_point_name"] == "知识点1"

    pending = await client.get("/api/problems/pending")
    assert pending.json()["total"] == 0

    reopened = await client.post(f"/api/problems/{problem_id}/reopen")
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "draft"


@pytest.mark.asyncio
async def test_problem_lookup_by_knowledge_point_and_solutions(client: AsyncClient) -> None:
    body = await submit_draft(client)
    problem_id = body["id"]
    await client.post(
        f"/api/problems/{problem_id}/confirm",
        json={
            "content_md": "题面",
            "kind": "hard",
            "knowledge_points": [
                {
                    "knowledge_point_id": str(POINT_IDS[0]),
                    "role": "primary",
                    "weight": 1.0,
                }
            ],
        },
    )

    by_point = await client.get(f"/api/problems?kp_id={POINT_IDS[0]}")
    assert by_point.status_code == 200
    assert by_point.json()["total"] == 1

    other_point = await client.get(f"/api/problems?kp_id={POINT_IDS[1]}")
    assert other_point.json()["total"] == 0

    solution = await client.post(
        f"/api/problems/{problem_id}/solutions",
        json={"content_md": "洛必达法则", "method_tag": "洛必达", "source": "self"},
    )
    assert solution.status_code == 201
    solutions = solution.json()["solutions"]
    assert len(solutions) == 1
    assert solutions[0]["verified"] is True

    gpt_solution = await client.post(
        f"/api/problems/{problem_id}/solutions",
        json={"content_md": "泰勒展开", "source": "gpt"},
    )
    assert gpt_solution.json()["solutions"][1]["verified"] is False


@pytest.mark.asyncio
async def test_due_review_list_includes_drafts_and_respects_flag(client: AsyncClient) -> None:
    body = await submit_draft(client)
    problem_id = body["id"]

    due = await client.get("/api/problems/reviews/due")
    assert due.status_code == 200
    payload = due.json()
    assert payload["total"] == 1
    assert payload["problems"][0]["id"] == problem_id

    confirmed_only = await client.get("/api/problems/reviews/due?include_drafts=false")
    assert confirmed_only.json()["total"] == 0

    future = await client.get("/api/problems/reviews/due?as_of=2000-01-01")
    assert future.json()["total"] == 0


@pytest.mark.asyncio
async def test_review_grade_progression_updates_schedule(client: AsyncClient) -> None:
    body = await submit_draft(client)
    problem_id = body["id"]

    first = await client.post(
        f"/api/problems/{problem_id}/review?as_of=2026-07-16",
        json={"grade": "mastered"},
    )
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["reps"] == 1
    assert first_body["interval_days"] == 1
    assert first_body["due_date"] == "2026-07-17"
    assert first_body["ef"] > 2.5

    second = await client.post(
        f"/api/problems/{problem_id}/review?as_of=2026-07-17",
        json={"grade": "mastered"},
    )
    second_body = second.json()
    assert second_body["reps"] == 2
    assert second_body["interval_days"] == 6
    assert second_body["due_date"] == "2026-07-23"

    third = await client.post(
        f"/api/problems/{problem_id}/review?as_of=2026-07-23",
        json={"grade": "mastered"},
    )
    third_body = third.json()
    assert third_body["reps"] == 3
    assert third_body["interval_days"] == round(6 * third_body["ef"])


@pytest.mark.asyncio
async def test_review_forgot_resets_and_floors_ease_factor(client: AsyncClient) -> None:
    body = await submit_draft(client)
    problem_id = body["id"]

    await client.post(
        f"/api/problems/{problem_id}/review?as_of=2026-07-16",
        json={"grade": "mastered"},
    )
    await client.post(
        f"/api/problems/{problem_id}/review?as_of=2026-07-17",
        json={"grade": "mastered"},
    )

    forgot = await client.post(
        f"/api/problems/{problem_id}/review?as_of=2026-07-23",
        json={"grade": "forgot"},
    )
    forgot_body = forgot.json()
    assert forgot_body["reps"] == 0
    assert forgot_body["interval_days"] == 1
    assert forgot_body["due_date"] == "2026-07-24"

    for _ in range(6):
        forgot_body = (
            await client.post(
                f"/api/problems/{problem_id}/review?as_of=2026-07-24",
                json={"grade": "forgot"},
            )
        ).json()
    assert forgot_body["ef"] >= 1.3


@pytest.mark.asyncio
async def test_extract_returns_normalized_suggestions(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = await submit_draft(client)
    problem_id = body["id"]

    captured: dict[str, object] = {}

    async def fake_complete_chat(
        messages: list[dict[str, object]],
        settings: object,
        reasoning_effort: str | None = None,
    ) -> str:
        captured["messages"] = messages
        return (
            "```json\n"
            "{\"content_md\": \"求 $\\\\lim_{x\\\\to 0} \\\\frac{\\\\sin x}{x}$ 的值。\",\n"
            " \"knowledge_points\": ["
            f"{{\"knowledge_point_id\": \"{POINT_IDS[0]}\", \"weight\": 2}},"
            f"{{\"knowledge_point_id\": \"{uuid4()}\", \"weight\": 5}},"
            f"{{\"knowledge_point_id\": \"{POINT_IDS[1]}\", \"weight\": 1}}],\n"
            " \"solution\": {\"content_md\": \"等价无穷小替换，极限为 1。\","
            " \"method_tag\": \"等价无穷小\"}}\n"
            "```"
        )

    monkeypatch.setattr("graduate_entrance.ai.client.complete_chat", fake_complete_chat)

    response = await client.post(f"/api/problems/{problem_id}/extract")
    assert response.status_code == 200
    result = response.json()
    assert result["problem_id"] == problem_id
    assert result["content_md"].startswith("求 $\\lim")
    points = result["knowledge_points"]
    assert [entry["knowledge_point_id"] for entry in points] == [str(p) for p in POINT_IDS]
    assert points[0]["role"] == "primary"
    assert points[1]["role"] == "secondary"
    assert points[0]["knowledge_point_name"].endswith("知识点1")
    assert abs(sum(entry["weight"] for entry in points) - 1.0) < 1e-6
    assert points[0]["weight"] == pytest.approx(2 / 3, abs=0.002)
    assert result["solution"]["method_tag"] == "等价无穷小"

    messages = captured["messages"]
    assert isinstance(messages, list) and len(messages) == 2
    user_content = messages[1]["content"]
    assert isinstance(user_content, list)
    assert user_content[0]["type"] == "text"
    assert str(POINT_IDS[0]) in user_content[0]["text"]
    assert user_content[1]["type"] == "image_url"
    assert user_content[1]["image_url"]["url"].startswith("data:image/png;base64,")


@pytest.mark.asyncio
async def test_extract_invalid_json_returns_502(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = await submit_draft(client)

    async def fake_complete_chat(
        messages: list[dict[str, object]],
        settings: object,
        reasoning_effort: str | None = None,
    ) -> str:
        return "这不是 JSON"

    monkeypatch.setattr("graduate_entrance.ai.client.complete_chat", fake_complete_chat)

    response = await client.post(f"/api/problems/{body['id']}/extract")
    assert response.status_code == 502


@pytest.mark.asyncio
async def test_extract_unconfigured_returns_503(client: AsyncClient) -> None:
    body = await submit_draft(client)
    response = await client.post(f"/api/problems/{body['id']}/extract")
    assert response.status_code == 503


async def confirm_with_points(client: AsyncClient, problem_id: str, cause: str) -> None:
    response = await client.post(
        f"/api/problems/{problem_id}/confirm",
        json={
            "content_md": "题面",
            "kind": "wrong",
            "cause": cause,
            "knowledge_points": [
                {
                    "knowledge_point_id": str(POINT_IDS[0]),
                    "role": "primary",
                    "weight": 0.7,
                },
                {
                    "knowledge_point_id": str(POINT_IDS[1]),
                    "role": "secondary",
                    "weight": 0.3,
                },
            ],
        },
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_insights_aggregates_weakness_causes_and_trend(client: AsyncClient) -> None:
    first = await submit_draft(client)
    second = await submit_draft(client)
    await confirm_with_points(client, str(first["id"]), cause="concept")
    await confirm_with_points(client, str(second["id"]), cause="concept")

    forgot = await client.post(
        f"/api/problems/{first['id']}/review?as_of=2026-07-16",
        json={"grade": "forgot"},
    )
    assert forgot.status_code == 200
    mastered = await client.post(
        f"/api/problems/{second['id']}/review?as_of=2026-07-16",
        json={"grade": "mastered"},
    )
    assert mastered.status_code == 200

    response = await client.get("/api/stats/insights?as_of=2026-07-16")
    assert response.status_code == 200
    payload = response.json()

    assert payload["total_problems"] == 2
    assert payload["confirmed_problems"] == 2

    points = payload["knowledge_points"]
    assert len(points) == 2
    primary = next(
        p for p in points if p["knowledge_point_id"] == str(POINT_IDS[0])
    )
    assert primary["problem_count"] == 2
    assert primary["weighted_errors"] == pytest.approx(1.4)
    assert primary["forgot_reviews"] == 1
    assert primary["total_reviews"] == 2
    assert primary["weakness_score"] == pytest.approx(1.4 * 1.5)
    assert points[0]["knowledge_point_id"] == str(POINT_IDS[0])

    assert payload["causes"] == [{"cause": "concept", "count": 2}]

    subjects = payload["subjects"]
    assert len(subjects) == 1
    assert subjects[0]["subject_name"] == "数学一"
    assert subjects[0]["problem_count"] == 2
    assert subjects[0]["wrong_count"] == 2

    trend = payload["weekly_trend"]
    assert len(trend) == 8
    latest = trend[-1]
    assert latest["week_start"] == "2026-07-13"
    assert latest["reviews"] == 2
    assert latest["forgot"] == 1
    assert latest["mastered"] == 1
    assert latest["new_problems"] == 2
