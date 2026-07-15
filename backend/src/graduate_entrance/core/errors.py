from collections.abc import Mapping

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException


class ValidationIssue(BaseModel):
    type: str
    location: str
    message: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str
    details: list[ValidationIssue] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


def request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


def error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: list[ValidationIssue] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            request_id=request_id(request),
            details=details,
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
        headers=headers,
    )


def install_exception_handlers(application: FastAPI) -> None:
    @application.exception_handler(HTTPException)
    async def handle_http_exception(
        request: Request,
        exception: HTTPException,
    ) -> JSONResponse:
        message = exception.detail if isinstance(exception.detail, str) else "Request failed"
        code = (
            "unauthorized"
            if exception.status_code == status.HTTP_401_UNAUTHORIZED
            else "http_error"
        )
        return error_response(
            request,
            exception.status_code,
            code,
            message,
            headers=exception.headers,
        )

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exception: RequestValidationError,
    ) -> JSONResponse:
        return error_response(
            request,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "validation_error",
            "Request validation failed",
            details=[
                ValidationIssue(
                    type=str(issue["type"]),
                    location=".".join(str(part) for part in issue["loc"]),
                    message=str(issue["msg"]),
                )
                for issue in exception.errors()
            ],
        )
