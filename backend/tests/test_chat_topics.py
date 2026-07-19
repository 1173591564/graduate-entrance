from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from graduate_entrance.chat import topics
from graduate_entrance.core.config import Settings
from graduate_entrance.db.base import Base
from graduate_entrance.models.chat import ChatConversation, ChatMessage, ChatTopicTag


def _configured_settings() -> Settings:
    return Settings(
        ai_base_url="https://relay.example.com/v1",
        ai_api_key="test-key",
        ai_model="gpt-5.5",
    )


@pytest_asyncio.fixture
async def session_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite://")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    monkeypatch.setattr(topics, "session_factory", factory)
    yield factory
    await engine.dispose()


async def _seed_message(factory: async_sessionmaker[AsyncSession]) -> ChatMessage:
    async with factory() as session:
        conversation = ChatConversation(id=uuid4(), title="测试")
        session.add(conversation)
        await session.flush()
        message = ChatMessage(
            id=uuid4(),
            conversation_id=conversation.id,
            role="assistant",
            content_md="答案",
            images=[],
        )
        session.add(message)
        await session.commit()
        return message


@pytest.mark.asyncio
async def test_tags_are_persisted(
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = await _seed_message(session_factory)

    async def fake_complete_chat(
        messages: list[dict[str, object]],
        settings: object,
        reasoning_effort: str | None = None,
    ) -> str:
        assert reasoning_effort == "low"
        return (
            '[{"subject": "数学一", "topic": "泰勒公式"},'
            ' {"subject": "408", "topic": "拓扑排序"}]'
        )

    monkeypatch.setattr(topics, "complete_chat", fake_complete_chat)

    written = await topics.tag_message_topics(
        message.id, "泰勒公式怎么展开", "答案", _configured_settings()
    )
    assert written == 2

    async with session_factory() as session:
        tags = (await session.scalars(select(ChatTopicTag))).all()
        assert {(tag.subject, tag.topic) for tag in tags} == {
            ("数学一", "泰勒公式"),
            ("408", "拓扑排序"),
        }


@pytest.mark.asyncio
async def test_unconfigured_ai_skips(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    written = await topics.tag_message_topics(uuid4(), "问", "答", Settings())
    assert written == 0


@pytest.mark.asyncio
async def test_invalid_json_is_ignored(
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_complete_chat(
        messages: list[dict[str, object]],
        settings: object,
        reasoning_effort: str | None = None,
    ) -> str:
        return "这不是 JSON"

    monkeypatch.setattr(topics, "complete_chat", fake_complete_chat)
    written = await topics.tag_message_topics(
        uuid4(), "问", "答", _configured_settings()
    )
    assert written == 0


def test_parse_tags_handles_fenced_json() -> None:
    raw = '```json\n[{"subject": "政治", "topic": "矛盾论"}]\n```'
    assert topics._parse_tags(raw) == [("政治", "矛盾论")]


def test_parse_tags_drops_malformed_entries() -> None:
    raw = '[{"subject": "数学一"}, "oops", {"subject": "408", "topic": "B树"}]'
    assert topics._parse_tags(raw) == [("408", "B树")]
