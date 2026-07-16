import math
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from graduate_entrance.models.problems import Problem, ProblemKnowledgePoint, Solution
from graduate_entrance.models.syllabus import KnowledgePoint, Subject
from graduate_entrance.schemas.problems import (
    ProblemConfirmRequest,
    ProblemKind,
    ProblemKnowledgePointRead,
    ProblemListResponse,
    ProblemPendingResponse,
    ProblemRead,
    SolutionCreateRequest,
    SolutionRead,
)

MAX_IMAGES_PER_PROBLEM = 6


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
    return (await _read_problems(session, [loaded]))[0]


async def reopen_problem(session: AsyncSession, problem_id: UUID) -> ProblemRead:
    problem = await _load_problem(session, problem_id)
    problem.status = "draft"
    problem.confirmed_at = None
    await session.commit()
    loaded = await _load_problem(session, problem.id)
    return (await _read_problems(session, [loaded]))[0]


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
