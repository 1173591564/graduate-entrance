from collections.abc import AsyncIterator
from typing import Any

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

PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d4944415478da63f8ffff3f0300050001ff8f7ad10000000049454e"
    "44ae426082"
)


@pytest_asyncio.fixture
async def client(tmp_path: Any) -> AsyncIterator[AsyncClient]:
    get_settings().chat_images_dir = tmp_path / "chat-images"
    engine = create_async_engine("sqlite+aiosqlite://")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

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


def _fake_ai(monkeypatch: pytest.MonkeyPatch, reply: str = "这是回答") -> list[Any]:
    calls: list[Any] = []

    async def fake_complete_chat(
        messages: list[dict[str, object]],
        settings: object,
        reasoning_effort: str | None = None,
    ) -> str:
        calls.append(messages)
        return reply

    monkeypatch.setattr("graduate_entrance.ai.client.complete_chat", fake_complete_chat)
    return calls


@pytest.mark.asyncio
async def test_send_message_creates_conversation_and_reply(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _fake_ai(monkeypatch, "极限等于 1")
    response = await client.post(
        "/api/chat/messages",
        data={"content": "这道题极限怎么求？"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["conversation"]["title"] == "这道题极限怎么求？"
    assert body["user_message"]["role"] == "user"
    assert body["reply"]["role"] == "assistant"
    assert body["reply"]["content_md"] == "极限等于 1"
    assert calls[0][0]["role"] == "system"
    assert calls[0][-1] == {"role": "user", "content": "这道题极限怎么求？"}


@pytest.mark.asyncio
async def test_send_message_continues_conversation_with_history(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _fake_ai(monkeypatch)
    first = await client.post("/api/chat/messages", data={"content": "第一问"})
    conversation_id = first.json()["conversation"]["id"]
    second = await client.post(
        "/api/chat/messages",
        data={"conversation_id": conversation_id, "content": "第二问"},
    )
    assert second.status_code == 200
    assert second.json()["conversation"]["id"] == conversation_id
    roles = [entry["role"] for entry in calls[1]]
    assert roles == ["system", "user", "assistant", "user"]

    history = await client.get(f"/api/chat/conversations/{conversation_id}")
    assert history.status_code == 200
    messages = history.json()["messages"]
    assert [message["role"] for message in messages] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]


@pytest.mark.asyncio
async def test_send_message_with_image(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _fake_ai(monkeypatch)
    response = await client.post(
        "/api/chat/messages",
        data={"content": "看图解题"},
        files=[("images", ("problem.png", PNG_BYTES, "image/png"))],
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["user_message"]["images"]) == 1
    content = calls[0][-1]["content"]
    assert isinstance(content, list)
    assert content[0] == {"type": "text", "text": "看图解题"}
    assert content[1]["type"] == "image_url"

    image_name = body["user_message"]["images"][0]
    image_response = await client.get(f"/api/chat/images/{image_name}")
    assert image_response.status_code == 200


@pytest.mark.asyncio
async def test_send_empty_message_rejected(client: AsyncClient) -> None:
    response = await client.post("/api/chat/messages", data={"content": "  "})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_and_delete_conversations(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_ai(monkeypatch)
    created = await client.post("/api/chat/messages", data={"content": "问题 A"})
    conversation_id = created.json()["conversation"]["id"]

    listing = await client.get("/api/chat/conversations")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    deleted = await client.delete(f"/api/chat/conversations/{conversation_id}")
    assert deleted.status_code == 204
    listing_after = await client.get("/api/chat/conversations")
    assert listing_after.json()["total"] == 0

    missing = await client.get(f"/api/chat/conversations/{conversation_id}")
    assert missing.status_code == 404
