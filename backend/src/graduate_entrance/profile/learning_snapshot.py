"""跨模块学习画像快照：聚合各闭环信号，喂给周计划与周复盘的 prompt。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.mastery.service import list_mastery_gaps
from graduate_entrance.models.chat import ChatTopicTag
from graduate_entrance.models.essay import EssayMaterial
from graduate_entrance.models.problems import Problem
from graduate_entrance.problems.insights import get_problem_insights
from graduate_entrance.recitation.service import recitation_stats
from graduate_entrance.vocab.service import vocab_stats

MAX_GAPS = 5
MAX_WEAK_POINTS = 5
MAX_CHAT_TOPICS = 5
CHAT_TOPIC_DAYS = 14


@dataclass
class LearningSnapshot:
    as_of: date
    gap_lines: list[str] = field(default_factory=list)
    weak_lines: list[str] = field(default_factory=list)
    vocab_due: int = 0
    vocab_learned: int = 0
    vocab_total: int = 0
    recitation_never: int = 0
    recitation_total: int = 0
    review_due: int = 0
    essay_due: int = 0
    chat_topic_lines: list[str] = field(default_factory=list)


async def build_learning_snapshot(
    session: AsyncSession, as_of: date
) -> LearningSnapshot:
    snapshot = LearningSnapshot(as_of=as_of)

    gaps = await list_mastery_gaps(session, limit=MAX_GAPS)
    snapshot.gap_lines = [
        f"{item.subject_name}·{item.knowledge_point_name}："
        f"掌握 {item.mastery} / 目标 {item.target}（缺口 {item.gap}）"
        for item in gaps.items
    ]

    insights = await get_problem_insights(session, as_of)
    snapshot.weak_lines = [
        f"{point.knowledge_point_name}：{point.problem_count} 题，"
        f"遗忘 {point.forgot_reviews}/{point.total_reviews}，弱点分 {point.weakness_score}"
        for point in insights.knowledge_points[:MAX_WEAK_POINTS]
    ]

    vocab = await vocab_stats(session, as_of)
    snapshot.vocab_due = vocab.due_count
    snapshot.vocab_learned = vocab.learned_count
    snapshot.vocab_total = vocab.total_count

    recitation = await recitation_stats(session, None, as_of)
    snapshot.recitation_never = recitation.never_recited
    snapshot.recitation_total = recitation.total_count

    snapshot.review_due = (
        await session.scalar(
            select(func.count())
            .select_from(Problem)
            .where(
                Problem.due_date.is_not(None),
                Problem.due_date <= as_of,
                Problem.status == "confirmed",
            )
        )
        or 0
    )

    snapshot.essay_due = (
        await session.scalar(
            select(func.count())
            .select_from(EssayMaterial)
            .where(EssayMaterial.due_date <= as_of)
        )
        or 0
    )

    since = datetime.combine(
        as_of - timedelta(days=CHAT_TOPIC_DAYS), time.min, tzinfo=UTC
    )
    topic_rows = (
        await session.execute(
            select(
                ChatTopicTag.subject,
                ChatTopicTag.topic,
                func.count().label("asked"),
            )
            .where(ChatTopicTag.created_at >= since)
            .group_by(ChatTopicTag.subject, ChatTopicTag.topic)
            .order_by(func.count().desc())
            .limit(MAX_CHAT_TOPICS)
        )
    ).all()
    snapshot.chat_topic_lines = [
        f"{subject}·{topic}：问了 {asked} 次" for subject, topic, asked in topic_rows
    ]

    return snapshot


def snapshot_text(snapshot: LearningSnapshot) -> str:
    gap_block = "\n".join(f"- {line}" for line in snapshot.gap_lines) or "（暂无）"
    weak_block = "\n".join(f"- {line}" for line in snapshot.weak_lines) or "（暂无）"
    vocab_line = (
        f"已学 {snapshot.vocab_learned}/{snapshot.vocab_total}，"
        f"到期待复习 {snapshot.vocab_due} 个"
        if snapshot.vocab_total
        else "（未导入词库）"
    )
    recitation_line = (
        f"共 {snapshot.recitation_total} 条，未背过 {snapshot.recitation_never} 条"
        if snapshot.recitation_total
        else "（暂无背诵条目）"
    )
    chat_block = (
        "\n".join(f"- {line}" for line in snapshot.chat_topic_lines) or "（暂无）"
    )
    return (
        f"学习画像快照（截至 {snapshot.as_of}）：\n"
        f"掌握度缺口 Top{MAX_GAPS}：\n{gap_block}\n\n"
        f"错题薄弱知识点：\n{weak_block}\n\n"
        f"单词：{vocab_line}\n"
        f"背诵：{recitation_line}\n"
        f"错题到期待复习：{snapshot.review_due} 道\n"
        f"作文素材到期待背：{snapshot.essay_due} 篇\n\n"
        f"近{CHAT_TOPIC_DAYS}天提问高频主题（学生反复问=可能薄弱）：\n{chat_block}"
    )
