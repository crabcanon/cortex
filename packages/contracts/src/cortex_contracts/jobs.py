"""Job DTOs."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .enums import JobStatus, JobType


class TelemetryContext(BaseModel):
    trace_id: str | None = None
    span_id: str | None = None
    request_id: str | None = None
    deployment_ring: str | None = None
    experiment_variant: str | None = None


class JobError(BaseModel):
    code: str | None = None
    message: str | None = None


class JobMetrics(BaseModel):
    queue_latency_ms: int | None = Field(default=None, ge=0)
    run_latency_ms: int | None = Field(default=None, ge=0)


class JobAccepted(BaseModel):
    job_id: str
    job_type: JobType
    status: JobStatus = Field(default=JobStatus.QUEUED)
    submitted_at: datetime
    poll_url: str
    result_url: str | None = None
    cancel_url: str | None = None
    request_id: str | None = None
    trace_id: str | None = None


class JobStatusDetail(BaseModel):
    job_id: str
    job_type: JobType
    status: JobStatus
    operation_name: str
    submitted_at: datetime
    progress_percent: float | None = Field(default=None, ge=0, le=100)
    queue_name: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    correlation_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: JobError | None = None
    metrics: JobMetrics | None = None
    telemetry: TelemetryContext | None = None


JobStatusSummary = JobStatusDetail


class JobEvent(BaseModel):
    sequence: int = Field(ge=1)
    level: str
    event_type: str
    event_at: datetime
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    telemetry: TelemetryContext | None = None
