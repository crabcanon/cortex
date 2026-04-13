"""Job DTOs."""

from pydantic import BaseModel, Field

from .enums import JobStatus, JobType


class JobAccepted(BaseModel):
    job_id: str
    job_type: JobType
    status: JobStatus = Field(default=JobStatus.QUEUED)
    submitted_at: str
    poll_url: str
    result_url: str | None = None
    cancel_url: str | None = None


class JobStatusSummary(BaseModel):
    job_id: str
    job_type: JobType
    status: JobStatus
    operation_name: str
    submitted_at: str
    started_at: str | None = None
    finished_at: str | None = None
