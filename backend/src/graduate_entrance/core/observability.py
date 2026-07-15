import logging
from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, status
from starlette.responses import Response

from graduate_entrance.core.errors import error_response

logger = logging.getLogger("graduate_entrance.access")


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def install_request_logging(application: FastAPI) -> None:
    @application.middleware("http")
    async def request_logging(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request.state.request_id = request.headers.get("X-Request-ID") or str(uuid4())
        started_at = perf_counter()
        try:
            response = await call_next(request)
        except Exception as exception:
            logger.error(
                "unhandled_error method=%s path=%s request_id=%s",
                request.method,
                request.url.path,
                request.state.request_id,
                exc_info=exception,
            )
            response = error_response(
                request,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "internal_error",
                "An unexpected error occurred",
            )
        response.headers["X-Request-ID"] = request.state.request_id
        logger.info(
            "request method=%s path=%s status=%s duration_ms=%.2f request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            (perf_counter() - started_at) * 1000,
            request.state.request_id,
        )
        return response
