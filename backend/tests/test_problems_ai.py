from collections.abc import AsyncIterator
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

from graduate_entrance.core.config import get_settings
from graduate_entrance.db.base import Base
from graduate_entrance.db.session import get_session
from graduate_entrance.main import app
from graduate_entrance.models.syllabus import Subject

MATH_ID = uuid4()
ENGLISH_ID = uuid4()

PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d4944415478da63f8ffff3f0300050001ff8f7ad10000000049454e"
    "44ae426082"
)


@pytest_asyncio.fixture
async def client(tmp_path: Any) -> AsyncIterator[AsyncClient]:
    get_settings().problem_images_dir = tmp_path / "problem-images"
    engine = create_async_engine("sqlite+aiosqlite://")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        session.add(Subject(id=MATH_ID, code="math1", name="数学一", order=1))
        session.add(Subject(id=ENGLISH_ID, code="english1", name="英语一", order=3))
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


async def submit_english_draft(client: AsyncClient, answer: str = "") -> dict[str, Any]:
    response = await client.post(
        "/api/problems",
        data={
            "subject_id": str(ENGLISH_ID),
            "kind": "wrong",
            "content_md": "Write an essay about environmental protection.",
            "my_answer_md": answer,
        },
    )
    assert response.status_code == 201
    body: dict[str, Any] = response.json()
    return body


@pytest.mark.asyncio
async def test_batch_upload_extracts_each_image(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_complete_chat(messages: list[dict[str, object]], settings: object) -> str:
        return '{"content_md": "识别的题面", "knowledge_points": [], "solution": null}'

    monkeypatch.setattr("graduate_entrance.ai.client.complete_chat", fake_complete_chat)

    response = await client.post(
        "/api/problems/batch",
        data={"subject_id": str(MATH_ID), "kind": "wrong", "source_ref": "真题 2021"},
        files=[
            ("images", ("a.png", PNG_BYTES, "image/png")),
            ("images", ("b.png", PNG_BYTES, "image/png")),
        ],
    )
    assert response.status_code == 201
    body = response.json()
    assert body["total"] == 2
    assert body["extracted"] == 2
    for item in body["items"]:
        assert item["error"] is None
        assert item["extraction"]["content_md"] == "识别的题面"
        assert item["problem"]["status"] == "draft"
        assert len(item["problem"]["images"]) == 1

    pending = await client.get("/api/problems/pending")
    assert pending.json()["total"] == 2


@pytest.mark.asyncio
async def test_batch_upload_reports_per_item_errors(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = {"count": 0}

    async def fake_complete_chat(messages: list[dict[str, object]], settings: object) -> str:
        calls["count"] += 1
        if calls["count"] == 1:
            return "not json"
        return '{"content_md": "第二题", "knowledge_points": [], "solution": null}'

    monkeypatch.setattr("graduate_entrance.ai.client.complete_chat", fake_complete_chat)

    response = await client.post(
        "/api/problems/batch",
        data={"subject_id": str(MATH_ID)},
        files=[
            ("images", ("a.png", PNG_BYTES, "image/png")),
            ("images", ("b.png", PNG_BYTES, "image/png")),
        ],
    )
    assert response.status_code == 201
    body = response.json()
    assert body["total"] == 2
    assert body["extracted"] == 1
    assert body["items"][0]["extraction"] is None
    assert body["items"][0]["error"]
    assert body["items"][1]["extraction"]["content_md"] == "第二题"


@pytest.mark.asyncio
async def test_grade_persists_score_and_feedback(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_complete_chat(messages: list[dict[str, object]], settings: object) -> str:
        return (
            '{"score": 72.5, "feedback_md": "结构完整，第二段论证薄弱。",'
            ' "suggestions": ["增加数据支撑", "替换重复词汇"]}'
        )

    monkeypatch.setattr("graduate_entrance.ai.client.complete_chat", fake_complete_chat)

    body = await submit_english_draft(client, answer="My essay draft ...")
    response = await client.post(f"/api/problems/{body['id']}/grade", json={"answer_md": ""})
    assert response.status_code == 200
    result = response.json()
    assert result["score"] == 72.5
    assert "论证薄弱" in result["feedback_md"]
    assert result["suggestions"] == ["增加数据支撑", "替换重复词汇"]

    stored = await client.get(f"/api/problems/{body['id']}")
    assert stored.json()["ai_score"] == 72.5
    assert stored.json()["ai_feedback_md"] == "结构完整，第二段论证薄弱。"
    assert stored.json()["ai_graded_at"] is not None


@pytest.mark.asyncio
async def test_grade_rejects_math_subject(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_complete_chat(messages: list[dict[str, object]], settings: object) -> str:
        return '{"score": 90, "feedback_md": "", "suggestions": []}'

    monkeypatch.setattr("graduate_entrance.ai.client.complete_chat", fake_complete_chat)

    response = await client.post(
        "/api/problems",
        data={"subject_id": str(MATH_ID), "kind": "wrong", "content_md": "求极限"},
    )
    problem_id = response.json()["id"]
    graded = await client.post(f"/api/problems/{problem_id}/grade", json={"answer_md": "x=1"})
    assert graded.status_code == 400
    assert "英语、政治" in graded.json()["error"]["message"]


@pytest.mark.asyncio
async def test_grade_requires_answer(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_complete_chat(messages: list[dict[str, object]], settings: object) -> str:
        return '{"score": 90, "feedback_md": "", "suggestions": []}'

    monkeypatch.setattr("graduate_entrance.ai.client.complete_chat", fake_complete_chat)

    body = await submit_english_draft(client)
    graded = await client.post(f"/api/problems/{body['id']}/grade", json={"answer_md": " "})
    assert graded.status_code == 400
    assert "作答" in graded.json()["error"]["message"]
