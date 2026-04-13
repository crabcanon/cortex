"""Problem Details model."""

from pydantic import BaseModel, Field


class ProblemDetails(BaseModel):
    type: str = Field(default="about:blank")
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    request_id: str | None = None
    decision_id: str | None = None
    reason_code: str | None = None
    required_scopes: list[str] = Field(default_factory=list)
    required_permissions: list[str] = Field(default_factory=list)
    field_errors: list[dict[str, str]] = Field(default_factory=list)
