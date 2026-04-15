"""Shared API header contracts."""

from pydantic import BaseModel

TRACEPARENT_HEADER = "traceparent"
TRACESTATE_HEADER = "tracestate"
BAGGAGE_HEADER = "baggage"
X_TRACE_ID_HEADER = "X-Trace-Id"
X_REQUEST_ID_HEADER = "X-Request-Id"
X_DECISION_ID_HEADER = "X-Decision-Id"
X_CORTEX_ISSUER_SECRET_HEADER = "X-Cortex-Issuer-Secret"


class CorrelationHeaders(BaseModel):
    traceparent: str | None = None
    tracestate: str | None = None
    baggage: str | None = None
    trace_id: str | None = None
    request_id: str | None = None
    decision_id: str | None = None
