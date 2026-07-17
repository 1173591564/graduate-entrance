"""Recompute and read persisted knowledge-point mastery.

The mastery value is derived from the same three signals the profile view uses
(studied tasks, review grades, wrong/hard problems) but is *persisted* so that
planning and retro can cheaply read the ``target - mastery`` gap instead of
recomputing the whole graph every time.

``target`` is back-derived, never hand-entered: the syllabus requirement level
says *how well* a point must be known, and the subject goal ratio
(target_score / full_score) scales that ambition up or down.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from graduate_entrance.models.mastery import KpMastery
from graduate_entrance.models.problems import Problem, ReviewLog
from graduate_entrance.models.profile import SubjectGoal
from graduate_entrance.models.scheduling import ScheduledTask
from graduate_entrance.models.syllabus import (
    Chapter,
    KnowledgePoint,
    Subject,
    SyllabusModule,
)
from graduate_entrance.schemas.mastery import MasteryGap, MasteryGapResponse

GRADE_SCORES = {"forgot": 0.0, "vague": 0.5, "mastered": 1.0}

# How well a point must be known, by syllabus requirement level (0..1).
REQUIREMENT_TARGET_BASE = {
    "awareness": 0.55,
    "understanding": 0.70,
    "application": 0.85,
    "mastery": 0.95,
}
DEFAULT_REQUIREMENT_BASE = 0.70
# Fallback goal ratio when a subject has no explicit goal yet.
DEFAULT_GOAL_RATIO = 0.80


def knowledge_point_mastery(
    studied: bool,
    review_scores: list[float],
    weighted_errors: float,
) -> float:
    """Blend the three signals into a 0..100 mastery estimate."""
    score = 0.5 if studied else 0.0
    if review_scores:
        grade_ratio = sum(review_scores) / len(review_scores)
        score += 0.5 * grade_ratio
        score -= 0.3 * min(weighted_errors, 2.0) / 2.0 * (1.0 - grade_ratio)
    elif weighted_errors > 0:
        score -= 0.3 * min(weighted_errors, 2.0) / 2.0
    elif studied:
        score += 0.25
    return round(max(0.0, min(1.0, score)) * 100, 1)


def derive_target(requirement_level: str, goal_ratio: float) -> float:
    """Back-derive a 0..100 mastery target for one knowledge point."""
    base = REQUIREMENT_TARGET_BASE.get(requirement_level, DEFAULT_REQUIREMENT_BASE)
    ratio = max(0.0, min(1.0, goal_ratio))
    return round(base * ratio * 100, 1)


async def recompute_kp_mastery(
    session: AsyncSession,
    kp_ids: set[UUID] | None = None,
) -> int:
    """Recompute mastery + target for knowledge points and persist it.

    When ``kp_ids`` is given only those points are rewritten (a targeted
    write-back after a single signal); otherwise every point is recomputed.
    Returns the number of knowledge points written. Idempotent: running it twice
    with the same underlying signals yields the same rows.
    """
    if kp_ids is not None and not kp_ids:
        return 0

    kp_query = (
        select(
            KnowledgePoint.id,
            KnowledgePoint.requirement_level,
            SyllabusModule.subject_id,
        )
        .join(Chapter, KnowledgePoint.chapter_id == Chapter.id)
        .join(SyllabusModule, Chapter.module_id == SyllabusModule.id)
    )
    if kp_ids is not None:
        kp_query = kp_query.where(KnowledgePoint.id.in_(kp_ids))
    kp_rows = (await session.execute(kp_query)).all()

    goals = {
        goal.subject_id: goal for goal in (await session.scalars(select(SubjectGoal))).all()
    }

    studied_kp_ids = {
        row[0]
        for row in (
            await session.execute(
                select(ScheduledTask.knowledge_point_id)
                .where(ScheduledTask.status == "completed")
                .where(ScheduledTask.knowledge_point_id.is_not(None))
                .distinct()
            )
        ).all()
    }

    problems = (
        (await session.scalars(select(Problem).options(selectinload(Problem.kp_links))))
        .unique()
        .all()
    )
    problem_kp_ids: dict[UUID, list[UUID]] = {}
    kp_weighted_errors: dict[UUID, float] = defaultdict(float)
    for problem in problems:
        problem_kp_ids[problem.id] = [link.knowledge_point_id for link in problem.kp_links]
        for link in problem.kp_links:
            if problem.kind in ("wrong", "hard"):
                kp_weighted_errors[link.knowledge_point_id] += link.weight

    kp_review_scores: dict[UUID, list[float]] = defaultdict(list)
    for log in (await session.scalars(select(ReviewLog))).all():
        for kp_id in problem_kp_ids.get(log.problem_id, []):
            kp_review_scores[kp_id].append(GRADE_SCORES.get(log.grade, 0.0))

    existing = {
        row.knowledge_point_id: row
        for row in (await session.scalars(select(KpMastery))).all()
    }
    now = datetime.now(UTC)
    written = 0
    for kp_id, requirement_level, subject_id in kp_rows:
        studied = kp_id in studied_kp_ids
        review_scores = kp_review_scores.get(kp_id, [])
        weighted_errors = kp_weighted_errors.get(kp_id, 0.0)
        mastery = knowledge_point_mastery(studied, review_scores, weighted_errors)
        goal = goals.get(subject_id)
        goal_ratio = (
            goal.target_score / goal.full_score
            if goal and goal.full_score
            else DEFAULT_GOAL_RATIO
        )
        target = derive_target(requirement_level, goal_ratio)
        has_signal = studied or bool(review_scores) or weighted_errors > 0

        row = existing.get(kp_id)
        if row is None:
            row = KpMastery(knowledge_point_id=kp_id, subject_id=subject_id)
            session.add(row)
        row.subject_id = subject_id
        row.mastery = Decimal(str(mastery))
        row.target = Decimal(str(target))
        row.studied = studied
        if has_signal:
            row.last_signal_at = now
        written += 1

    await session.commit()
    return written


async def list_mastery_gaps(
    session: AsyncSession,
    limit: int = 20,
    recompute: bool = True,
) -> MasteryGapResponse:
    """Return knowledge points sorted by the largest ``target - mastery`` gap.

    This is what planning and retro consume: the biggest gaps are the most
    valuable things to schedule next.
    """
    if recompute:
        await recompute_kp_mastery(session)

    rows = (
        await session.execute(
            select(
                KpMastery.knowledge_point_id,
                KnowledgePoint.name,
                KpMastery.subject_id,
                Subject.name,
                KpMastery.mastery,
                KpMastery.target,
                KpMastery.studied,
            )
            .join(KnowledgePoint, KnowledgePoint.id == KpMastery.knowledge_point_id)
            .join(Subject, Subject.id == KpMastery.subject_id)
        )
    ).all()

    items = [
        MasteryGap(
            knowledge_point_id=kp_id,
            knowledge_point_name=kp_name,
            subject_id=subject_id,
            subject_name=subject_name,
            mastery=float(mastery),
            target=float(target),
            gap=round(float(target) - float(mastery), 1),
            studied=studied,
        )
        for kp_id, kp_name, subject_id, subject_name, mastery, target, studied in rows
    ]
    items.sort(key=lambda item: item.gap, reverse=True)
    positive = [item for item in items if item.gap > 0]
    return MasteryGapResponse(
        generated_at=datetime.now(UTC),
        knowledge_point_total=len(items),
        gap_count=len(positive),
        items=positive[:limit],
    )
