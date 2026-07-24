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


CONTENT_PAYLOAD = {
    "source": "ar5iv",
    "blocks": [
        {"type": "heading", "level": 1, "md": "RAG Survey"},
        {"type": "heading", "level": 2, "md": "Abstract"},
        {"type": "paragraph", "md": "We study retrieval."},
        {"type": "heading", "level": 2, "md": "1 Introduction"},
        {"type": "paragraph", "md": "Formula $\\pi_{\\theta}$ inline."},
    ],
}


async def _paper_id(client: AsyncClient) -> str:
    await client.post("/api/papers/sync", json=SYNC_PAYLOAD)
    body = (await client.get("/api/papers")).json()
    paper = body["groups"][0]["papers"][0]
    assert isinstance(paper["id"], str)
    return paper["id"]


@pytest.mark.asyncio
async def test_content_upload_read_and_toc(client: AsyncClient) -> None:
    paper_id = await _paper_id(client)

    missing = await client.get(f"/api/papers/{paper_id}/content")
    assert missing.status_code == 404

    upload = await client.put(
        f"/api/papers/{paper_id}/content", json=CONTENT_PAYLOAD
    )
    assert upload.status_code == 200
    assert upload.json()["paper"]["has_content"] is True

    body = (await client.get(f"/api/papers/{paper_id}/content")).json()
    assert body["source"] == "ar5iv"
    assert len(body["blocks"]) == 5
    assert body["toc"] == [
        {"title": "RAG Survey", "level": 1, "block_index": 0},
        {"title": "Abstract", "level": 2, "block_index": 1},
        {"title": "1 Introduction", "level": 2, "block_index": 3},
    ]

    listed = (await client.get("/api/papers")).json()
    flags = {
        paper["id"]: paper["has_content"]
        for group in listed["groups"]
        for paper in group["papers"]
    }
    assert flags[paper_id] is True
    assert sum(flags.values()) == 1


@pytest.mark.asyncio
async def test_content_upload_is_idempotent_overwrite(client: AsyncClient) -> None:
    paper_id = await _paper_id(client)
    await client.put(f"/api/papers/{paper_id}/content", json=CONTENT_PAYLOAD)

    replaced = {
        "source": "pdf",
        "blocks": [{"type": "paragraph", "md": "plain text only"}],
    }
    second = await client.put(f"/api/papers/{paper_id}/content", json=replaced)
    assert second.status_code == 200

    body = (await client.get(f"/api/papers/{paper_id}/content")).json()
    assert body["source"] == "pdf"
    assert len(body["blocks"]) == 1
    assert body["toc"] == []


@pytest.mark.asyncio
async def test_content_unknown_paper_returns_404(client: AsyncClient) -> None:
    response = await client.put(
        "/api/papers/00000000-0000-0000-0000-000000000000/content",
        json=CONTENT_PAYLOAD,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_annotation_crud(client: AsyncClient) -> None:
    paper_id = await _paper_id(client)
    await client.put(f"/api/papers/{paper_id}/content", json=CONTENT_PAYLOAD)

    created = await client.post(
        f"/api/papers/{paper_id}/annotations",
        json={"block_index": 2, "excerpt": "We study retrieval.", "note": "核心论点"},
    )
    assert created.status_code == 201
    annotation = created.json()
    assert annotation["color"] == "yellow"
    assert annotation["note"] == "核心论点"

    listed = (await client.get(f"/api/papers/{paper_id}/annotations")).json()
    assert len(listed["annotations"]) == 1

    patched = await client.patch(
        f"/api/papers/annotations/{annotation['id']}",
        json={"note": "改后的批注", "color": "green"},
    )
    assert patched.status_code == 200
    assert patched.json()["note"] == "改后的批注"
    assert patched.json()["color"] == "green"

    deleted = await client.delete(f"/api/papers/annotations/{annotation['id']}")
    assert deleted.status_code == 204
    empty = (await client.get(f"/api/papers/{paper_id}/annotations")).json()
    assert empty["annotations"] == []


@pytest.mark.asyncio
async def test_annotation_rejects_out_of_range_block(client: AsyncClient) -> None:
    paper_id = await _paper_id(client)
    no_content = await client.post(
        f"/api/papers/{paper_id}/annotations",
        json={"block_index": 0},
    )
    assert no_content.status_code == 400

    await client.put(f"/api/papers/{paper_id}/content", json=CONTENT_PAYLOAD)
    out_of_range = await client.post(
        f"/api/papers/{paper_id}/annotations",
        json={"block_index": 99},
    )
    assert out_of_range.status_code == 400
