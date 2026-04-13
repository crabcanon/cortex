"""Trace context helpers."""

from opentelemetry import trace


def get_trace_context() -> dict[str, str | None]:
    """Return the current trace and span identifiers."""
    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return {"trace_id": None, "span_id": None}
    return {
        "trace_id": format(span_context.trace_id, "032x"),
        "span_id": format(span_context.span_id, "016x"),
    }
