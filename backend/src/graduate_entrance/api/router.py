from fastapi import APIRouter, Depends

from graduate_entrance.api.routes.health import public_router as public_health_router
from graduate_entrance.api.routes.health import router as protected_health_router
from graduate_entrance.api.routes.planning import router as planning_router
from graduate_entrance.api.routes.syllabus import router as syllabus_router
from graduate_entrance.core.auth import require_api_token

public_api_router = APIRouter()
public_api_router.include_router(public_health_router)

protected_api_router = APIRouter(dependencies=[Depends(require_api_token)])
protected_api_router.include_router(protected_health_router)
protected_api_router.include_router(syllabus_router)
protected_api_router.include_router(planning_router)
