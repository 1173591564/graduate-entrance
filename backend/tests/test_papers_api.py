import io
from collections.abc import AsyncIterator
from pathlib import Path

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

SYNC_PAYLOAD = {
    "papers": [
        {
            "rel_path": "RAG/survey.pdf",
            "title": "RAG Survey",
            "category": "RAG",
            "size_bytes": 1200,
        },
        {"rel_path": "Agents/react.pdf", "category": "Agents", "size_bytes": 900},
        {
            "rel_path": "RAG/self-rag.pdf",
            "title": "Self-RAG",
            "category": "RAG",
            "size_bytes": 80,
        },
    ]
}


@pytest_asyncio.fixture
async def client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    engine = create_async_engine("sqlite+aiosqlite://")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    get_settings().papers_dir = tmp_path / "papers"

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
    get_settings.cache_clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_sync_is_idempotent(client: AsyncClient) -> None:
    first = await client.post("/api/papers/sync", json=SYNC_PAYLOAD)
    assert first.status_code == 200
    assert first.json() == {"imported": 3, "updated": 0, "total_count": 3}

    second = await client.post("/api/papers/sync", json=SYNC_PAYLOAD)
    assert second.json() == {"imported": 0, "updated": 3, "total_count": 3}


@pytest.mark.asyncio
async def test_list_groups_by_category_and_derives_title(client: AsyncClient) -> None:
    await client.post("/api/papers/sync", json=SYNC_PAYLOAD)
    body = (await client.get("/api/papers")).json()
    categories = [group["category"] for group in body["groups"]]
    assert categories == ["Agents", "RAG"]
    agents = body["groups"][0]["papers"][0]
    assert agents["title"] == "react"
    assert agents["has_file"] is False
    assert body["stats"] == {
        "total_count": 3,
        "unread_count": 3,
        "reading_count": 0,
        "done_count": 0,
    }


@pytest.mark.asyncio
async def test_today_prefers_reading_then_unread(client: AsyncClient) -> None:
    await client.post("/api/papers/sync", json=SYNC_PAYLOAD)
    today = (await client.get("/api/papers/today")).json()
    first_pick = today["paper"]["id"]

    reading = (await client.get("/api/papers")).json()["groups"][1]["papers"][0]["id"]
    await client.post(
        f"/api/papers/{reading}/status",
        json={"status": "reading", "as_of": "2026-07-20"},
    )
    today_after = (await client.get("/api/papers/today")).json()
    assert today_after["paper"]["id"] == reading
    assert today_after["stats"]["reading_count"] == 1
    assert first_pick is not None


@pytest.mark.asyncio
async def test_status_transitions_track_dates(client: AsyncClient) -> None:
    await client.post("/api/papers/sync", json=SYNC_PAYLOAD)
    paper_id = (await client.get("/api/papers")).json()["groups"][0]["papers"][0]["id"]

    done = await client.post(
        f"/api/papers/{paper_id}/status",
        json={"status": "done", "as_of": "2026-07-20"},
    )
    body = done.json()["paper"]
    assert body["status"] == "done"
    assert body["started_on"] == "2026-07-20"
    assert body["finished_on"] == "2026-07-20"

    reset = await client.post(
        f"/api/papers/{paper_id}/status",
        json={"status": "unread"},
    )
    reset_body = reset.json()["paper"]
    assert reset_body["started_on"] is None
    assert reset_body["finished_on"] is None


@pytest.mark.asyncio
async def test_status_unknown_paper_returns_404(client: AsyncClient) -> None:
    response = await client.post(
        "/api/papers/00000000-0000-0000-0000-000000000000/status",
        json={"status": "reading"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_upload_and_download_pdf(client: AsyncClient) -> None:
    await client.post("/api/papers/sync", json=SYNC_PAYLOAD)
    paper_id = (await client.get("/api/papers")).json()["groups"][0]["papers"][0]["id"]

    missing = await client.get(f"/api/papers/{paper_id}/file")
    assert missing.status_code == 404

    pdf_bytes = b"%PDF-1.4 fake"
    upload = await client.post(
        f"/api/papers/{paper_id}/file",
        files={"file": ("react.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload.status_code == 200
    assert upload.json()["has_file"] is True

    download = await client.get(f"/api/papers/{paper_id}/file")
    assert download.status_code == 200
    assert download.content == pdf_bytes


@pytest.mark.asyncio
async def test_upload_rejects_non_pdf(client: AsyncClient) -> None:
    await client.post("/api/papers/sync", json=SYNC_PAYLOAD)
    paper_id = (await client.get("/api/papers")).json()["groups"][0]["papers"][0]["id"]
    response = await client.post(
        f"/api/papers/{paper_id}/file",
        files={"file": ("x.txt", io.BytesIO(b"nope"), "text/plain")},
    )
    assert response.status_code == 400
