from collections import defaultdict
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from graduate_entrance.models.problems import Problem, ReviewLog
from graduate_entrance.models.syllabus import KnowledgePoint, Subject
from graduate_entrance.schemas.problems import (
    CauseInsight,
    KnowledgePointInsight,
    ProblemInsightsResponse,
    SubjectInsight,
    WeeklyTrendPoint,
)

TREND_WEEKS = 8


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


async def get_problem_insights(
    session: AsyncSession, as_of: date
) -> ProblemInsightsResponse:
    problems = (
        (
            await session.scalars(
                select(Problem).options(selectinload(Problem.kp_links))
            )
        )
        .unique()
        .all()
    )
    logs = (await session.scalars(select(ReviewLog))).all()

    kp_problem_count: dict[UUID, int] = defaultdict(int)
    kp_weighted_errors: dict[UUID, float] = defaultdict(float)
    kp_problem_ids: dict[UUID, set[UUID]] = defaultdict(set)
    cause_counts: dict[str, int] = defaultdict(int)
    subject_problem_count: dict[UUID | None, int] = defaultdict(int)
    subject_wrong_count: dict[UUID | None, int] = defaultdict(int)

    for problem in problems:
        subject_problem_count[problem.subject_id] += 1
        if problem.kind == "wrong":
            subject_wrong_count[problem.subject_id] += 1
        if problem.status == "confirmed" and problem.cause:
            cause_counts[problem.cause] += 1
        for link in problem.kp_links:
            kp_problem_count[link.knowledge_point_id] += 1
            kp_problem_ids[link.knowledge_point_id].add(problem.id)
            if problem.kind in ("wrong", "hard"):
                kp_weighted_errors[link.knowledge_point_id] += link.weight

    kp_forgot: dict[UUID, int] = defaultdict(int)
    kp_reviews: dict[UUID, int] = defaultdict(int)
    problem_kp_ids: dict[UUID, list[UUID]] = {
        problem.id: [link.knowledge_point_id for link in problem.kp_links]
        for problem in problems
    }
    for log in logs:
        for kp_id in problem_kp_ids.get(log.problem_id, []):
            kp_reviews[kp_id] += 1
            if log.grade == "forgot":
                kp_forgot[kp_id] += 1

    point_names = {
        point.id: point.name
        for point in (
            await session.scalars(
                select(KnowledgePoint).where(KnowledgePoint.id.in_(kp_problem_count))
            )
        ).all()
    }
    subject_names = {
        subject.id: subject.name
        for subject in (
            await session.scalars(
                select(Subject).where(
                    Subject.id.in_([sid for sid in subject_problem_count if sid is not None])
                )
            )
        ).all()
    }

    knowledge_points = sorted(
        (
            KnowledgePointInsight(
                knowledge_point_id=kp_id,
                knowledge_point_name=point_names.get(kp_id, ""),
                problem_count=count,
                weighted_errors=round(kp_weighted_errors[kp_id], 3),
                forgot_reviews=kp_forgot[kp_id],
                total_reviews=kp_reviews[kp_id],
                weakness_score=round(
                    kp_weighted_errors[kp_id]
                    * (1 + (kp_forgot[kp_id] / kp_reviews[kp_id] if kp_reviews[kp_id] else 0)),
                    3,
                ),
            )
            for kp_id, count in kp_problem_count.items()
        ),
        key=lambda item: (-item.weakness_score, item.knowledge_point_name),
    )

    causes = sorted(
        (CauseInsight(cause=cause, count=count) for cause, count in cause_counts.items()),
        key=lambda item: (-item.count, item.cause),
    )

    subjects = sorted(
        (
            SubjectInsight(
                subject_id=subject_id,
                subject_name=(
                    subject_names.get(subject_id, "未分类") if subject_id else "未分类"
                ),
                problem_count=count,
                wrong_count=subject_wrong_count[subject_id],
            )
            for subject_id, count in subject_problem_count.items()
        ),
        key=lambda item: (-item.problem_count, item.subject_name),
    )

    first_week = _week_start(as_of) - timedelta(weeks=TREND_WEEKS - 1)
    trend: dict[date, WeeklyTrendPoint] = {
        first_week + timedelta(weeks=offset): WeeklyTrendPoint(
            week_start=first_week + timedelta(weeks=offset),
            new_problems=0,
            reviews=0,
            forgot=0,
            vague=0,
            mastered=0,
        )
        for offset in range(TREND_WEEKS)
    }
    for problem in problems:
        week = _week_start(problem.created_at.date())
        if week in trend:
            trend[week].new_problems += 1
    for log in logs:
        week = _week_start(log.reviewed_on)
        if week not in trend:
            continue
        point = trend[week]
        point.reviews += 1
        if log.grade == "forgot":
            point.forgot += 1
        elif log.grade == "vague":
            point.vague += 1
        else:
            point.mastered += 1

    return ProblemInsightsResponse(
        as_of=as_of,
        total_problems=len(problems),
        confirmed_problems=sum(1 for p in problems if p.status == "confirmed"),
        knowledge_points=knowledge_points,
        causes=causes,
        subjects=subjects,
        weekly_trend=[trend[week] for week in sorted(trend)],
    )
