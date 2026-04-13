"""Logging correlation helpers."""

import logging

from .context import get_trace_context


class TraceContextFilter(logging.Filter):
    """Inject trace correlation fields into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        context = get_trace_context()
        record.trace_id = context["trace_id"]
        record.span_id = context["span_id"]
        return True


def install_logging_correlation(logger: logging.Logger | None = None) -> logging.Logger:
    """Install trace correlation on a logger if not already present."""
    target_logger = logger or logging.getLogger("cortex")
    if not any(isinstance(existing, TraceContextFilter) for existing in target_logger.filters):
        target_logger.addFilter(TraceContextFilter())
    return target_logger
