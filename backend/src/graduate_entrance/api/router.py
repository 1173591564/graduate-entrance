from fastapi import APIRouter

from graduate_entrance.api.routes.health import router as health_router
from graduate_entrance.api.routes.planning import router as planning_router
from graduate_entrance.api.routes.syllabus import router as syllabus_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(syllabus_router)
api_router.include_router(planning_router)
