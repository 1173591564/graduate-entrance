import math
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from graduate_entrance.mastery.service import recompute_kp_mastery
from graduate_entrance.models.problems import (
    Problem,
    ProblemKnowledgePoint,
    ReviewLog,
    Solution,
)
from graduate_entrance.models.syllabus import KnowledgePoint, Subject
from graduate_entrance.schemas.problems import (
    ProblemConfirmRequest,
    ProblemKind,
    ProblemKnowledgePointRead,
    ProblemListResponse,
    ProblemPendingResponse,
    ProblemRead,
    ReviewDueResponse,
    ReviewGrade,
    ReviewResult,
    SolutionCreateRequest,
    SolutionRead,
)

MAX_IMAGES_PER_PROBLEM = 6
MIN_EASE_FACTOR = 1.3
GRADE_QUALITY: dict[ReviewGrade, int] = {"forgot": 2, "vague": 3, "mastered": 5}


def _apply_sm2(
    ef: float, interval_days: int, reps: int, grade: ReviewGrade
) -> tuple[float, int, int]:
    """Return updated (ef, interval_days, reps) for an SM-2 review response."""
    quality = GRADE_QUALITY[grade]
    next_ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    next_ef = max(MIN_EASE_FACTOR, next_ef)
    if quality < 3:
        return next_ef, 1, 0
    if reps <= 0:
        next_interval = 1
    elif reps == 1:
        next_interval = 6
    else:
        next_interval = max(1, round(interval_days * next_ef))
    return next_ef, next_interval, reps + 1


async def _subject_names(session: AsyncSession, subject_ids: set[UUID]) -> dict[UUID, str]:
    if not subject_ids:
        return {}
    subjects = (
        await session.scalars(select(Subject).where(Subject.id.in_(subject_ids)))
    ).all()
    return {subject.id: subject.name for subject in subjects}


async def _knowledge_point_names(
    session: AsyncSession, point_ids: set[UUID]
) -> dict[UUID, str]:
    if not point_ids:
        return {}
    points = (
        await session.scalars(select(KnowledgePoint).where(KnowledgePoint.id.in_(point_ids)))
    ).all()
    return {point.id: point.name for point in points}


def _to_read(
    problem: Problem,
    subject_names: dict[UUID, str],
    point_names: dict[UUID, str],
) -> ProblemRead:
    links = sorted(
        problem.kp_links,
        key=lambda link: (link.role != "primary", -link.weight),
    )
    return ProblemRead(
        id=problem.id,
        subject_id=problem.subject_id,
        subject_name=(
            subject_names.get(problem.subject_id) if problem.subject_id is not None else None
        ),
        content_md=problem.content_md,
        images=problem.images,
        source_ref=problem.source_ref,
        kind=problem.kind,
        my_answer_md=problem.my_answer_md,
        cause=problem.cause,
        note=problem.note,
        status=problem.status,
        due_date=problem.due_date,
        reps=problem.reps,
        confirmed_at=problem.confirmed_at,
        ai_score=problem.ai_score,
        ai_feedback_md=problem.ai_feedback_md,
        ai_graded_at=problem.ai_graded_at,
        created_at=problem.created_at,
        knowledge_points=[
            ProblemKnowledgePointRead(
                knowledge_point_id=link.knowledge_point_id,
                knowledge_point_name=point_names.get(link.knowledge_point_id, ""),
                role=link.role,
                weight=link.weight,
            )
            for link in links
        ],
        solutions=[
            SolutionRead(
                id=solution.id,
                content_md=solution.content_md,
                method_tag=solution.method_tag,
                source=solution.source,
                verified=solution.verified,
                created_at=solution.created_at,
            )
            for solution in problem.solutions
        ],
    )


async def _read_problems(
    session: AsyncSession, problems: list[Problem]
) -> list[ProblemRead]:
    subject_ids = {p.subject_id for p in problems if p.subject_id is not None}
    point_ids = {link.knowledge_point_id for p in problems for link in p.kp_links}
    subject_names = await _subject_names(session, subject_ids)
    point_names = await _knowledge_point_names(session, point_ids)
    return [_to_read(problem, subject_names, point_names) for problem in problems]


async def _load_problem(session: AsyncSession, problem_id: UUID) -> Problem:
    problem = await session.scalar(
        select(Problem)
        .where(Problem.id == problem_id)
        .options(selectinload(Problem.kp_links), selectinload(Problem.solutions))
        .execution_options(populate_existing=True)
    )
    if problem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="problem not found",
        )
    return problem


async def create_problem(
    session: AsyncSession,
    subject_id: UUID | None,
    kind: ProblemKind,
    content_md: str,
    source_ref: str,
    my_answer_md: str,
    note: str,
    image_names: list[str],
) -> ProblemRead:
    if not content_md.strip() and not image_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="problem requires content_md or at least one image",
        )
    if subject_id is not None:
        subject = await session.scalar(select(Subject).where(Subject.id == subject_id))
        if subject is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="subject not found",
            )
    problem = Problem(
        id=uuid4(),
        subject_id=subject_id,
        content_md=content_md,
        images=image_names,
        source_ref=source_ref,
        kind=kind,
        my_answer_md=my_answer_md,
        note=note,
        status="draft",
        due_date=date.today(),
    )
    session.add(problem)
    await session.commit()
    loaded = await _load_problem(session, problem.id)
    return (await _read_problems(session, [loaded]))[0]


async def list_pending(session: AsyncSession) -> ProblemPendingResponse:
    problems = list(
        (
            await session.scalars(
                select(Problem)
                .where(Problem.status == "draft")
                .options(selectinload(Problem.kp_links), selectinload(Problem.solutions))
                .order_by(Problem.created_at)
            )
        ).all()
    )
    total = await session.scalar(
        select(func.count()).select_from(Problem).where(Problem.status == "draft")
    )
    return ProblemPendingResponse(
        total=total or 0,
        problems=await _read_problems(session, problems),
    )


async def list_problems(
    session: AsyncSession,
    knowledge_point_id: UUID | None,
    subject_id: UUID | None,
    limit: int,
) -> ProblemListResponse:
    query = (
        select(Problem)
        .options(selectinload(Problem.kp_links), selectinload(Problem.solutions))
        .order_by(Problem.created_at.desc())
    )
    if subject_id is not None:
        query = query.where(Problem.subject_id == subject_id)
    if knowledge_point_id is not None:
        query = query.join(
            ProblemKnowledgePoint,
            ProblemKnowledgePoint.problem_id == Problem.id,
        ).where(ProblemKnowledgePoint.knowledge_point_id == knowledge_point_id)
    problems = list((await session.scalars(query.limit(limit))).all())
    if knowledge_point_id is not None:

        def rank(problem: Problem) -> tuple[int, float]:
            for link in problem.kp_links:
                if link.knowledge_point_id == knowledge_point_id:
                    return (0 if link.role == "primary" else 1, -link.weight)
            return (2, 0.0)

        problems.sort(key=rank)
    return ProblemListResponse(
        total=len(problems),
        problems=await _read_problems(session, problems),
    )


async def get_problem(session: AsyncSession, problem_id: UUID) -> ProblemRead:
    problem = await _load_problem(session, problem_id)
    return (await _read_problems(session, [problem]))[0]


async def confirm_problem(
    session: AsyncSession,
    problem_id: UUID,
    payload: ProblemConfirmRequest,
) -> ProblemRead:
    problem = await _load_problem(session, problem_id)
    primary_count = sum(1 for link in payload.knowledge_points if link.role == "primary")
    if primary_count != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="exactly one primary knowledge point is required",
        )
    point_ids = [link.knowledge_point_id for link in payload.knowledge_points]
    if len(set(point_ids)) != len(point_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="duplicate knowledge point mapping",
        )
    total_weight = sum(link.weight for link in payload.knowledge_points)
    if not math.isclose(total_weight, 1.0, abs_tol=0.001):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="knowledge point weights must sum to 1",
        )
    known = await _knowledge_point_names(session, set(point_ids))
    missing = [str(point_id) for point_id in point_ids if point_id not in known]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"knowledge points not found: {', '.join(missing)}",
        )
    problem.content_md = payload.content_md
    problem.kind = payload.kind
    problem.cause = payload.cause
    problem.my_answer_md = payload.my_answer_md
    problem.note = payload.note
    problem.source_ref = payload.source_ref
    problem.status = "confirmed"
    problem.confirmed_at = datetime.now(UTC)
    if problem.due_date is None:
        problem.due_date = date.today()
    problem.kp_links = [
        ProblemKnowledgePoint(
            problem_id=problem.id,
            knowledge_point_id=link.knowledge_point_id,
            role=link.role,
            weight=link.weight,
        )
        for link in payload.knowledge_points
    ]
    await session.commit()
    loaded = await _load_problem(session, problem.id)
    await recompute_kp_mastery(
        session, {link.knowledge_point_id for link in loaded.kp_links}
    )
    return (await _read_problems(session, [loaded]))[0]


async def reopen_problem(session: AsyncSession, problem_id: UUID) -> ProblemRead:
    problem = await _load_problem(session, problem_id)
    problem.status = "draft"
    problem.confirmed_at = None
    await session.commit()
    loaded = await _load_problem(session, problem.id)
    return (await _read_problems(session, [loaded]))[0]


async def list_due_reviews(
    session: AsyncSession,
    as_of: date,
    include_drafts: bool,
    limit: int,
) -> ReviewDueResponse:
    query = (
        select(Problem)
        .where(Problem.due_date.is_not(None), Problem.due_date <= as_of)
        .options(selectinload(Problem.kp_links), selectinload(Problem.solutions))
        .order_by(Problem.due_date, Problem.created_at)
    )
    if not include_drafts:
        query = query.where(Problem.status == "confirmed")
    problems = list((await session.scalars(query.limit(limit))).all())
    count_query = (
        select(func.count())
        .select_from(Problem)
        .where(Problem.due_date.is_not(None), Problem.due_date <= as_of)
    )
    if not include_drafts:
        count_query = count_query.where(Problem.status == "confirmed")
    total = await session.scalar(count_query)
    return ReviewDueResponse(
        total=total or 0,
        as_of=as_of,
        problems=await _read_problems(session, problems),
    )


async def review_problem(
    session: AsyncSession,
    problem_id: UUID,
    grade: ReviewGrade,
    as_of: date,
) -> ReviewResult:
    problem = await _load_problem(session, problem_id)
    next_ef, next_interval, next_reps = _apply_sm2(
        problem.ef, problem.interval_days, problem.reps, grade
    )
    problem.ef = next_ef
    problem.interval_days = next_interval
    problem.reps = next_reps
    problem.due_date = as_of + timedelta(days=next_interval)
    session.add(ReviewLog(id=uuid4(), problem_id=problem.id, grade=grade, reviewed_on=as_of))
    await session.commit()
    loaded = await _load_problem(session, problem.id)
    await recompute_kp_mastery(
        session, {link.knowledge_point_id for link in loaded.kp_links}
    )
    read = (await _read_problems(session, [loaded]))[0]
    return ReviewResult(
        problem=read,
        grade=grade,
        ef=loaded.ef,
        interval_days=loaded.interval_days,
        reps=loaded.reps,
        due_date=loaded.due_date or as_of,
    )


async def add_solution(
    session: AsyncSession,
    problem_id: UUID,
    payload: SolutionCreateRequest,
) -> ProblemRead:
    problem = await _load_problem(session, problem_id)
    session.add(
        Solution(
            id=uuid4(),
            problem_id=problem.id,
            content_md=payload.content_md,
            method_tag=payload.method_tag,
            source=payload.source,
            verified=payload.source != "gpt",
        )
    )
    await session.commit()
    loaded = await _load_problem(session, problem.id)
    return (await _read_problems(session, [loaded]))[0]
