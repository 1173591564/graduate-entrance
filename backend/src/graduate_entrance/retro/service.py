from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.ai import client as ai_client
from graduate_entrance.core.config import Settings, get_settings
from graduate_entrance.models.retro import RetroMessage
from graduate_entrance.problems.insights import get_problem_insights
from graduate_entrance.profile.service import get_study_profile
from graduate_entrance.scheduling.ai_week import generate_ai_week_plan
from graduate_entrance.scheduling.service import get_weekly_stats
from graduate_entrance.schemas.retro import (
    RetroChatResponse,
    RetroConfirmResponse,
    RetroContext,
    RetroMessageRead,
    RetroSessionResponse,
    RetroSubjectSnapshot,
)

MAX_WEAK_POINTS = 6
MAX_HISTORY_MESSAGES = 20

SYSTEM_PROMPT = (
    "你是一名 11408 考研备考教练，正在和考生做每周复盘对话。"
    "你会拿到本周执行数据、各科掌握度画像和薄弱知识点。"
    "对话要求：直接、具体、口语化；先肯定做得好的地方，再指出问题和下周的取舍建议；"
    "回答控制在 200 字以内；如果考生表达了下周的时间变化或偏好，记住并在建议中体现；"
    "当考生确认方向后，提醒他点击「生成下周计划」落库。"
)


def normalize_week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


async def _build_context(session: AsyncSession, week_start: date) -> RetroContext:
    week_end = week_start + timedelta(days=6)
    stats = await get_weekly_stats(session, week_start, week_end)
    week = stats.weeks[0] if stats.weeks else None
    profile = await get_study_profile(session, week_end)
    insights = await get_problem_insights(session, week_end)
    weak_points = [
        f"{point.knowledge_point_name}（{point.problem_count} 题，"
        f"遗忘 {point.forgot_reviews}/{point.total_reviews}）"
        for point in insights.knowledge_points[:MAX_WEAK_POINTS]
    ]
    return RetroContext(
        week_start=week_start,
        week_end=week_end,
        planned_minutes=week.planned_minutes if week else 0,
        completed_minutes=week.completed_minutes if week else 0,
        total_tasks=week.total_tasks if week else 0,
        completed_tasks=week.completed_tasks if week else 0,
        execution_rate=week.execution_rate if week else 0.0,
        days_to_exam=profile.days_to_exam,
        subjects=[
            RetroSubjectSnapshot(
                subject_name=subject.subject_name,
                mastery=subject.mastery,
                coverage=subject.coverage,
                target_score=subject.target_score,
                estimated_score=subject.estimated_score,
            )
            for subject in profile.subjects
        ],
        weak_points=weak_points,
    )


def _context_text(context: RetroContext) -> str:
    subject_lines = "\n".join(
        f"- {subject.subject_name}：掌握度 {subject.mastery}%，"
        f"覆盖 {round(subject.coverage * 100)}%"
        + (
            f"，预估 {subject.estimated_score}/目标 {subject.target_score}"
            if subject.target_score is not None
            else "（未设目标分）"
        )
        for subject in context.subjects
    )
    weak_lines = "\n".join(f"- {point}" for point in context.weak_points) or "（暂无）"
    return (
        f"本周（{context.week_start} ~ {context.week_end}）执行数据：\n"
        f"- 任务完成 {context.completed_tasks}/{context.total_tasks}，"
        f"执行率 {round(context.execution_rate * 100)}%\n"
        f"- 已学 {context.completed_minutes} 分钟 / 计划 {context.planned_minutes} 分钟\n"
        f"- 距考试还有 {context.days_to_exam} 天\n\n"
        f"各科画像：\n{subject_lines}\n\n"
        f"薄弱知识点：\n{weak_lines}"
    )


async def _load_messages(session: AsyncSession, week_start: date) -> list[RetroMessage]:
    return list(
        await session.scalars(
            select(RetroMessage)
            .where(RetroMessage.week_start == week_start)
            .order_by(RetroMessage.created_at)
        )
    )


def _message_reads(messages: list[RetroMessage]) -> list[RetroMessageRead]:
    return [
        RetroMessageRead(
            id=message.id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
        )
        for message in messages
    ]


async def get_retro_session(session: AsyncSession, as_of: date) -> RetroSessionResponse:
    week_start = normalize_week_start(as_of)
    context = await _build_context(session, week_start)
    messages = await _load_messages(session, week_start)
    return RetroSessionResponse(context=context, messages=_message_reads(messages))


async def send_retro_message(
    session: AsyncSession,
    as_of: date,
    content: str,
    settings: Settings | None = None,
) -> RetroChatResponse:
    settings = settings or get_settings()
    week_start = normalize_week_start(as_of)
    context = await _build_context(session, week_start)
    history = await _load_messages(session, week_start)

    user_message = RetroMessage(week_start=week_start, role="user", content=content.strip())
    session.add(user_message)
    await session.flush()

    chat_messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _context_text(context)},
        {"role": "assistant", "content": "收到，我已经了解你本周的数据，开始复盘吧。"},
    ]
    for message in history[-MAX_HISTORY_MESSAGES:]:
        chat_messages.append({"role": message.role, "content": message.content})
    chat_messages.append({"role": "user", "content": content.strip()})

    reply = await ai_client.complete_chat(chat_messages, settings)
    assistant_message = RetroMessage(
        week_start=week_start, role="assistant", content=reply.strip()
    )
    session.add(assistant_message)
    await session.commit()

    messages = await _load_messages(session, week_start)
    return RetroChatResponse(messages=_message_reads(messages))


async def confirm_next_week_plan(
    session: AsyncSession,
    as_of: date,
    settings: Settings | None = None,
) -> RetroConfirmResponse:
    week_start = normalize_week_start(as_of)
    next_week = week_start + timedelta(weeks=1)
    plan = await generate_ai_week_plan(session, next_week, settings)
    return RetroConfirmResponse(plan=plan)
