"""进程内 APScheduler：单实例部署下驱动自动化 job。"""

from __future__ import annotations

import logging
from collections.abc import Coroutine
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from graduate_entrance.automation.jobs import (
    DAILY_BACKLOG_CHECK,
    DAILY_MASTERY_WATCH,
    WEEKLY_PLAN_DRAFT,
    run_daily_backlog_check,
    run_daily_mastery_watch,
    run_weekly_plan_draft,
)
from graduate_entrance.core.config import Settings

logger = logging.getLogger(__name__)

MISFIRE_GRACE_SECONDS = 6 * 3600


def create_scheduler(settings: Settings) -> AsyncIOScheduler:
    timezone = ZoneInfo(settings.automation_timezone)
    scheduler = AsyncIOScheduler(timezone=timezone)
    scheduler.add_job(
        run_weekly_plan_draft,
        CronTrigger(day_of_week="sun", hour=21, minute=0, timezone=timezone),
        id=WEEKLY_PLAN_DRAFT,
        coalesce=True,
        misfire_grace_time=MISFIRE_GRACE_SECONDS,
    )
    scheduler.add_job(
        run_daily_mastery_watch,
        CronTrigger(hour=6, minute=0, timezone=timezone),
        id=DAILY_MASTERY_WATCH,
        coalesce=True,
        misfire_grace_time=MISFIRE_GRACE_SECONDS,
    )
    scheduler.add_job(
        run_daily_backlog_check,
        CronTrigger(hour=6, minute=5, timezone=timezone),
        id=DAILY_BACKLOG_CHECK,
        coalesce=True,
        misfire_grace_time=MISFIRE_GRACE_SECONDS,
    )
    return scheduler


async def run_startup_catchup(settings: Settings) -> None:
    """Re-run jobs whose scheduled moment already passed but were missed while down.

    The in-memory scheduler cannot recover misfires across a restart, so on
    startup we attempt each job whose trigger time has elapsed. Every job
    self-skips when its target date already has a successful run, so this is
    idempotent and cheap.
    """
    now = datetime.now(ZoneInfo(settings.automation_timezone))
    daily_due = now.replace(hour=6, minute=0, second=0, microsecond=0)
    backlog_due = now.replace(hour=6, minute=5, second=0, microsecond=0)
    tasks: list[tuple[str, Coroutine[Any, Any, str]]] = []
    if now >= daily_due:
        tasks.append((DAILY_MASTERY_WATCH, run_daily_mastery_watch()))
    if now >= backlog_due:
        tasks.append((DAILY_BACKLOG_CHECK, run_daily_backlog_check()))
    if now.weekday() == 6 and now.hour >= 21:
        tasks.append((WEEKLY_PLAN_DRAFT, run_weekly_plan_draft()))
    for job_name, coro in tasks:
        try:
            result = await coro
            if result != "skipped":
                logger.info("startup catch-up ran %s -> %s", job_name, result)
        except Exception:
            logger.exception("startup catch-up for %s failed", job_name)
