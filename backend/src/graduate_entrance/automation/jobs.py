"""自动化 job：每次运行独立开 session，结果写入 automation_runs。"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.db.session import session_factory
from graduate_entrance.models.automation import AutomationRun
from graduate_entrance.models.scheduling import AiWeekPlan
from graduate_entrance.scheduling.ai_week import generate_ai_week_plan

logger = logging.getLogger(__name__)

WEEKLY_PLAN_DRAFT = "weekly_plan_draft"


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
