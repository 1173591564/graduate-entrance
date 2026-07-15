from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from graduate_entrance.db.session import get_session
from graduate_entrance.planning.service import (
    create_availability_exception,
    create_availability_period,
    create_material,
    create_phase,
    create_task_template,
    delete_availability_exception,
    delete_availability_period,
    delete_material,
    delete_phase,
    delete_task_template,
    get_planning_config,
    update_availability_exception,
    update_availability_period,
    update_material,
    update_phase,
    update_task_template,
)
from graduate_entrance.schemas.planning import (
    AvailabilityExceptionInput,
    AvailabilityExceptionRead,
    AvailabilityPeriodInput,
    AvailabilityPeriodRead,
    MaterialInput,
    MaterialRead,
    PlanningConfigResponse,
    PlanPhaseInput,
    PlanPhaseRead,
    TaskTemplateInput,
    TaskTemplateRead,
)

router = APIRouter(prefix="/planning", tags=["planning"])
Session = Annotated[AsyncSession, Depends(get_session)]


async def get_planning_config_response(session: Session) -> PlanningConfigResponse:
    return await get_planning_config(session)


@router.get("/config", response_model=PlanningConfigResponse)
async def read_planning_config(
    config: Annotated[PlanningConfigResponse, Depends(get_planning_config_response)],
) -> PlanningConfigResponse:
    return config


@router.post("/phases", response_model=PlanPhaseRead, status_code=status.HTTP_201_CREATED)
async def add_phase(payload: PlanPhaseInput, session: Session) -> PlanPhaseRead:
    return await create_phase(session, payload)


@router.put("/phases/{phase_id}", response_model=PlanPhaseRead)
async def replace_phase(
    phase_id: UUID,
    payload: PlanPhaseInput,
    session: Session,
) -> PlanPhaseRead:
    return await update_phase(session, phase_id, payload)


@router.delete("/phases/{phase_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_phase(phase_id: UUID, session: Session) -> Response:
    await delete_phase(session, phase_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/availability-periods",
    response_model=AvailabilityPeriodRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_availability_period(
    payload: AvailabilityPeriodInput,
    session: Session,
) -> AvailabilityPeriodRead:
    return await create_availability_period(session, payload)


@router.put(
    "/availability-periods/{period_id}",
    response_model=AvailabilityPeriodRead,
)
async def replace_availability_period(
    period_id: UUID,
    payload: AvailabilityPeriodInput,
    session: Session,
) -> AvailabilityPeriodRead:
    return await update_availability_period(session, period_id, payload)


@router.delete(
    "/availability-periods/{period_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_availability_period(period_id: UUID, session: Session) -> Response:
    await delete_availability_period(session, period_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/availability-exceptions",
    response_model=AvailabilityExceptionRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_availability_exception(
    payload: AvailabilityExceptionInput,
    session: Session,
) -> AvailabilityExceptionRead:
    return await create_availability_exception(session, payload)


@router.put(
    "/availability-exceptions/{exception_id}",
    response_model=AvailabilityExceptionRead,
)
async def replace_availability_exception(
    exception_id: UUID,
    payload: AvailabilityExceptionInput,
    session: Session,
) -> AvailabilityExceptionRead:
    return await update_availability_exception(session, exception_id, payload)


@router.delete(
    "/availability-exceptions/{exception_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_availability_exception(exception_id: UUID, session: Session) -> Response:
    await delete_availability_exception(session, exception_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/materials", response_model=MaterialRead, status_code=status.HTTP_201_CREATED)
async def add_material(payload: MaterialInput, session: Session) -> MaterialRead:
    return await create_material(session, payload)


@router.put("/materials/{material_id}", response_model=MaterialRead)
async def replace_material(
    material_id: UUID,
    payload: MaterialInput,
    session: Session,
) -> MaterialRead:
    return await update_material(session, material_id, payload)


@router.delete("/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_material(material_id: UUID, session: Session) -> Response:
    await delete_material(session, material_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/task-templates",
    response_model=TaskTemplateRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_task_template(
    payload: TaskTemplateInput,
    session: Session,
) -> TaskTemplateRead:
    return await create_task_template(session, payload)


@router.put("/task-templates/{template_id}", response_model=TaskTemplateRead)
async def replace_task_template(
    template_id: UUID,
    payload: TaskTemplateInput,
    session: Session,
) -> TaskTemplateRead:
    return await update_task_template(session, template_id, payload)


@router.delete("/task-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_task_template(template_id: UUID, session: Session) -> Response:
    await delete_task_template(session, template_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
