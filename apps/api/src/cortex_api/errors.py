"""Problem Details exception handlers."""

import logging
from typing import Any

from cortex_common import CortexError
from cortex_contracts import (
    X_DECISION_ID_HEADER,
    X_REQUEST_ID_HEADER,
    X_TRACE_ID_HEADER,
    ProblemDetails,
)
from cortex_observability import get_trace_context
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("cortex.api.errors")


def _problem_response(
    request: Request,
    *,
    status_code: int,
    title: str,
    detail: str,
    error_code: str,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    trace_context = get_trace_context()
    payload = ProblemDetails(
        title=title,
        status=status_code,
        detail=detail,
        error_code=error_code,
        trace_id=trace_context["trace_id"],
        span_id=trace_context["span_id"],
        request_id=getattr(request.state, "request_id", None),
        decision_id=extra.get("decision_id") if extra else None,
        reason_code=extra.get("reason_code") if extra else None,
        required_scopes=extra.get("required_scopes", []) if extra else [],
        required_permissions=extra.get("required_permissions", []) if extra else [],
        field_errors=extra.get("field_errors", []) if extra else [],
    )
    headers = {
        X_REQUEST_ID_HEADER: payload.request_id or "",
        X_TRACE_ID_HEADER: payload.trace_id or "",
    }
    if payload.decision_id:
        headers[X_DECISION_ID_HEADER] = payload.decision_id
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json", exclude_none=True),
        headers={key: value for key, value in headers.items() if value},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(CortexError)
    async def handle_cortex_error(request: Request, exc: CortexError) -> JSONResponse:
        return _problem_response(
            request,
            status_code=exc.status_code,
            title=exc.code.replace("_", " ").title(),
            detail=exc.detail,
            error_code=exc.code,
            extra=dict(exc.extra),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        field_errors = [
            {"field": ".".join(str(part) for part in error["loc"]), "message": error["msg"]}
            for error in exc.errors()
        ]
        return _problem_response(
            request,
            status_code=422,
            title="Validation Error",
            detail="Request validation failed.",
            error_code="validation_error",
            extra={"field_errors": field_errors},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled API exception", exc_info=exc)
        return _problem_response(
            request,
            status_code=500,
            title="Internal Server Error",
            detail="Unexpected server error.",
            error_code="internal_error",
        )
