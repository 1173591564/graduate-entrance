from collections.abc import Collection
from datetime import date
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from graduate_entrance.models.planning import (
    AvailabilityException,
    AvailabilityPeriod,
    AvailabilityRule,
    Material,
    PlanPhase,
    PlanPhaseSubjectRatio,
    TaskTemplate,
    TaskTemplatePhase,
)
from graduate_entrance.models.syllabus import Subject
from graduate_entrance.schemas.planning import (
    AvailabilityExceptionInput,
    AvailabilityExceptionRead,
    AvailabilityPeriodInput,
    AvailabilityPeriodRead,
    AvailabilityRuleInput,
    MaterialInput,
    MaterialRead,
    PhaseSubjectRatioInput,
    PlanningConfigResponse,
    PlanningSubjectRead,
    PlanPhaseInput,
    PlanPhaseRead,
    TaskTemplateInput,
    TaskTemplateRead,
)


def phase_read(phase: PlanPhase) -> PlanPhaseRead:
    return PlanPhaseRead(
        id=phase.id,
        name=phase.name,
        start_date=phase.start_date,
        end_date=phase.end_date,
        description=phase.description,
        milestones=phase.milestones,
        allow_new_tasks=phase.allow_new_tasks,
        order=phase.order,
        subject_ratios=[
            PhaseSubjectRatioInput(
                subject_id=ratio.subject_id,
                percentage=ratio.percentage,
            )
            for ratio in phase.subject_ratios
        ],
    )


def availability_period_read(period: AvailabilityPeriod) -> AvailabilityPeriodRead:
    return AvailabilityPeriodRead(
        id=period.id,
        name=period.name,
        start_date=period.start_date,
        end_date=period.end_date,
        weekly_target_minutes=period.weekly_target_minutes,
        order=period.order,
        rules=[
            AvailabilityRuleInput(
                weekday=rule.weekday,
                available_minutes=rule.available_minutes,
            )
            for rule in period.rules
        ],
    )


def availability_exception_read(
    exception: AvailabilityException,
) -> AvailabilityExceptionRead:
    return AvailabilityExceptionRead(
        id=exception.id,
        date=exception.date,
        available_minutes=exception.available_minutes,
        reason=exception.reason,
    )


def material_read(material: Material) -> MaterialRead:
    return MaterialRead(
        id=material.id,
        subject_id=material.subject_id,
        name=material.name,
        material_type=material.material_type,
        source=material.source,
        description=material.description,
        active=material.active,
        order=material.order,
    )


def task_template_read(template: TaskTemplate) -> TaskTemplateRead:
    return TaskTemplateRead(
        id=template.id,
        subject_id=template.subject_id,
        material_id=template.material_id,
        name=template.name,
        task_type=template.task_type,
        default_est_minutes=template.default_est_minutes,
        description=template.description,
        active=template.active,
        order=template.order,
        phase_ids=sorted((link.phase_id for link in template.phase_links), key=str),
    )


async def get_planning_config(session: AsyncSession) -> PlanningConfigResponse:
    subjects = (
        await session.scalars(select(Subject).order_by(Subject.order, Subject.name))
    ).all()
    phases = (
        await session.scalars(
            select(PlanPhase)
            .options(selectinload(PlanPhase.subject_ratios))
            .order_by(PlanPhase.order, PlanPhase.start_date)
        )
    ).all()
    periods = (
        await session.scalars(
            select(AvailabilityPeriod)
            .options(selectinload(AvailabilityPeriod.rules))
            .order_by(AvailabilityPeriod.order, AvailabilityPeriod.start_date)
        )
    ).all()
    exceptions = (
        await session.scalars(
            select(AvailabilityException).order_by(AvailabilityException.date)
        )
    ).all()
    materials = (
        await session.scalars(select(Material).order_by(Material.order, Material.name))
    ).all()
    templates = (
        await session.scalars(
            select(TaskTemplate)
            .options(selectinload(TaskTemplate.phase_links))
            .order_by(TaskTemplate.order, TaskTemplate.name)
        )
    ).all()

    return PlanningConfigResponse(
        subjects=[
            PlanningSubjectRead(
                id=subject.id,
                code=subject.code,
                name=subject.name,
                order=subject.order,
            )
            for subject in subjects
        ],
        phases=[phase_read(phase) for phase in phases],
        availability_periods=[availability_period_read(period) for period in periods],
        availability_exceptions=[
            availability_exception_read(exception) for exception in exceptions
        ],
        materials=[material_read(material) for material in materials],
        task_templates=[task_template_read(template) for template in templates],
    )


async def ensure_subjects_exist(session: AsyncSession, subject_ids: Collection[UUID]) -> None:
    if not subject_ids:
        return
    found = set(
        await session.scalars(select(Subject.id).where(Subject.id.in_(subject_ids)))
    )
    missing = set(subject_ids) - found
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="One or more subjects do not exist",
        )


async def ensure_phases_exist(session: AsyncSession, phase_ids: Collection[UUID]) -> None:
    found = set(
        await session.scalars(select(PlanPhase.id).where(PlanPhase.id.in_(phase_ids)))
    )
    missing = set(phase_ids) - found
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="One or more phases do not exist",
        )


async def ensure_phase_available(
    session: AsyncSession,
    payload: PlanPhaseInput,
    excluded_id: UUID | None = None,
) -> None:
    name_query = select(PlanPhase.id).where(PlanPhase.name == payload.name)
    overlap_query = select(PlanPhase.id).where(
        PlanPhase.start_date <= payload.end_date,
        PlanPhase.end_date >= payload.start_date,
    )
    if excluded_id is not None:
        name_query = name_query.where(PlanPhase.id != excluded_id)
        overlap_query = overlap_query.where(PlanPhase.id != excluded_id)
    if await session.scalar(name_query):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phase name already exists",
        )
    if await session.scalar(overlap_query):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phase dates overlap")


async def create_phase(session: AsyncSession, payload: PlanPhaseInput) -> PlanPhaseRead:
    await ensure_subjects_exist(
        session,
        [ratio.subject_id for ratio in payload.subject_ratios],
    )
    await ensure_phase_available(session, payload)
    phase = PlanPhase(
        name=payload.name,
        start_date=payload.start_date,
        end_date=payload.end_date,
        description=payload.description,
        milestones=payload.milestones,
        allow_new_tasks=payload.allow_new_tasks,
        order=payload.order,
        subject_ratios=[
            PlanPhaseSubjectRatio(
                subject_id=ratio.subject_id,
                percentage=ratio.percentage,
            )
            for ratio in payload.subject_ratios
        ],
    )
    session.add(phase)
    await session.commit()
    return phase_read(phase)


async def update_phase(
    session: AsyncSession,
    phase_id: UUID,
    payload: PlanPhaseInput,
) -> PlanPhaseRead:
    phase = await session.get(
        PlanPhase,
        phase_id,
        options=(selectinload(PlanPhase.subject_ratios),),
    )
    if phase is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phase not found")
    await ensure_subjects_exist(
        session,
        [ratio.subject_id for ratio in payload.subject_ratios],
    )
    await ensure_phase_available(session, payload, phase_id)
    phase.name = payload.name
    phase.start_date = payload.start_date
    phase.end_date = payload.end_date
    phase.description = payload.description
    phase.milestones = payload.milestones
    phase.allow_new_tasks = payload.allow_new_tasks
    phase.order = payload.order
    phase.subject_ratios = [
        PlanPhaseSubjectRatio(
            subject_id=ratio.subject_id,
            percentage=ratio.percentage,
        )
        for ratio in payload.subject_ratios
    ]
    await session.commit()
    return phase_read(phase)


async def delete_phase(session: AsyncSession, phase_id: UUID) -> None:
    phase = await session.get(PlanPhase, phase_id)
    if phase is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phase not found")
    template_id = await session.scalar(
        select(TaskTemplatePhase.task_template_id)
        .where(TaskTemplatePhase.phase_id == phase_id)
        .limit(1)
    )
    if template_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phase is used by one or more task templates",
        )
    await session.delete(phase)
    await session.commit()


async def ensure_period_available(
    session: AsyncSession,
    payload: AvailabilityPeriodInput,
    excluded_id: UUID | None = None,
) -> None:
    name_query = select(AvailabilityPeriod.id).where(AvailabilityPeriod.name == payload.name)
    overlap_query = select(AvailabilityPeriod.id).where(
        AvailabilityPeriod.start_date <= payload.end_date,
        AvailabilityPeriod.end_date >= payload.start_date,
    )
    if excluded_id is not None:
        name_query = name_query.where(AvailabilityPeriod.id != excluded_id)
        overlap_query = overlap_query.where(AvailabilityPeriod.id != excluded_id)
    if await session.scalar(name_query):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Availability period name already exists",
        )
    if await session.scalar(overlap_query):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Availability period dates overlap",
        )


async def create_availability_period(
    session: AsyncSession,
    payload: AvailabilityPeriodInput,
) -> AvailabilityPeriodRead:
    await ensure_period_available(session, payload)
    period = AvailabilityPeriod(
        name=payload.name,
        start_date=payload.start_date,
        end_date=payload.end_date,
        weekly_target_minutes=payload.weekly_target_minutes,
        order=payload.order,
        rules=[
            AvailabilityRule(
                weekday=rule.weekday,
                available_minutes=rule.available_minutes,
            )
            for rule in payload.rules
        ],
    )
    session.add(period)
    await session.commit()
    return availability_period_read(period)


async def update_availability_period(
    session: AsyncSession,
    period_id: UUID,
    payload: AvailabilityPeriodInput,
) -> AvailabilityPeriodRead:
    period = await session.get(
        AvailabilityPeriod,
        period_id,
        options=(selectinload(AvailabilityPeriod.rules),),
    )
    if period is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability period not found",
        )
    await ensure_period_available(session, payload, period_id)
    period.name = payload.name
    period.start_date = payload.start_date
    period.end_date = payload.end_date
    period.weekly_target_minutes = payload.weekly_target_minutes
    period.order = payload.order
    period.rules = [
        AvailabilityRule(
            weekday=rule.weekday,
            available_minutes=rule.available_minutes,
        )
        for rule in payload.rules
    ]
    await session.commit()
    return availability_period_read(period)


async def delete_availability_period(session: AsyncSession, period_id: UUID) -> None:
    period = await session.get(AvailabilityPeriod, period_id)
    if period is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability period not found",
        )
    await session.delete(period)
    await session.commit()


async def ensure_exception_date_available(
    session: AsyncSession,
    exception_date: date,
    excluded_id: UUID | None = None,
) -> None:
    query = select(AvailabilityException.id).where(
        AvailabilityException.date == exception_date
    )
    if excluded_id is not None:
        query = query.where(AvailabilityException.id != excluded_id)
    if await session.scalar(query):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Availability exception already exists for this date",
        )


async def create_availability_exception(
    session: AsyncSession,
    payload: AvailabilityExceptionInput,
) -> AvailabilityExceptionRead:
    await ensure_exception_date_available(session, payload.date)
    exception = AvailabilityException(
        date=payload.date,
        available_minutes=payload.available_minutes,
        reason=payload.reason,
    )
    session.add(exception)
    await session.commit()
    return availability_exception_read(exception)


async def update_availability_exception(
    session: AsyncSession,
    exception_id: UUID,
    payload: AvailabilityExceptionInput,
) -> AvailabilityExceptionRead:
    exception = await session.get(AvailabilityException, exception_id)
    if exception is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability exception not found",
        )
    await ensure_exception_date_available(session, payload.date, exception_id)
    exception.date = payload.date
    exception.available_minutes = payload.available_minutes
    exception.reason = payload.reason
    await session.commit()
    return availability_exception_read(exception)


async def delete_availability_exception(session: AsyncSession, exception_id: UUID) -> None:
    exception = await session.get(AvailabilityException, exception_id)
    if exception is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability exception not found",
        )
    await session.delete(exception)
    await session.commit()


async def create_material(session: AsyncSession, payload: MaterialInput) -> MaterialRead:
    if payload.subject_id is not None:
        await ensure_subjects_exist(session, [payload.subject_id])
    material = Material(
        subject_id=payload.subject_id,
        name=payload.name,
        material_type=payload.material_type,
        source=payload.source,
        description=payload.description,
        active=payload.active,
        order=payload.order,
    )
    session.add(material)
    await session.commit()
    return material_read(material)


async def update_material(
    session: AsyncSession,
    material_id: UUID,
    payload: MaterialInput,
) -> MaterialRead:
    material = await session.get(Material, material_id)
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    if payload.subject_id is not None:
        await ensure_subjects_exist(session, [payload.subject_id])
    material.subject_id = payload.subject_id
    material.name = payload.name
    material.material_type = payload.material_type
    material.source = payload.source
    material.description = payload.description
    material.active = payload.active
    material.order = payload.order
    await session.commit()
    return material_read(material)


async def delete_material(session: AsyncSession, material_id: UUID) -> None:
    material = await session.get(Material, material_id)
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    await session.delete(material)
    await session.commit()


async def validate_template_references(
    session: AsyncSession,
    payload: TaskTemplateInput,
) -> None:
    await ensure_subjects_exist(session, [payload.subject_id])
    await ensure_phases_exist(session, payload.phase_ids)
    if payload.material_id is None:
        return
    material = await session.get(Material, payload.material_id)
    if material is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Material does not exist",
        )
    if material.subject_id is not None and material.subject_id != payload.subject_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Material belongs to a different subject",
        )


async def create_task_template(
    session: AsyncSession,
    payload: TaskTemplateInput,
) -> TaskTemplateRead:
    await validate_template_references(session, payload)
    template = TaskTemplate(
        subject_id=payload.subject_id,
        material_id=payload.material_id,
        name=payload.name,
        task_type=payload.task_type,
        default_est_minutes=payload.default_est_minutes,
        description=payload.description,
        active=payload.active,
        order=payload.order,
        phase_links=[
            TaskTemplatePhase(phase_id=phase_id) for phase_id in payload.phase_ids
        ],
    )
    session.add(template)
    await session.commit()
    return task_template_read(template)


async def update_task_template(
    session: AsyncSession,
    template_id: UUID,
    payload: TaskTemplateInput,
) -> TaskTemplateRead:
    template = await session.get(
        TaskTemplate,
        template_id,
        options=(selectinload(TaskTemplate.phase_links),),
    )
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task template not found",
        )
    await validate_template_references(session, payload)
    template.subject_id = payload.subject_id
    template.material_id = payload.material_id
    template.name = payload.name
    template.task_type = payload.task_type
    template.default_est_minutes = payload.default_est_minutes
    template.description = payload.description
    template.active = payload.active
    template.order = payload.order
    template.phase_links = [
        TaskTemplatePhase(phase_id=phase_id) for phase_id in payload.phase_ids
    ]
    await session.commit()
    return task_template_read(template)


async def delete_task_template(session: AsyncSession, template_id: UUID) -> None:
    template = await session.get(TaskTemplate, template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task template not found",
        )
    await session.delete(template)
    await session.commit()
