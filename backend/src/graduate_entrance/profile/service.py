from collections import defaultdict
from datetime import date
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from graduate_entrance.core.config import Settings, get_settings
from graduate_entrance.mastery.service import GRADE_SCORES, knowledge_point_mastery
from graduate_entrance.models.problems import Problem, ReviewLog
from graduate_entrance.models.profile import SubjectGoal
from graduate_entrance.models.scheduling import ScheduledTask
from graduate_entrance.models.syllabus import Chapter, KnowledgePoint, Subject, SyllabusModule
from graduate_entrance.schemas.profile import (
    GoalsResponse,
    StudyProfileResponse,
    SubjectGoalInput,
    SubjectGoalRead,
    SubjectMastery,
    WeakKnowledgePoint,
)

WEAK_POINT_LIMIT = 5
WEAK_MASTERY_THRESHOLD = 60.0


async def list_goals(session: AsyncSession) -> GoalsResponse:
    subjects = (await session.scalars(select(Subject).order_by(Subject.order))).all()
    goals = {goal.subject_id: goal for goal in (await session.scalars(select(SubjectGoal))).all()}
    return GoalsResponse(
        goals=[
            SubjectGoalRead(
                subject_id=subject.id,
                subject_name=subject.name,
                target_score=goal.target_score,
                full_score=goal.full_score,
                note=goal.note,
                updated_at=goal.updated_at,
            )
            for subject in subjects
            if (goal := goals.get(subject.id)) is not None
        ]
    )


async def upsert_goals(session: AsyncSession, inputs: list[SubjectGoalInput]) -> GoalsResponse:
    subject_ids = {
        subject_id for subject_id in (await session.scalars(select(Subject.id))).all()
    }
    for entry in inputs:
        if entry.subject_id not in subject_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"subject {entry.subject_id} not found",
            )
        goal = await session.get(SubjectGoal, entry.subject_id)
        if goal is None:
            goal = SubjectGoal(
                subject_id=entry.subject_id,
                target_score=entry.target_score,
                full_score=entry.full_score,
                note=entry.note,
            )
            session.add(goal)
        else:
            goal.target_score = entry.target_score
            goal.full_score = entry.full_score
            goal.note = entry.note
    await session.commit()
    return await list_goals(session)


async def get_study_profile(
    session: AsyncSession,
    as_of: date,
    settings: Settings | None = None,
) -> StudyProfileResponse:
    settings = settings or get_settings()
    subjects = (await session.scalars(select(Subject).order_by(Subject.order))).all()
    goals = {goal.subject_id: goal for goal in (await session.scalars(select(SubjectGoal))).all()}

    kp_rows = (
        await session.execute(
            select(KnowledgePoint.id, KnowledgePoint.name, SyllabusModule.subject_id)
            .join(Chapter, KnowledgePoint.chapter_id == Chapter.id)
            .join(SyllabusModule, Chapter.module_id == SyllabusModule.id)
        )
    ).all()
    subject_kps: dict[UUID, list[tuple[UUID, str]]] = defaultdict(list)
    for kp_id, kp_name, subject_id in kp_rows:
        subject_kps[subject_id].append((kp_id, kp_name))

    studied_rows = (
        await session.execute(
            select(ScheduledTask.knowledge_point_id)
            .where(ScheduledTask.status == "completed")
            .where(ScheduledTask.knowledge_point_id.is_not(None))
            .distinct()
        )
    ).all()
    studied_kp_ids = {row[0] for row in studied_rows}

    minute_rows = (
        await session.execute(
            select(
                ScheduledTask.subject_id,
                func.coalesce(func.sum(ScheduledTask.actual_minutes), 0),
            )
            .where(ScheduledTask.status == "completed")
            .group_by(ScheduledTask.subject_id)
        )
    ).all()
    subject_minutes = {row[0]: int(row[1]) for row in minute_rows}

    problems = (
        (await session.scalars(select(Problem).options(selectinload(Problem.kp_links))))
        .unique()
        .all()
    )
    logs = (await session.scalars(select(ReviewLog))).all()
    problem_kp_ids: dict[UUID, list[UUID]] = {}
    kp_problem_count: dict[UUID, int] = defaultdict(int)
    kp_weighted_errors: dict[UUID, float] = defaultdict(float)
    subject_problem_count: dict[UUID, int] = defaultdict(int)
    subject_wrong_count: dict[UUID, int] = defaultdict(int)
    for problem in problems:
        if problem.subject_id is not None:
            subject_problem_count[problem.subject_id] += 1
            if problem.kind == "wrong":
                subject_wrong_count[problem.subject_id] += 1
        problem_kp_ids[problem.id] = [link.knowledge_point_id for link in problem.kp_links]
        for link in problem.kp_links:
            kp_problem_count[link.knowledge_point_id] += 1
            if problem.kind in ("wrong", "hard"):
                kp_weighted_errors[link.knowledge_point_id] += link.weight

    kp_review_scores: dict[UUID, list[float]] = defaultdict(list)
    kp_forgot: dict[UUID, int] = defaultdict(int)
    for log in logs:
        for kp_id in problem_kp_ids.get(log.problem_id, []):
            kp_review_scores[kp_id].append(GRADE_SCORES.get(log.grade, 0.0))
            if log.grade == "forgot":
                kp_forgot[kp_id] += 1

    subject_results: list[SubjectMastery] = []
    for subject in subjects:
        kps = subject_kps.get(subject.id, [])
        masteries: list[tuple[UUID, str, float]] = []
        studied_count = 0
        for kp_id, kp_name in kps:
            studied = kp_id in studied_kp_ids
            if studied:
                studied_count += 1
            masteries.append(
                (
                    kp_id,
                    kp_name,
                    knowledge_point_mastery(
                        studied,
                        kp_review_scores.get(kp_id, []),
                        kp_weighted_errors.get(kp_id, 0.0),
                    ),
                )
            )
        total = len(kps)
        subject_mastery = (
            round(sum(m for _, _, m in masteries) / total, 1) if total else 0.0
        )
        coverage = round(studied_count / total, 3) if total else 0.0
        goal = goals.get(subject.id)
        estimated_score = (
            round(goal.full_score * subject_mastery / 100, 1) if goal else None
        )
        weak_points = [
            WeakKnowledgePoint(
                knowledge_point_id=kp_id,
                knowledge_point_name=kp_name,
                mastery=mastery,
                problem_count=kp_problem_count.get(kp_id, 0),
                forgot_reviews=kp_forgot.get(kp_id, 0),
            )
            for kp_id, kp_name, mastery in sorted(masteries, key=lambda item: item[2])
            if mastery < WEAK_MASTERY_THRESHOLD
        ][:WEAK_POINT_LIMIT]
        subject_results.append(
            SubjectMastery(
                subject_id=subject.id,
                subject_name=subject.name,
                target_score=goal.target_score if goal else None,
                full_score=goal.full_score if goal else None,
                knowledge_point_total=total,
                studied_points=studied_count,
                coverage=coverage,
                mastery=subject_mastery,
                estimated_score=estimated_score,
                studied_minutes=subject_minutes.get(subject.id, 0),
                problem_count=subject_problem_count.get(subject.id, 0),
                wrong_count=subject_wrong_count.get(subject.id, 0),
                weak_points=weak_points,
            )
        )

    totals = [entry for entry in subject_results if entry.knowledge_point_total > 0]
    overall_mastery = (
        round(sum(entry.mastery for entry in totals) / len(totals), 1) if totals else 0.0
    )
    overall_coverage = (
        round(
            sum(entry.studied_points for entry in totals)
            / sum(entry.knowledge_point_total for entry in totals),
            3,
        )
        if totals
        else 0.0
    )
    return StudyProfileResponse(
        as_of=as_of,
        exam_date=settings.exam_date,
        days_to_exam=max(0, (settings.exam_date - as_of).days),
        overall_mastery=overall_mastery,
        overall_coverage=overall_coverage,
        subjects=subject_results,
    )
