"""Request correlation and tracing middleware."""

from collections.abc import Awaitable, Callable

from cortex_common import new_prefixed_id
from cortex_contracts import X_REQUEST_ID_HEADER, X_TRACE_ID_HEADER
from cortex_observability import get_trace_context
from fastapi import Request, Response
from opentelemetry import propagate, trace
from opentelemetry.trace import Status, StatusCode


async def request_context_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get(X_REQUEST_ID_HEADER) or new_prefixed_id("request")
    request.state.request_id = request_id

    tracer = trace.get_tracer("cortex.api.http")
    carrier = dict(request.headers)
    context = propagate.extract(carrier)
    span_name = f"{request.method} {request.url.path}"

    with tracer.start_as_current_span(span_name, context=context) as span:
        span.set_attribute("http.request.method", request.method)
        span.set_attribute("url.path", request.url.path)
        span.set_attribute("cortex.request_id", request_id)
        try:
            response = await call_next(request)
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise

        if response.status_code >= 500:
            span.set_status(Status(StatusCode.ERROR))

        trace_context = get_trace_context()
        response.headers[X_REQUEST_ID_HEADER] = request_id
        if trace_context["trace_id"]:
            response.headers[X_TRACE_ID_HEADER] = str(trace_context["trace_id"])
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
