from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from graduate_entrance.chat import summarize
from graduate_entrance.core.config import Settings
from graduate_entrance.db.base import Base
from graduate_entrance.models.chat import ChatConversation, ChatMessage


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
    monkeypatch.setattr(summarize, "session_factory", factory)
    yield factory
    await engine.dispose()


async def _seed_conversation(
    factory: async_sessionmaker[AsyncSession], message_count: int
) -> UUID:
    base = datetime(2026, 7, 20, 8, 0, tzinfo=UTC)
    async with factory() as session:
        conversation = ChatConversation(id=uuid4(), title="长对话")
        session.add(conversation)
        await session.flush()
        for index in range(message_count):
            session.add(
                ChatMessage(
                    id=uuid4(),
                    conversation_id=conversation.id,
                    role="user" if index % 2 == 0 else "assistant",
                    content_md=f"消息{index}",
                    images=[],
                    created_at=base + timedelta(minutes=index),
                )
            )
        await session.commit()
        return conversation.id


@pytest.mark.asyncio
async def test_folds_older_messages_into_summary(
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conversation_id = await _seed_conversation(session_factory, summarize.HISTORY_LIMIT + 4)

    captured: dict[str, object] = {}

    async def fake_complete_chat(
        messages: list[dict[str, object]],
        settings: object,
        reasoning_effort: str | None = None,
    ) -> str:
        assert reasoning_effort == "low"
        captured["user"] = messages[-1]["content"]
        return "学生反复问极限与泰勒展开，数学一薄弱。"

    monkeypatch.setattr(summarize, "complete_chat", fake_complete_chat)

    updated = await summarize.summarize_conversation(
        conversation_id, _configured_settings()
    )
    assert updated is True

    async with session_factory() as session:
        conversation = (
            await session.execute(
                select(ChatConversation).where(ChatConversation.id == conversation_id)
            )
        ).scalar_one()
        assert conversation.summary == "学生反复问极限与泰勒展开，数学一薄弱。"
        assert conversation.summary_upto_message_id is not None
    # Only the 4 messages pushed out of the window are folded.
    assert "消息3" in str(captured["user"])
    assert "消息4" not in str(captured["user"])


@pytest.mark.asyncio
async def test_short_conversation_is_skipped(
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conversation_id = await _seed_conversation(session_factory, summarize.HISTORY_LIMIT)

    async def fail(*args: object, **kwargs: object) -> str:
        raise AssertionError("complete_chat should not be called")

    monkeypatch.setattr(summarize, "complete_chat", fail)

    updated = await summarize.summarize_conversation(
        conversation_id, _configured_settings()
    )
    assert updated is False


@pytest.mark.asyncio
async def test_incremental_folds_only_new_messages(
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conversation_id = await _seed_conversation(session_factory, summarize.HISTORY_LIMIT + 2)

    prompts: list[str] = []

    async def fake_complete_chat(
        messages: list[dict[str, object]],
        settings: object,
        reasoning_effort: str | None = None,
    ) -> str:
        prompts.append(str(messages[-1]["content"]))
        return f"摘要 v{len(prompts)}"

    monkeypatch.setattr(summarize, "complete_chat", fake_complete_chat)

    assert await summarize.summarize_conversation(
        conversation_id, _configured_settings()
    )

    # Append two more messages so two older turns fall out of the window.
    base = datetime(2026, 7, 20, 12, 0, tzinfo=UTC)
    async with session_factory() as session:
        for index in range(2):
            session.add(
                ChatMessage(
                    id=uuid4(),
                    conversation_id=conversation_id,
                    role="user",
                    content_md=f"新消息{index}",
                    images=[],
                    created_at=base + timedelta(minutes=index),
                )
            )
        await session.commit()

    assert await summarize.summarize_conversation(
        conversation_id, _configured_settings()
    )

    # The second pass carries the prior summary and only the newly-evicted turns.
    assert "摘要 v1" in prompts[1]
    assert "消息2" in prompts[1]
    assert "消息0" not in prompts[1]


@pytest.mark.asyncio
async def test_unconfigured_ai_skips(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    conversation_id = await _seed_conversation(session_factory, summarize.HISTORY_LIMIT + 2)
    assert (
        await summarize.summarize_conversation(conversation_id, Settings()) is False
    )
