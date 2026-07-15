from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from fractions import Fraction
from heapq import heappop, heappush
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from graduate_entrance.models.planning import (
    AvailabilityException,
    AvailabilityPeriod,
    Material,
    PlanPhase,
    TaskTemplate,
    TaskTemplatePhase,
)
from graduate_entrance.models.scheduling import ScheduledTask, TaskPoolItem
from graduate_entrance.models.syllabus import (
    Chapter,
    KnowledgeDependency,
    KnowledgePoint,
    Subject,
    SyllabusModule,
)
from graduate_entrance.schemas.scheduling import (
    CalendarDayRead,
    CalendarResponse,
    CalendarWeekRead,
    PlanDaySummary,
    PlanGenerationRequest,
    PlanResponse,
    PlanSubjectSummary,
    PlanTaskRead,
    TaskPoolGenerationResponse,
    TaskPoolItemRead,
    TaskPoolPage,
)


@dataclass(frozen=True)
class _PoolSpec:
    id: UUID
    phase_id: UUID
    subject_id: UUID
    knowledge_point_id: UUID
    task_template_id: UUID
    material_id: UUID | None
    title: str
    task_type: str
    est_minutes: int
    priority: int
    sort_key: tuple[int, int, int, int, int, int, str]


@dataclass(frozen=True)
class _Candidate:
    pool_item_id: UUID
    phase_id: UUID
    phase_name: str
    subject_id: UUID
    subject_name: str
    subject_order: int
    knowledge_point_id: UUID
    knowledge_point_name: str
    material_id: UUID | None
    material_name: str | None
    title: str
    task_type: str
    est_minutes: int
    priority: int


def _pool_item_id(phase_id: UUID, template_id: UUID, point_id: UUID) -> UUID:
    return uuid5(NAMESPACE_URL, f"task-pool:{phase_id}:{template_id}:{point_id}")


def _scheduled_task_id(pool_item_id: UUID) -> UUID:
    return uuid5(NAMESPACE_URL, f"scheduled-task:{pool_item_id}")


async def generate_task_pool(session: AsyncSession) -> TaskPoolGenerationResponse:
    templates = (
        await session.scalars(
            select(TaskTemplate)
            .where(TaskTemplate.active.is_(True))
            .options(selectinload(TaskTemplate.phase_links))
            .order_by(TaskTemplate.order, TaskTemplate.name, TaskTemplate.id)
        )
    ).all()
    phases = {
        phase.id: phase
        for phase in (
            await session.scalars(select(PlanPhase).order_by(PlanPhase.order, PlanPhase.id))
        ).all()
    }
    subject_orders = {
        subject.id: subject.order
        for subject in (
            await session.scalars(select(Subject).order_by(Subject.order, Subject.id))
        ).all()
    }
    point_rows = (
        await session.execute(
            select(KnowledgePoint, Chapter, SyllabusModule)
            .join(Chapter, KnowledgePoint.chapter_id == Chapter.id)
            .join(SyllabusModule, Chapter.module_id == SyllabusModule.id)
            .order_by(
                SyllabusModule.order,
                Chapter.order,
                KnowledgePoint.order,
                KnowledgePoint.id,
            )
        )
    ).tuples().all()
    points_by_subject: dict[
        UUID,
        list[tuple[KnowledgePoint, Chapter, SyllabusModule]],
    ] = defaultdict(list)
    for point, chapter, module in point_rows:
        points_by_subject[module.subject_id].append((point, chapter, module))

    specs: list[_PoolSpec] = []
    for template in templates:
        phase_ids = sorted(
            (link.phase_id for link in template.phase_links),
            key=lambda phase_id: (
                phases[phase_id].order,
                phases[phase_id].start_date,
                str(phase_id),
            ),
        )
        for phase_id in phase_ids:
            for point, chapter, module in points_by_subject[template.subject_id]:
                specs.append(
                    _PoolSpec(
                        id=_pool_item_id(phase_id, template.id, point.id),
                        phase_id=phase_id,
                        subject_id=template.subject_id,
                        knowledge_point_id=point.id,
                        task_template_id=template.id,
                        material_id=template.material_id,
                        title=f"{point.name} · {template.name}",
                        task_type=template.task_type,
                        est_minutes=template.default_est_minutes,
                        priority=0,
                        sort_key=(
                            phases[phase_id].order,
                            subject_orders[template.subject_id],
                            module.order,
                            chapter.order,
                            point.order,
                            template.order,
                            str(point.id),
                        ),
                    )
                )
    specs.sort(key=lambda spec: (*spec.sort_key, str(spec.id)))
    prioritized_specs: list[_PoolSpec] = []
    group_priority: dict[tuple[UUID, UUID], int] = defaultdict(int)
    for spec in specs:
        group = (spec.phase_id, spec.subject_id)
        prioritized_specs.append(
            _PoolSpec(
                id=spec.id,
                phase_id=spec.phase_id,
                subject_id=spec.subject_id,
                knowledge_point_id=spec.knowledge_point_id,
                task_template_id=spec.task_template_id,
                material_id=spec.material_id,
                title=spec.title,
                task_type=spec.task_type,
                est_minutes=spec.est_minutes,
                priority=group_priority[group],
                sort_key=spec.sort_key,
            )
        )
        group_priority[group] += 1
    specs = prioritized_specs

    existing = {
        (item.phase_id, item.task_template_id, item.knowledge_point_id): item
        for item in (await session.scalars(select(TaskPoolItem))).all()
    }
    created = 0
    updated = 0
    deleted = 0
    desired_keys = {
        (spec.phase_id, spec.task_template_id, spec.knowledge_point_id) for spec in specs
    }
    for key, stale_item in existing.items():
        if key not in desired_keys:
            await session.delete(stale_item)
            deleted += 1
    for spec in specs:
        key = (spec.phase_id, spec.task_template_id, spec.knowledge_point_id)
        item = existing.get(key)
        if item is None:
            session.add(
                TaskPoolItem(
                    id=spec.id,
                    phase_id=spec.phase_id,
                    subject_id=spec.subject_id,
                    knowledge_point_id=spec.knowledge_point_id,
                    task_template_id=spec.task_template_id,
                    material_id=spec.material_id,
                    title=spec.title,
                    task_type=spec.task_type,
                    est_minutes=spec.est_minutes,
                    priority=spec.priority,
                )
            )
            created += 1
            continue
        values = (
            item.subject_id,
            item.material_id,
            item.title,
            item.task_type,
            item.est_minutes,
            item.priority,
        )
        new_values = (
            spec.subject_id,
            spec.material_id,
            spec.title,
            spec.task_type,
            spec.est_minutes,
            spec.priority,
        )
        if values != new_values:
            item.subject_id = spec.subject_id
            item.material_id = spec.material_id
            item.title = spec.title
            item.task_type = spec.task_type
            item.est_minutes = spec.est_minutes
            item.priority = spec.priority
            updated += 1
    await session.commit()
    return TaskPoolGenerationResponse(
        created=created,
        updated=updated,
        deleted=deleted,
        total=len(specs),
    )


def _task_pool_query() -> Select[
    tuple[
        TaskPoolItem,
        PlanPhase,
        Subject,
        KnowledgePoint,
        TaskTemplate,
        Material,
    ]
]:
    return (
        select(
            TaskPoolItem,
            PlanPhase,
            Subject,
            KnowledgePoint,
            TaskTemplate,
            Material,
        )
        .join(PlanPhase, TaskPoolItem.phase_id == PlanPhase.id)
        .join(Subject, TaskPoolItem.subject_id == Subject.id)
        .join(KnowledgePoint, TaskPoolItem.knowledge_point_id == KnowledgePoint.id)
        .join(TaskTemplate, TaskPoolItem.task_template_id == TaskTemplate.id)
        .join(
            TaskTemplatePhase,
            and_(
                TaskTemplatePhase.task_template_id == TaskPoolItem.task_template_id,
                TaskTemplatePhase.phase_id == TaskPoolItem.phase_id,
            ),
        )
        .outerjoin(Material, TaskPoolItem.material_id == Material.id)
        .where(TaskTemplate.active.is_(True))
    )


async def list_task_pool(
    session: AsyncSession,
    phase_id: UUID | None,
    subject_id: UUID | None,
    offset: int,
    limit: int,
) -> TaskPoolPage:
    query = _task_pool_query()
    filters = []
    if phase_id is not None:
        filters.append(TaskPoolItem.phase_id == phase_id)
    if subject_id is not None:
        filters.append(TaskPoolItem.subject_id == subject_id)
    if filters:
        query = query.where(*filters)
    rows = (
        await session.execute(
            query.order_by(TaskPoolItem.priority, TaskPoolItem.id).offset(offset).limit(limit)
        )
    ).tuples().all()

    count_query = (
        select(func.count(TaskPoolItem.id))
        .join(TaskTemplate, TaskPoolItem.task_template_id == TaskTemplate.id)
        .join(
            TaskTemplatePhase,
            and_(
                TaskTemplatePhase.task_template_id == TaskPoolItem.task_template_id,
                TaskTemplatePhase.phase_id == TaskPoolItem.phase_id,
            ),
        )
        .where(TaskTemplate.active.is_(True), *filters)
    )
    total = int((await session.scalar(count_query)) or 0)
    return TaskPoolPage(
        items=[
            TaskPoolItemRead(
                id=item.id,
                phase_id=phase.id,
                phase_name=phase.name,
                subject_id=subject.id,
                subject_name=subject.name,
                knowledge_point_id=point.id,
                knowledge_point_name=point.name,
                task_template_id=template.id,
                task_template_name=template.name,
                material_id=material.id if material is not None else None,
                material_name=material.name if material is not None else None,
                title=item.title,
                task_type=item.task_type,
                est_minutes=item.est_minutes,
                priority=item.priority,
            )
            for item, phase, subject, point, template, material in rows
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


def _knowledge_order(
    candidates: list[_Candidate],
    dependencies: Sequence[KnowledgeDependency],
) -> tuple[dict[UUID, int], bool]:
    point_priority: dict[UUID, int] = {}
    for candidate in candidates:
        point_priority[candidate.knowledge_point_id] = min(
            point_priority.get(candidate.knowledge_point_id, candidate.priority),
            candidate.priority,
        )
    successors: dict[UUID, set[UUID]] = defaultdict(set)
    indegree = {point_id: 0 for point_id in point_priority}
    for dependency in dependencies:
        predecessor = dependency.predecessor_kp_id
        successor = dependency.successor_kp_id
        if predecessor not in indegree or successor not in indegree:
            continue
        if successor in successors[predecessor]:
            continue
        successors[predecessor].add(successor)
        indegree[successor] += 1

    ready: list[tuple[int, str, UUID]] = []
    for point_id, degree in indegree.items():
        if degree == 0:
            heappush(ready, (point_priority[point_id], str(point_id), point_id))
    ordered: list[UUID] = []
    while ready:
        _, _, point_id = heappop(ready)
        ordered.append(point_id)
        for successor in sorted(
            successors[point_id],
            key=lambda item: (point_priority[item], str(item)),
        ):
            indegree[successor] -= 1
            if indegree[successor] == 0:
                heappush(
                    ready,
                    (point_priority[successor], str(successor), successor),
                )
    cycle = len(ordered) != len(indegree)
    if cycle:
        ordered.extend(
            sorted(
                (point_id for point_id in indegree if point_id not in ordered),
                key=lambda item: (point_priority[item], str(item)),
            )
        )
    return {point_id: order for order, point_id in enumerate(ordered)}, cycle


def _task_read(task: ScheduledTask) -> PlanTaskRead:
    return PlanTaskRead(
        id=task.id,
        pool_item_id=task.pool_item_id,
        phase_id=task.phase_id,
        phase_name=task.phase_name,
        subject_id=task.subject_id,
        subject_name=task.subject_name,
        knowledge_point_id=task.knowledge_point_id,
        knowledge_point_name=task.knowledge_point_name,
        material_id=task.material_id,
        material_name=task.material_name,
        title=task.title,
        task_type=task.task_type,
        planned_date=task.planned_date,
        est_minutes=task.est_minutes,
        status=task.status,
        actual_minutes=task.actual_minutes,
        carry_count=task.carry_count,
        order=task.order,
    )


def _proposal_read(candidate: _Candidate, planned_date: date, order: int) -> PlanTaskRead:
    return PlanTaskRead(
        id=_scheduled_task_id(candidate.pool_item_id),
        pool_item_id=candidate.pool_item_id,
        phase_id=candidate.phase_id,
        phase_name=candidate.phase_name,
        subject_id=candidate.subject_id,
        subject_name=candidate.subject_name,
        knowledge_point_id=candidate.knowledge_point_id,
        knowledge_point_name=candidate.knowledge_point_name,
        material_id=candidate.material_id,
        material_name=candidate.material_name,
        title=candidate.title,
        task_type=candidate.task_type,
        planned_date=planned_date,
        est_minutes=candidate.est_minutes,
        status="planned",
        order=order,
    )


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _date_range(start_date: date, end_date: date) -> list[date]:
    return [
        start_date + timedelta(days=offset)
        for offset in range((end_date - start_date).days + 1)
    ]


async def _build_plan(
    session: AsyncSession,
    payload: PlanGenerationRequest,
) -> PlanResponse:
    phases = (
        await session.scalars(
            select(PlanPhase)
            .where(
                PlanPhase.start_date <= payload.end_date,
                PlanPhase.end_date >= payload.start_date,
            )
            .options(selectinload(PlanPhase.subject_ratios))
            .order_by(PlanPhase.order, PlanPhase.start_date, PlanPhase.id)
        )
    ).all()
    periods = (
        await session.scalars(
            select(AvailabilityPeriod)
            .where(
                AvailabilityPeriod.start_date <= payload.end_date,
                AvailabilityPeriod.end_date >= payload.start_date,
            )
            .options(selectinload(AvailabilityPeriod.rules))
            .order_by(AvailabilityPeriod.order, AvailabilityPeriod.start_date)
        )
    ).all()
    exceptions = {
        exception.date: exception
        for exception in (
            await session.scalars(
                select(AvailabilityException).where(
                    AvailabilityException.date >= payload.start_date,
                    AvailabilityException.date <= payload.end_date,
                )
            )
        ).all()
    }
    planning_subjects = (
        await session.scalars(select(Subject).order_by(Subject.order, Subject.id))
    ).all()
    candidate_rows = (
        await session.execute(
            _task_pool_query()
            .where(
                PlanPhase.start_date <= payload.end_date,
                PlanPhase.end_date >= payload.start_date,
                PlanPhase.allow_new_tasks.is_(True),
            )
            .order_by(TaskPoolItem.priority, TaskPoolItem.id)
        )
    ).tuples().all()
    candidates = [
        _Candidate(
            pool_item_id=item.id,
            phase_id=phase.id,
            phase_name=phase.name,
            subject_id=subject.id,
            subject_name=subject.name,
            subject_order=subject.order,
            knowledge_point_id=point.id,
            knowledge_point_name=point.name,
            material_id=material.id if material is not None else None,
            material_name=material.name if material is not None else None,
            title=item.title,
            task_type=item.task_type,
            est_minutes=item.est_minutes,
            priority=item.priority,
        )
        for item, phase, subject, point, _, material in candidate_rows
    ]
    pool_item_ids = [candidate.pool_item_id for candidate in candidates]
    existing_query = select(ScheduledTask).where(
        or_(
            and_(
                ScheduledTask.planned_date >= payload.start_date,
                ScheduledTask.planned_date <= payload.end_date,
            ),
            ScheduledTask.pool_item_id.in_(pool_item_ids),
        )
    )
    existing_tasks = (await session.scalars(existing_query)).all()
    reserved_pool_ids = {
        task.pool_item_id
        for task in existing_tasks
        if task.pool_item_id is not None
        and not (
            task.status == "planned"
            and payload.start_date <= task.planned_date <= payload.end_date
        )
    }
    candidates = [
        candidate
        for candidate in candidates
        if candidate.pool_item_id not in reserved_pool_ids
    ]
    fixed_tasks = [
        task
        for task in existing_tasks
        if payload.start_date <= task.planned_date <= payload.end_date
        and task.status != "planned"
    ]

    point_ids = {candidate.knowledge_point_id for candidate in candidates}
    dependencies: Sequence[KnowledgeDependency] = ()
    if point_ids:
        dependencies = (
            await session.scalars(
                select(KnowledgeDependency).where(
                    KnowledgeDependency.predecessor_kp_id.in_(point_ids),
                    KnowledgeDependency.successor_kp_id.in_(point_ids),
                )
            )
        ).all()

    warnings: list[str] = []
    queues: dict[tuple[UUID, UUID], list[_Candidate]] = {}
    candidates_by_group: dict[tuple[UUID, UUID], list[_Candidate]] = defaultdict(list)
    for candidate in candidates:
        candidates_by_group[(candidate.phase_id, candidate.subject_id)].append(candidate)
    for key, group in candidates_by_group.items():
        point_order, cycle = _knowledge_order(group, dependencies)
        if cycle:
            warnings.append(
                f"Knowledge dependency cycle detected for phase {key[0]} subject {key[1]}"
            )
        queues[key] = sorted(
            group,
            key=lambda candidate: (
                point_order[candidate.knowledge_point_id],
                candidate.priority,
                str(candidate.pool_item_id),
            ),
        )

    phase_by_date: dict[date, PlanPhase] = {}
    period_by_date: dict[date, AvailabilityPeriod] = {}
    for day in _date_range(payload.start_date, payload.end_date):
        matching_phase = next(
            (phase for phase in phases if phase.start_date <= day <= phase.end_date),
            None,
        )
        if matching_phase is not None:
            phase_by_date[day] = matching_phase
        matching_period = next(
            (period for period in periods if period.start_date <= day <= period.end_date),
            None,
        )
        if matching_period is not None:
            period_by_date[day] = matching_period

    fixed_reads = [_task_read(task) for task in fixed_tasks]
    day_used: dict[date, int] = defaultdict(int)
    week_used: dict[date, int] = defaultdict(int)
    subject_used: dict[tuple[UUID, UUID], int] = defaultdict(int)
    day_order: dict[date, int] = defaultdict(int)
    for task in fixed_tasks:
        if task.status == "completed":
            day_used[task.planned_date] += task.est_minutes
            week_used[_week_start(task.planned_date)] += task.est_minutes
            if task.phase_id is not None and task.subject_id is not None:
                subject_used[(task.phase_id, task.subject_id)] += task.est_minutes
        day_order[task.planned_date] = max(day_order[task.planned_date], task.order + 1)

    ratios = {
        (ratio.phase_id, ratio.subject_id): ratio.percentage
        for phase in phases
        for ratio in phase.subject_ratios
        if ratio.percentage > 0
    }
    subject_names = {subject.id: subject.name for subject in planning_subjects}
    subject_orders = {subject.id: subject.order for subject in planning_subjects}
    proposals: list[PlanTaskRead] = []
    day_capacity: dict[date, int] = {}
    for day in _date_range(payload.start_date, payload.end_date):
        phase = phase_by_date.get(day)
        period = period_by_date.get(day)
        if period is None:
            day_capacity[day] = 0
            continue
        exception = exceptions.get(day)
        rules = {rule.weekday: rule.available_minutes for rule in period.rules}
        available_minutes = (
            exception.available_minutes
            if exception is not None
            else rules.get(day.weekday(), 0)
        )
        day_capacity[day] = available_minutes
        if phase is None or not phase.allow_new_tasks:
            continue
        week = _week_start(day)
        remaining = min(
            max(available_minutes - day_used[day], 0),
            max(period.weekly_target_minutes - week_used[week], 0),
        )
        while remaining > 0:
            eligible_subjects = [
                subject_id
                for phase_id, subject_id in queues
                if phase_id == phase.id
                and queues[(phase_id, subject_id)]
                and queues[(phase_id, subject_id)][0].est_minutes <= remaining
                and (phase_id, subject_id) in ratios
            ]
            if not eligible_subjects:
                break
            subject_id = min(
                eligible_subjects,
                key=lambda item: (
                    Fraction(
                        subject_used[(phase.id, item)],
                        ratios[(phase.id, item)],
                    ),
                    subject_orders[item],
                    str(item),
                ),
            )
            candidate = queues[(phase.id, subject_id)].pop(0)
            proposal = _proposal_read(candidate, day, day_order[day])
            proposals.append(proposal)
            day_order[day] += 1
            day_used[day] += candidate.est_minutes
            week_used[week] += candidate.est_minutes
            subject_used[(phase.id, subject_id)] += candidate.est_minutes
            remaining = min(
                max(available_minutes - day_used[day], 0),
                max(period.weekly_target_minutes - week_used[week], 0),
            )

    unscheduled_count = sum(len(queue) for queue in queues.values())
    if unscheduled_count:
        warnings.append(f"{unscheduled_count} task-pool items did not fit the requested range")
    if not phases:
        warnings.append("No planning phase overlaps the requested range")
    if not periods:
        warnings.append("No availability period overlaps the requested range")
    if not candidate_rows:
        warnings.append("No eligible task-pool items exist for the requested range")

    all_tasks = sorted(
        [*fixed_reads, *proposals],
        key=lambda task: (task.planned_date, task.order, str(task.id)),
    )
    days = [
        PlanDaySummary(
            date=day,
            available_minutes=day_capacity.get(day, 0),
            planned_minutes=day_used[day],
            remaining_minutes=max(day_capacity.get(day, 0) - day_used[day], 0),
        )
        for day in _date_range(payload.start_date, payload.end_date)
    ]
    subjects = [
        PlanSubjectSummary(
            phase_id=phase.id,
            phase_name=phase.name,
            subject_id=ratio.subject_id,
            subject_name=subject_names.get(ratio.subject_id, str(ratio.subject_id)),
            target_percentage=ratio.percentage,
            planned_minutes=subject_used[(phase.id, ratio.subject_id)],
        )
        for phase in phases
        for ratio in sorted(
            phase.subject_ratios,
            key=lambda item: (subject_orders.get(item.subject_id, 10_000), str(item.subject_id)),
        )
        if ratio.percentage > 0
    ]
    return PlanResponse(
        start_date=payload.start_date,
        end_date=payload.end_date,
        persisted=False,
        tasks=all_tasks,
        days=days,
        subjects=subjects,
        warnings=warnings,
    )


async def preview_plan(
    session: AsyncSession,
    payload: PlanGenerationRequest,
) -> PlanResponse:
    return await _build_plan(session, payload)


async def persist_plan(
    session: AsyncSession,
    payload: PlanGenerationRequest,
) -> PlanResponse:
    plan = await _build_plan(session, payload)
    planned_tasks = [task for task in plan.tasks if task.status == "planned"]
    planned_pool_ids = {
        task.pool_item_id for task in planned_tasks if task.pool_item_id is not None
    }
    existing = (
        await session.scalars(
            select(ScheduledTask).where(
                ScheduledTask.status == "planned",
                ScheduledTask.planned_date >= payload.start_date,
                ScheduledTask.planned_date <= payload.end_date,
            )
        )
    ).all()
    existing_by_pool = {
        task.pool_item_id: task for task in existing if task.pool_item_id is not None
    }
    for existing_task in existing:
        if existing_task.pool_item_id not in planned_pool_ids:
            await session.delete(existing_task)
    for proposal in planned_tasks:
        if proposal.pool_item_id is None:
            continue
        scheduled_task = existing_by_pool.get(proposal.pool_item_id)
        if scheduled_task is None:
            scheduled_task = ScheduledTask(
                id=proposal.id,
                pool_item_id=proposal.pool_item_id,
                phase_id=proposal.phase_id,
                subject_id=proposal.subject_id,
                knowledge_point_id=proposal.knowledge_point_id,
                material_id=proposal.material_id,
                phase_name=proposal.phase_name,
                subject_name=proposal.subject_name,
                knowledge_point_name=proposal.knowledge_point_name,
                material_name=proposal.material_name,
                title=proposal.title,
                task_type=proposal.task_type,
                planned_date=proposal.planned_date,
                est_minutes=proposal.est_minutes,
                status="planned",
                actual_minutes=None,
                done_at=None,
                carry_count=proposal.carry_count,
                order=proposal.order,
            )
            session.add(scheduled_task)
            continue
        scheduled_task.phase_id = proposal.phase_id
        scheduled_task.subject_id = proposal.subject_id
        scheduled_task.knowledge_point_id = proposal.knowledge_point_id
        scheduled_task.material_id = proposal.material_id
        scheduled_task.phase_name = proposal.phase_name
        scheduled_task.subject_name = proposal.subject_name
        scheduled_task.knowledge_point_name = proposal.knowledge_point_name
        scheduled_task.material_name = proposal.material_name
        scheduled_task.title = proposal.title
        scheduled_task.task_type = proposal.task_type
        scheduled_task.planned_date = proposal.planned_date
        scheduled_task.est_minutes = proposal.est_minutes
        scheduled_task.order = proposal.order
    await session.commit()
    return plan.model_copy(update={"persisted": True})


async def get_calendar(
    session: AsyncSession,
    month: str,
    month_start: date,
    month_end: date,
) -> CalendarResponse:
    tasks = (
        await session.scalars(
            select(ScheduledTask)
            .where(
                ScheduledTask.planned_date >= month_start,
                ScheduledTask.planned_date <= month_end,
            )
            .order_by(ScheduledTask.planned_date, ScheduledTask.order, ScheduledTask.id)
        )
    ).all()
    tasks_by_day: dict[date, list[ScheduledTask]] = defaultdict(list)
    for task in tasks:
        tasks_by_day[task.planned_date].append(task)
    days = [
        CalendarDayRead(
            date=day,
            planned_minutes=sum(
                task.est_minutes for task in day_tasks if task.status != "skipped"
            ),
            completed_minutes=sum(
                task.actual_minutes
                if task.actual_minutes is not None
                else task.est_minutes
                for task in day_tasks
                if task.status == "completed"
            ),
            tasks=[_task_read(task) for task in day_tasks],
        )
        for day, day_tasks in sorted(tasks_by_day.items())
    ]
    week_totals: dict[date, tuple[int, int]] = defaultdict(lambda: (0, 0))
    for day in days:
        week = _week_start(day.date)
        planned, completed = week_totals[week]
        week_totals[week] = (
            planned + day.planned_minutes,
            completed + day.completed_minutes,
        )
    weeks = [
        CalendarWeekRead(
            week_start=week,
            week_end=week + timedelta(days=6),
            planned_minutes=planned,
            completed_minutes=completed,
        )
        for week, (planned, completed) in sorted(week_totals.items())
    ]
    return CalendarResponse(month=month, days=days, weeks=weeks)
