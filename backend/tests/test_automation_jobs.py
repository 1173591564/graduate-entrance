from collections.abc import AsyncIterator
from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from graduate_entrance.automation import jobs
from graduate_entrance.db.base import Base
from graduate_entrance.models.automation import AutomationRun
from graduate_entrance.models.scheduling import ScheduledTask
from graduate_entrance.models.vocab import VocabWord
from graduate_entrance.schemas.mastery import MasteryGap, MasteryGapResponse

AS_OF = date(2026, 7, 20)


@pytest_asyncio.fixture
async def session_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite://")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    monkeypatch.setattr(jobs, "session_factory", factory)
    yield factory
    await engine.dispose()


def _gap(name: str, gap: float, studied: bool = True) -> MasteryGap:
    return MasteryGap(
        knowledge_point_id=uuid4(),
        knowledge_point_name=name,
        subject_id=uuid4(),
        subject_name="数学一",
        mastery=100.0 - gap,
        target=100.0,
        gap=gap,
        studied=studied,
    )


def _gap_response(items: list[MasteryGap]) -> MasteryGapResponse:
    return MasteryGapResponse(
        generated_at=datetime(2026, 7, 20),
        knowledge_point_total=len(items),
        gap_count=len(items),
        items=items,
    )


@pytest.mark.asyncio
async def test_mastery_watch_inserts_capped_auto_tasks(
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gaps = _gap_response(
        [
            _gap("重要极限", 80.0),
            _gap("泰勒公式", 70.0),
            _gap("级数收敛", 60.0),
            _gap("未学知识点", 90.0, studied=False),
        ]
    )

    async def fake_gaps(session: object, limit: int = 20) -> MasteryGapResponse:
        return gaps

    monkeypatch.setattr(jobs, "list_mastery_gaps", fake_gaps)

    result = await jobs.run_daily_mastery_watch(as_of=AS_OF)
    assert result == "success"

    async with session_factory() as session:
        tasks = (await session.scalars(select(ScheduledTask))).all()
        assert len(tasks) == 2
        assert all(task.source == "auto" for task in tasks)
        assert {task.knowledge_point_name for task in tasks} == {
            "重要极限",
            "泰勒公式",
        }
        runs = (await session.scalars(select(AutomationRun))).all()
        assert runs[0].status == "success"

    # 再跑一次：当天已有同知识点任务，跳过
    result = await jobs.run_daily_mastery_watch(as_of=AS_OF)
    assert result == "skipped"
    async with session_factory() as session:
        tasks = (await session.scalars(select(ScheduledTask))).all()
        assert len(tasks) == 2


@pytest.mark.asyncio
async def test_mastery_watch_skips_small_gaps(
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_gaps(session: object, limit: int = 20) -> MasteryGapResponse:
        return _gap_response([_gap("小缺口", 10.0)])

    monkeypatch.setattr(jobs, "list_mastery_gaps", fake_gaps)
    result = await jobs.run_daily_mastery_watch(as_of=AS_OF)
    assert result == "skipped"


@pytest.mark.asyncio
async def test_backlog_check_alerts_on_vocab_backlog(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        for index in range(jobs.VOCAB_BACKLOG_THRESHOLD + 1):
            session.add(
                VocabWord(
                    id=uuid4(),
                    word=f"word{index}",
                    meaning="含义",
                    phonetic="",
                    example_en="",
                    example_zh="",
                    book_page=1,
                    reps=1,
                    due_date=AS_OF - timedelta(days=1),
                )
            )
        await session.commit()

    result = await jobs.run_daily_backlog_check(as_of=AS_OF)
    assert result == "success"

    async with session_factory() as session:
        run = (await session.scalars(select(AutomationRun))).one()
        assert run.job_name == "daily_backlog_check"
        assert any("单词到期欠账" in alert for alert in run.detail["alerts"])


@pytest.mark.asyncio
async def test_backlog_check_skips_when_clean(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    result = await jobs.run_daily_backlog_check(as_of=AS_OF)
    assert result == "skipped"
