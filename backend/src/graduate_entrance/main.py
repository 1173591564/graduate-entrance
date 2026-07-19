from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from graduate_entrance.api.router import protected_api_router, public_api_router
from graduate_entrance.automation.scheduler import create_scheduler
from graduate_entrance.core.config import get_settings
from graduate_entrance.core.errors import ErrorResponse, install_exception_handlers
from graduate_entrance.core.observability import configure_logging, install_request_logging
from graduate_entrance.db.session import dispose_engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    scheduler = None
    if settings.automation_enabled and settings.environment != "test":
        scheduler = create_scheduler(settings)
        scheduler.start()
    yield
    if scheduler is not None:
        scheduler.shutdown(wait=False)
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
        responses={
            401: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_request_logging(application)
    install_exception_handlers(application)
    application.include_router(public_api_router, prefix="/api")
    application.include_router(protected_api_router, prefix="/api")
    return application


app = create_app()
