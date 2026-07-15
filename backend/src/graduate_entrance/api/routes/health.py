from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from graduate_entrance.core.config import Settings, get_settings
from graduate_entrance.db.session import is_database_ready

router = APIRouter(tags=["health"])
public_router = APIRouter(tags=["health"])


class ServiceStatus(BaseModel):
    status: Literal["ok"]
    service: str
    environment: str


class HealthStatus(BaseModel):
    status: Literal["ok", "unavailable"]


@router.get("/ping", response_model=ServiceStatus)
async def ping(settings: Annotated[Settings, Depends(get_settings)]) -> ServiceStatus:
    return ServiceStatus(
        status="ok",
        service=settings.app_name,
        environment=settings.environment,
    )


@public_router.get("/health/live", response_model=HealthStatus)
async def liveness() -> HealthStatus:
    return HealthStatus(status="ok")


@public_router.get("/health/ready", response_model=HealthStatus)
async def readiness(database_ready: Annotated[bool, Depends(is_database_ready)]) -> HealthStatus:
    if not database_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        )
    return HealthStatus(status="ok")
