"""API error taxonomy and handlers."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from diagram_forge.api.schemas import ErrorResponse


# ─── Error codes ─────────────────────────────────────────────────────────────
# Client errors (4xx)
ERR_INVALID_REQUEST = "INVALID_REQUEST"
ERR_MISSING_FIELD = "MISSING_FIELD"
ERR_INVALID_FORMAT = "INVALID_FORMAT"
ERR_TOO_LONG = "INPUT_TOO_LONG"
ERR_UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
ERR_TOO_LARGE = "FILE_TOO_LARGE"

# Auth errors (401/403)
ERR_MISSING_API_KEY = "MISSING_API_KEY"
ERR_INVALID_API_KEY = "INVALID_API_KEY"

# Quota errors (429)
ERR_RATE_LIMITED = "RATE_LIMITED"

# Server errors (5xx)
ERR_INTERNAL = "INTERNAL_ERROR"
ERR_CIRCUIT_OPEN = "CIRCUIT_OPEN"
ERR_UPSTREAM_ERROR = "UPSTREAM_ERROR"
ERR_TIMEOUT = "TIMEOUT"


def error_response(
    code: str,
    message: str,
    request_id: str | None = None,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    details: dict | None = None,
    retryable: bool = False,
    retry_after: int | None = None,
) -> JSONResponse:
    """Create a standardized error response."""
    body = ErrorResponse(
        code=code,
        message=message,
        details=details,
        request_id=request_id,
        retryable=retryable,
        retry_after_seconds=retry_after,
    )
    headers = {}
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    if request_id is not None:
        headers["X-Request-ID"] = request_id
    headers["X-Data-Retention"] = "24h"
    return JSONResponse(content=body.model_dump(exclude_none=True), status_code=status_code, headers=headers)


def register_handlers(app: FastAPI) -> None:
    """Register global exception handlers."""

    @app.exception_handler(ValidationError)
    async def validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
        return error_response(
            code=ERR_INVALID_REQUEST,
            message="Request validation failed",
            details={"errors": exc.errors()},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    @app.exception_handler(ValueError)
    async def value_handler(request: Request, exc: ValueError) -> JSONResponse:
        return error_response(
            code=ERR_INVALID_REQUEST,
            message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
