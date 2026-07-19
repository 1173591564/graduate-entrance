from collections.abc import AsyncIterator
from datetime import date, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from graduate_entrance.db.base import Base
from graduate_entrance.models.essay import EssayMaterial
from graduate_entrance.models.vocab import VocabWord
from graduate_entrance.profile.learning_snapshot import (
    build_learning_snapshot,
    snapshot_text,
)

AS_OF = date(2026, 7, 20)


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite://")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as db:
        yield db
    await engine.dispose()


@pytest.mark.asyncio
async def test_snapshot_cold_start(session: AsyncSession) -> None:
    snapshot = await build_learning_snapshot(session, AS_OF)
    assert snapshot.vocab_total == 0
    assert snapshot.review_due == 0
    text = snapshot_text(snapshot)
    assert "（未导入词库）" in text
    assert "（暂无背诵条目）" in text
    assert "（暂无）" in text


@pytest.mark.asyncio
async def test_snapshot_counts_vocab_and_essay_backlog(
    session: AsyncSession,
) -> None:
    session.add(
        VocabWord(
            id=uuid4(),
            word="abandon",
            meaning="放弃",
            phonetic="",
            example_en="",
            example_zh="",
            book_page=1,
            reps=1,
            due_date=AS_OF - timedelta(days=1),
        )
    )
    session.add(
        EssayMaterial(
            title="范文一",
            category="sentence",
            topic="教育",
            content_md="...",
            translation_md="",
            source="",
            due_date=AS_OF,
        )
    )
    await session.commit()

    snapshot = await build_learning_snapshot(session, AS_OF)
    assert snapshot.vocab_due == 1
    assert snapshot.vocab_total == 1
    assert snapshot.essay_due == 1
    text = snapshot_text(snapshot)
    assert "到期待复习 1 个" in text
    assert "作文素材到期待背：1 篇" in text
