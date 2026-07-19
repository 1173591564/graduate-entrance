"""进程内 APScheduler：单实例部署下驱动自动化 job。"""

from __future__ import annotations

import logging
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
