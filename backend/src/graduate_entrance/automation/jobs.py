"""自动化 job：每次运行独立开 session，结果写入 automation_runs。"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.db.session import session_factory
from graduate_entrance.mastery.service import list_mastery_gaps
from graduate_entrance.models.automation import AutomationRun
from graduate_entrance.models.problems import Problem
from graduate_entrance.models.scheduling import AiWeekPlan, ScheduledTask
from graduate_entrance.scheduling.ai_week import generate_ai_week_plan
from graduate_entrance.vocab.service import vocab_stats

logger = logging.getLogger(__name__)

WEEKLY_PLAN_DRAFT = "weekly_plan_draft"
DAILY_MASTERY_WATCH = "daily_mastery_watch"
DAILY_BACKLOG_CHECK = "daily_backlog_check"

MASTERY_WATCH_MAX_INSERTS = 2
MASTERY_WATCH_MIN_GAP = 30.0
MASTERY_WATCH_EST_MINUTES = 30
VOCAB_BACKLOG_THRESHOLD = 100
REVIEW_BACKLOG_THRESHOLD = 20


async def _record_run(
    session: AsyncSession, job_name: str, status: str, detail: dict[str, Any]
) -> None:
    session.add(
        AutomationRun(id=uuid4(), job_name=job_name, status=status, detail=detail)
    )
    await session.commit()


async def run_weekly_plan_draft(as_of: date | None = None) -> str:
    """周日晚为下周生成 AI 计划草稿（不落正式任务，等用户确认）。"""
    today = as_of or date.today()
    next_week = today - timedelta(days=today.weekday()) + timedelta(weeks=1)
    async with session_factory() as session:
        existing = await session.scalar(
            select(AiWeekPlan).where(AiWeekPlan.week_start == next_week)
        )
        if existing is not None:
            await _record_run(
                session,
                WEEKLY_PLAN_DRAFT,
                "skipped",
                {
                    "week_start": next_week.isoformat(),
                    "reason": f"已存在 {existing.status} 计划",
                },
            )
            return "skipped"
        try:
            await generate_ai_week_plan(session, next_week, as_draft=True)
        except Exception as exc:
            logger.exception("weekly_plan_draft failed")
            await session.rollback()
            await _record_run(
                session,
                WEEKLY_PLAN_DRAFT,
                "failed",
                {"week_start": next_week.isoformat(), "error": str(exc)[:500]},
            )
            return "failed"
        await _record_run(
            session,
            WEEKLY_PLAN_DRAFT,
            "success",
            {"week_start": next_week.isoformat()},
        )
        return "success"


async def run_daily_mastery_watch(as_of: date | None = None) -> str:
    """每日为掌握度缺口最大的知识点自动补插复习任务（上限 2 条，可撤销）。"""
    today = as_of or date.today()
    async with session_factory() as session:
        try:
            gaps = await list_mastery_gaps(session, limit=20)
        except Exception as exc:
            logger.exception("daily_mastery_watch failed")
            await session.rollback()
            await _record_run(
                session,
                DAILY_MASTERY_WATCH,
                "failed",
                {"date": today.isoformat(), "error": str(exc)[:500]},
            )
            return "failed"
        candidates = [
            item
            for item in gaps.items
            if item.studied and item.gap >= MASTERY_WATCH_MIN_GAP
        ]
        existing_auto_today = (
            await session.scalar(
                select(func.count())
                .select_from(ScheduledTask)
                .where(
                    ScheduledTask.planned_date == today,
                    ScheduledTask.source == "auto",
                )
            )
            or 0
        )
        inserted: list[str] = []
        for item in candidates:
            if existing_auto_today + len(inserted) >= MASTERY_WATCH_MAX_INSERTS:
                break
            already_auto_today = await session.scalar(
                select(func.count())
                .select_from(ScheduledTask)
                .where(
                    ScheduledTask.planned_date == today,
                    ScheduledTask.knowledge_point_id == item.knowledge_point_id,
                )
            )
            if already_auto_today:
                continue
            session.add(
                ScheduledTask(
                    id=uuid4(),
                    subject_id=item.subject_id,
                    knowledge_point_id=item.knowledge_point_id,
                    phase_name="自动补漏",
                    subject_name=item.subject_name,
                    knowledge_point_name=item.knowledge_point_name,
                    material_name=None,
                    title=f"复习补漏：{item.knowledge_point_name}",
                    task_type="review",
                    planned_date=today,
                    est_minutes=MASTERY_WATCH_EST_MINUTES,
                    source="auto",
                    order=999,
                )
            )
            inserted.append(item.knowledge_point_name)
        status = "success" if inserted else "skipped"
        await _record_run(
            session,
            DAILY_MASTERY_WATCH,
            status,
            {"date": today.isoformat(), "inserted": inserted},
        )
        return status


async def run_daily_backlog_check(as_of: date | None = None) -> str:
    """每日检查单词/错题欠账，超阈值时留痕提醒（不自动重排计划）。"""
    today = as_of or date.today()
    async with session_factory() as session:
        try:
            vocab = await vocab_stats(session, today)
            review_due = (
                await session.scalar(
                    select(func.count())
                    .select_from(Problem)
                    .where(
                        Problem.due_date.is_not(None),
                        Problem.due_date <= today,
                        Problem.status == "confirmed",
                    )
                )
                or 0
            )
        except Exception as exc:
            logger.exception("daily_backlog_check failed")
            await session.rollback()
            await _record_run(
                session,
                DAILY_BACKLOG_CHECK,
                "failed",
                {"date": today.isoformat(), "error": str(exc)[:500]},
            )
            return "failed"
        alerts: list[str] = []
        if vocab.due_count > VOCAB_BACKLOG_THRESHOLD:
            alerts.append(f"单词到期欠账 {vocab.due_count} 个，建议加大每日词量")
        if review_due > REVIEW_BACKLOG_THRESHOLD:
            alerts.append(f"错题到期待复习 {review_due} 道，建议优先清复习队列")
        status = "success" if alerts else "skipped"
        await _record_run(
            session,
            DAILY_BACKLOG_CHECK,
            status,
            {"date": today.isoformat(), "alerts": alerts},
        )
        return status
