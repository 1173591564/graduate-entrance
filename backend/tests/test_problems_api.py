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
