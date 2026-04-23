"""Job query and control helpers."""

from datetime import datetime

from cortex_common import CortexError, NotFoundError, utc_now
from cortex_contracts import (
    JobError,
    JobEvent,
    JobMetrics,
    JobStatusDetail,
    TelemetryContext,
)
from cortex_contracts import (
    JobStatus as ContractJobStatus,
)
from cortex_contracts import (
    JobType as ContractJobType,
)
from cortex_db import CortexUnitOfWork
from cortex_domain import JobEventRecord, JobRecord, JobStatus


def _duration_ms(started_at: datetime | None, finished_at: datetime | None) -> int | None:
    if started_at is None or finished_at is None:
        return None
    return int((finished_at - started_at).total_seconds() * 1000)


def _to_job_status(job: JobRecord) -> JobStatusDetail:
    return JobStatusDetail(
        job_id=job.job_id,
        job_type=ContractJobType(job.job_type.value),
        operation_name=job.operation_name,
        status=ContractJobStatus(job.status.value),
        target_type=job.target_type,
        target_id=job.target_id,
        correlation_id=job.request_id,
        submitted_at=job.submitted_at,
        started_at=job.started_at,
        completed_at=job.finished_at,
        error=JobError(code=job.error_code, message=job.error_message)
        if job.error_code or job.error_message
        else None,
        metrics=JobMetrics(
            queue_latency_ms=_duration_ms(job.submitted_at, job.started_at),
            run_latency_ms=_duration_ms(job.started_at, job.finished_at),
        ),
        telemetry=TelemetryContext(
            trace_id=job.trace_id,
            span_id=job.span_id,
            request_id=job.request_id,
            deployment_ring=str(job.deployment_context.get("deployment_ring"))
            if job.deployment_context.get("deployment_ring")
            else None,
            experiment_variant=str(job.experiment_context.get("variant"))
            if job.experiment_context.get("variant")
            else None,
        ),
    )


def _to_job_event(event: JobEventRecord) -> JobEvent:
    return JobEvent(
        sequence=event.sequence_no,
        level=event.level,
        event_type=event.event_type,
        event_at=event.event_at,
        message=event.message,
        details=event.details,
        telemetry=TelemetryContext(trace_id=event.trace_id, span_id=event.span_id),
    )


async def get_job_status(uow: CortexUnitOfWork, job_id: str) -> JobStatusDetail:
    job = await uow.jobs.get(job_id)
    if job is None:
        raise NotFoundError(f"Job `{job_id}` was not found.")
    return _to_job_status(job)


async def list_job_events(
    uow: CortexUnitOfWork,
    job_id: str,
    *,
    limit: int = 100,
) -> list[JobEvent]:
    job = await uow.jobs.get(job_id)
    if job is None:
        raise NotFoundError(f"Job `{job_id}` was not found.")
    events = await uow.job_events.list_for_job(job_id, limit=limit)
    return [_to_job_event(event) for event in events]


async def cancel_job(uow: CortexUnitOfWork, job_id: str) -> JobStatusDetail:
    job = await uow.jobs.get(job_id)
    if job is None:
        raise NotFoundError(f"Job `{job_id}` was not found.")
    if job.status not in {JobStatus.QUEUED, JobStatus.RUNNING}:
        raise CortexError(
            code="job_state_conflict",
            detail="Only queued or running jobs can be cancelled.",
            status_code=409,
        )

    updated = await uow.jobs.update_status(
        job_id,
        status=JobStatus.CANCELLED,
        finished_at=utc_now(),
    )
    if updated is None:  # pragma: no cover - defensive
        raise NotFoundError(f"Job `{job_id}` was not found.")

    max_seq = await uow.job_events.get_max_sequence_no(job_id)
    next_sequence = max_seq + 1
    await uow.job_events.add(
        JobEventRecord(
            job_id=job_id,
            sequence_no=next_sequence,
            level="info",
            event_type="job.cancelled",
            message="Cancellation accepted by API control plane.",
            details={},
            trace_id=updated.trace_id,
            span_id=updated.span_id,
            event_at=utc_now(),
        )
    )
    return _to_job_status(updated)
