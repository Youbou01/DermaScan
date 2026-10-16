"""Turns every failure into the same `application/problem+json` shape."""

from http import HTTPStatus
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AppError, ProblemDetails
from app.core.middleware import REQUEST_ID_HEADER

PROBLEM_JSON = "application/problem+json"
logger = structlog.get_logger(__name__)


def _type_uri(code: str) -> str:
    return f"urn:skincare:problem:{code}"


def _request_id(request: Request) -> str | None:
    value: str | None = request.scope.get("state", {}).get("request_id")
    return value


def _problem(
    request: Request,
    *,
    status: int,
    code: str,
    title: str,
    detail: str | None = None,
    errors: list[dict[str, Any]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    request_id = _request_id(request)
    body = ProblemDetails(
        type=_type_uri(code),
        title=title,
        status=status,
        detail=detail,
        instance=request.url.path,
        request_id=request_id,
        errors=errors,
    )
    response_headers = dict(headers or {})
    if request_id:
        response_headers[REQUEST_ID_HEADER] = request_id
    return JSONResponse(
        body.model_dump(exclude_none=True),
        status_code=status,
        media_type=PROBLEM_JSON,
        headers=response_headers,
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    if exc.status_code >= 500:
        logger.error("app_error", code=exc.code, detail=exc.detail, exc_info=exc)
    return _problem(
        request, status=exc.status_code, code=exc.code, title=exc.title, detail=exc.detail
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    phrase = HTTPStatus(exc.status_code).phrase
    detail = exc.detail if isinstance(exc.detail, str) and exc.detail != phrase else None
    return _problem(
        request,
        status=exc.status_code,
        code=f"http-{exc.status_code}",
        title=phrase,
        detail=detail,
        headers=dict(exc.headers) if exc.headers else None,
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Only loc/msg/type: pydantic's "input" would echo user-supplied data back.
    errors = [
        {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]
    return _problem(
        request,
        status=422,
        code="request-validation-failed",
        title="Request validation failed",
        errors=errors,
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # The details stay in the logs; the client only gets a generic message + request_id.
    logger.error("unhandled_exception", request_id=_request_id(request), exc_info=exc)
    return _problem(
        request,
        status=500,
        code="internal-error",
        title="Internal server error",
        detail="Something went wrong. Quote the request_id when reporting this.",
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_error_handler)
