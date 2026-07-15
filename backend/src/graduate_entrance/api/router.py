from fastapi import APIRouter

from graduate_entrance.api.routes.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
