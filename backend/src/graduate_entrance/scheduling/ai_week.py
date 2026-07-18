import json
import re
from collections import defaultdict
from datetime import date, timedelta
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.ai import client as ai_client
from graduate_entrance.core.config import Settings, get_settings
from graduate_entrance.models.scheduling import AiWeekPlan
from graduate_entrance.problems.insights import get_problem_insights
from graduate_entrance.scheduling.service import persist_plan, preview_plan
from graduate_entrance.schemas.scheduling import (
    AiDailyFocus,
    AiWeekAdvice,
    AiWeekPlanResponse,
    PlanGenerationRequest,
    PlanResponse,
)

MAX_WEAK_POINTS = 6
JSON_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)

SYSTEM_PROMPT = (
    "你是一名 11408 考研备考规划师。根据下周已排定的每日任务、每日可用时长和薄弱知识点，"
    "输出严格的 JSON 对象（不要用 Markdown 代码块包裹），字段如下：\n"
    '{"summary": "本周策略总结（120 字以内，指出重点科目与薄弱点安排）",\n'
    ' "daily_focus": [{"date": "YYYY-MM-DD", "focus": "当天学习重点与建议（40 字以内）"}],\n'
    ' "review_suggestions": ["针对薄弱知识点的复习建议（每条 40 字以内，至多 4 条）"]}\n'
    "要求：daily_focus 覆盖下周每一天（无任务的天给休整或复习建议）；"
    "建议要具体可执行，紧扣给出的任务与薄弱点。"
)


def next_week_start(as_of: date) -> date:
    return as_of - timedelta(days=as_of.weekday()) + timedelta(weeks=1)


def _parse_advice_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    match = JSON_FENCE_PATTERN.match(text)
    if match:
        text = match.group(1)
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI week plan returned invalid JSON",
        ) from exc
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI week plan returned invalid JSON",
        )
    return data


def _normalize_daily_focus(
    entries: Any, week_start: date
) -> list[AiDailyFocus]:
    week_dates = [week_start + timedelta(days=offset) for offset in range(7)]
    by_date: dict[date, str] = {}
    if isinstance(entries, list):
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            focus = entry.get("focus")
            if not isinstance(focus, str) or not focus.strip():
                continue
            try:
                day = date.fromisoformat(str(entry.get("date")))
            except ValueError:
                continue
            if day in set(week_dates):
                by_date.setdefault(day, focus.strip())
    return [
        AiDailyFocus(date=day, focus=by_date.get(day, "按计划推进当日任务"))
        for day in week_dates
    ]


def _normalize_suggestions(entries: Any) -> list[str]:
    if not isinstance(entries, list):
        return []
    suggestions = [
        entry.strip() for entry in entries if isinstance(entry, str) and entry.strip()
    ]
    return suggestions[:4]


def _plan_context(plan: PlanResponse) -> str:
    tasks_by_date: dict[date, list[str]] = defaultdict(list)
    for task in plan.tasks:
        if task.status != "planned":
            continue
        tasks_by_date[task.planned_date].append(
            f"{task.subject_name}·{task.title}（{task.est_minutes} 分钟）"
        )
    lines: list[str] = []
    for day in plan.days:
        entries = tasks_by_date.get(day.date, [])
        joined = "；".join(entries) if entries else "（无任务）"
        lines.append(f"{day.date}（可用 {day.available_minutes} 分钟）：{joined}")
    return "\n".join(lines)


async def generate_ai_week_plan(
    session: AsyncSession,
    start_date: date,
    settings: Settings | None = None,
) -> AiWeekPlanResponse:
    settings = settings or get_settings()
    week_start = start_date - timedelta(days=start_date.weekday())
    week_end = week_start + timedelta(days=6)
    request = PlanGenerationRequest(start_date=week_start, end_date=week_end)
    plan = await preview_plan(session, request)
    total_available = sum(day.available_minutes for day in plan.days)
    if total_available <= 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"下周（{week_start} ~ {week_end}）没有任何可用学习时间，"
                "请先在「规划配置」中设置阶段、每日可用时长和任务模板"
            ),
        )
    insights = await get_problem_insights(session, week_start)
    weak_lines = "\n".join(
        f"- {point.knowledge_point_name}：{point.problem_count} 题，"
        f"遗忘 {point.forgot_reviews}/{point.total_reviews}，弱点分 {point.weakness_score}"
        for point in insights.knowledge_points[:MAX_WEAK_POINTS]
    )
    user_text = (
        f"下周（{week_start} ~ {week_end}）已排定计划：\n{_plan_context(plan)}\n\n"
        f"薄弱知识点（按弱点分降序，可能为空）：\n{weak_lines or '（暂无数据）'}\n\n"
        "请输出 JSON。"
    )
    raw = await ai_client.complete_chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
        settings,
        reasoning_effort=settings.ai_planning_reasoning_effort or None,
    )
    data = _parse_advice_json(raw)
    plan = await persist_plan(session, request)
    summary = data.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        summary = "已生成下周计划，按每日任务推进即可。"
    daily_focus = _normalize_daily_focus(data.get("daily_focus"), week_start)
    review_suggestions = _normalize_suggestions(data.get("review_suggestions"))

    stored = await session.scalar(
        select(AiWeekPlan).where(AiWeekPlan.week_start == week_start)
    )
    if stored is None:
        stored = AiWeekPlan(id=uuid4(), week_start=week_start, summary="", model="")
        session.add(stored)
    stored.summary = summary.strip()
    stored.daily_focus = [
        {"date": entry.date.isoformat(), "focus": entry.focus} for entry in daily_focus
    ]
    stored.review_suggestions = review_suggestions
    stored.model = settings.ai_model
    await session.commit()
    await session.refresh(stored)
    return AiWeekPlanResponse(plan=plan, advice=_advice_read(stored))


def _advice_read(stored: AiWeekPlan) -> AiWeekAdvice:
    return AiWeekAdvice(
        week_start=stored.week_start,
        summary=stored.summary,
        daily_focus=[
            AiDailyFocus(
                date=date.fromisoformat(entry["date"]),
                focus=entry["focus"],
            )
            for entry in stored.daily_focus
        ],
        review_suggestions=stored.review_suggestions,
        model=stored.model,
        created_at=stored.created_at,
    )


async def get_ai_week_advice(
    session: AsyncSession, week_start: date
) -> AiWeekAdvice | None:
    normalized = week_start - timedelta(days=week_start.weekday())
    stored = await session.scalar(
        select(AiWeekPlan).where(AiWeekPlan.week_start == normalized)
    )
    return _advice_read(stored) if stored is not None else None
