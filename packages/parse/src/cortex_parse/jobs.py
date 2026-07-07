"""Async parse job control-plane helpers."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from cortex_common import (
    NotFoundError,
    new_prefixed_id,
    normalize_idempotency_key,
    utc_now,
)
from cortex_contracts import JobAccepted, ParseJobRequest, ParseResult, TelemetryContext
from cortex_contracts import JobStatus as ContractJobStatus
from cortex_contracts import JobType as ContractJobType
from cortex_db import CortexUnitOfWork
from cortex_domain import JobEventRecord, JobRecord, JobStatus, JobType
from cortex_observability import get_trace_context

QUEUE_CONTEXT_KEY = "parse_worker"


class ParseJobControlService:
    """Create and inspect asynchronous parse jobs without binding to a queue vendor."""

    async def submit(
        self,
        *,
        uow: CortexUnitOfWork,
        caller: Any,
        request: ParseJobRequest,
        idempotency_key: str | None = None,
        request_id: str | None = None,
    ) -> JobAccepted:
        normalized_key = normalize_idempotency_key(idempotency_key) if idempotency_key else None
        if normalized_key is not None:
            existing = await uow.jobs.get_by_idempotency(
                caller.tenant_id,
                job_type=JobType.PARSE,
                idempotency_key=normalized_key,
            )
            if existing is not None:
                return self._accepted(existing)

        now = utc_now()
        trace_context = get_trace_context()
        job = await uow.jobs.add(
            JobRecord(
                job_id=new_prefixed_id("job"),
                tenant_id=caller.tenant_id,
                job_type=JobType.PARSE,
                status=JobStatus.QUEUED,
                operation_name="parse.document.async",
                priority=request.priority,
                idempotency_key=normalized_key,
                target_type="parse_source",
                target_id=(
                    request.source.object_id
                    or request.source.url
                    or request.source.uri
                    or request.source.filename
                ),
                submitted_at=now,
                request_id=request_id,
                trace_id=trace_context.get("trace_id"),
                span_id=trace_context.get("span_id"),
                request_payload=request.model_dump(mode="json"),
                telemetry_context={
                    "trace_id": trace_context.get("trace_id"),
                    "span_id": trace_context.get("span_id"),
                    "request_id": request_id,
                },
                deployment_context={
                    QUEUE_CONTEXT_KEY: self._initial_queue_state(request),
                },
                submitted_by=caller.actor_id or caller.subject,
            )
        )
        await self._append_event(
            uow,
            job=job,
            level="info",
            event_type="parse.job.queued",
            message="Parse job queued.",
            details={
                "priority": request.priority,
                **self._initial_queue_state(request),
            },
        )
        return self._accepted(job)

    async def get_completed_result(
        self,
        *,
        uow: CortexUnitOfWork,
        job_id: str,
    ) -> ParseResult | None:
        job = await uow.jobs.get(job_id)
        if job is None:
            raise NotFoundError(f"Parse job `{job_id}` was not found.")
        if job.status is not JobStatus.SUCCEEDED:
            return None
        result_payload = job.result_payload.get("parse_result")
        if not isinstance(result_payload, dict):
            raise NotFoundError(f"Parse result for job `{job_id}` was not found.")
        return ParseResult.model_validate(result_payload)

    async def next_queued_job(
        self,
        *,
        uow: CortexUnitOfWork,
        supported_engine_keys: set[str] | None = None,
        limit: int = 50,
    ) -> JobRecord | None:
        jobs = await uow.jobs.list_queued(job_type=JobType.PARSE, limit=limit)
        for job in jobs:
            if self._worker_can_handle(job, supported_engine_keys):
                return job
        return None

    async def recover_stale_leases(
        self,
        *,
        uow: CortexUnitOfWork,
        stale_before: datetime,
        limit: int = 100,
    ) -> int:
        recovered = 0
        stale_jobs = await uow.jobs.list_stale_running(
            job_type=JobType.PARSE,
            stale_before=stale_before,
            limit=limit,
        )
        for job in stale_jobs:
            state = self._queue_state(job)
            state["last_error"] = "worker lease expired"
            state["lease_owner"] = None
            state["lease_expires_at"] = None
            if self._attempts_remaining(state):
                state["status"] = "queued"
                await uow.jobs.update_status(
                    job.job_id,
                    status=JobStatus.QUEUED,
                    heartbeat_at=utc_now(),
                    deployment_context=self._with_queue_state(job, state),
                )
                await self._append_event(
                    uow,
                    job=job,
                    level="warning",
                    event_type="parse.job.lease_recovered",
                    message="Stale parse worker lease recovered and job requeued.",
                    details=state,
                )
            else:
                state["status"] = "failed"
                await uow.jobs.update_status(
                    job.job_id,
                    status=JobStatus.FAILED,
                    finished_at=utc_now(),
                    error_code="parse_worker_lease_expired",
                    error_message="Parse worker lease expired and retry budget was exhausted.",
                    deployment_context=self._with_queue_state(job, state),
                )
                await self._append_event(
                    uow,
                    job=job,
                    level="error",
                    event_type="parse.job.lease_expired",
                    message="Stale parse worker lease expired with no retry budget left.",
                    details=state,
                )
            recovered += 1
        return recovered

    async def claim_next_job(
        self,
        *,
        uow: CortexUnitOfWork,
        worker_id: str,
        lease_seconds: int,
        supported_engine_keys: set[str] | None = None,
        recover_stale: bool = True,
    ) -> JobRecord | None:
        now = utc_now()
        if recover_stale:
            await self.recover_stale_leases(
                uow=uow,
                stale_before=now - timedelta(seconds=lease_seconds),
            )

        job = await self.next_queued_job(
            uow=uow,
            supported_engine_keys=supported_engine_keys,
        )
        if job is None:
            return None

        state = self._queue_state(job)
        state["attempt"] = int(state.get("attempt", 0)) + 1
        state["status"] = "running"
        state["lease_owner"] = worker_id
        state["heartbeat_at"] = self._iso(now)
        state["lease_expires_at"] = self._iso(now + timedelta(seconds=lease_seconds))
        updated = await uow.jobs.update_status(
            job.job_id,
            status=JobStatus.RUNNING,
            started_at=job.started_at or now,
            heartbeat_at=now,
            deployment_context=self._with_queue_state(job, state),
        )
        claimed = updated or job
        await self._append_event(
            uow,
            job=claimed,
            level="info",
            event_type="parse.job.started",
            message="Parse worker started execution.",
            details=state,
        )
        return claimed

    async def refresh_heartbeat(
        self,
        *,
        uow: CortexUnitOfWork,
        job_id: str,
        worker_id: str,
        lease_seconds: int,
    ) -> JobRecord | None:
        job = await uow.jobs.get(job_id)
        if job is None or job.status is not JobStatus.RUNNING:
            return job
        state = self._queue_state(job)
        if state.get("lease_owner") not in {None, worker_id}:
            return job
        now = utc_now()
        state["lease_owner"] = worker_id
        state["heartbeat_at"] = self._iso(now)
        state["lease_expires_at"] = self._iso(now + timedelta(seconds=lease_seconds))
        return await uow.jobs.update_status(
            job.job_id,
            status=JobStatus.RUNNING,
            heartbeat_at=now,
            deployment_context=self._with_queue_state(job, state),
        )

    async def record_succeeded(
        self,
        *,
        uow: CortexUnitOfWork,
        job: JobRecord,
        result: ParseResult,
    ) -> None:
        state = self._queue_state(job)
        state["status"] = "succeeded"
        state["completed_at"] = self._iso(utc_now())
        state["lease_owner"] = None
        state["lease_expires_at"] = None
        await uow.jobs.update_status(
            job.job_id,
            status=JobStatus.SUCCEEDED,
            deployment_context=self._with_queue_state(job, state),
        )
        await self._append_event(
            uow,
            job=job,
            level="info",
            event_type="parse.job.succeeded",
            message="Parse worker completed execution.",
            details={
                "document_id": result.document.document_id,
                "selected_engine_key": result.diagnostics.selected_engine_key,
            },
        )

    async def record_failed(
        self,
        *,
        uow: CortexUnitOfWork,
        job: JobRecord,
        error: Exception,
    ) -> str:
        state = self._queue_state(job)
        state["last_error"] = str(error)
        state["last_error_code"] = getattr(error, "code", "parse_worker_failed")
        state["lease_owner"] = None
        state["lease_expires_at"] = None
        if self._attempts_remaining(state):
            state["status"] = "queued"
            await uow.jobs.update_status(
                job.job_id,
                status=JobStatus.QUEUED,
                heartbeat_at=utc_now(),
                deployment_context=self._with_queue_state(job, state),
            )
            await self._append_event(
                uow,
                job=job,
                level="warning",
                event_type="parse.job.retry_scheduled",
                message="Parse worker scheduled the job for retry.",
                details=state,
            )
            return "retrying"

        state["status"] = "failed"
        state["completed_at"] = self._iso(utc_now())
        await uow.jobs.update_status(
            job.job_id,
            status=JobStatus.FAILED,
            finished_at=utc_now(),
            error_code=getattr(error, "code", "parse_worker_failed"),
            error_message=str(error),
            deployment_context=self._with_queue_state(job, state),
        )
        await self._append_event(
            uow,
            job=job,
            level="error",
            event_type="parse.job.failed",
            message="Parse worker failed execution.",
            details=state,
        )
        return "failed"

    @staticmethod
    def _accepted(job: JobRecord) -> JobAccepted:
        return JobAccepted(
            job_id=job.job_id,
            job_type=ContractJobType.PARSE,
            status=ContractJobStatus(job.status.value),
            submitted_at=job.submitted_at,
            poll_url=f"/v1/jobs/{job.job_id}",
            result_url=f"/v1/parse/jobs/{job.job_id}/result",
            cancel_url=f"/v1/jobs/{job.job_id}/cancel",
            telemetry=TelemetryContext(
                trace_id=job.trace_id,
                span_id=job.span_id,
                request_id=job.request_id,
            ),
        )

    @staticmethod
    def _initial_queue_state(request: ParseJobRequest) -> dict[str, Any]:
        engine_keys = ParseJobControlService._required_engine_keys(request)
        return {
            "attempt": 0,
            "max_attempts": request.crawl.retry_policy.max_attempts,
            "execution_timeout_seconds": request.timeout_seconds,
            "preferred_engine_key": request.parser.preferred_engine_key,
            "engine_keys": engine_keys,
            "status": "queued",
            "lease_owner": None,
            "lease_expires_at": None,
            "heartbeat_at": None,
        }

    @staticmethod
    def _worker_can_handle(
        job: JobRecord,
        supported_engine_keys: set[str] | None,
    ) -> bool:
        if not supported_engine_keys:
            return True
        try:
            request = ParseJobRequest.model_validate(job.request_payload)
        except Exception:
            return True
        required = set(ParseJobControlService._required_engine_keys(request))
        return not required or bool(required & supported_engine_keys)

    @staticmethod
    def _required_engine_keys(request: ParseJobRequest) -> list[str]:
        if request.parser.allowed_engines:
            return list(dict.fromkeys(request.parser.allowed_engines))
        preferred = request.parser.preferred_engine_key
        return [preferred] if preferred else []

    @staticmethod
    def _queue_state(job: JobRecord) -> dict[str, Any]:
        state = job.deployment_context.get(QUEUE_CONTEXT_KEY)
        if not isinstance(state, dict):
            request = ParseJobRequest.model_validate(job.request_payload)
            return ParseJobControlService._initial_queue_state(request)
        return dict(state)

    @staticmethod
    def _with_queue_state(job: JobRecord, state: dict[str, Any]) -> dict[str, Any]:
        context = dict(job.deployment_context)
        context[QUEUE_CONTEXT_KEY] = dict(state)
        return context

    @staticmethod
    def _attempts_remaining(state: dict[str, Any]) -> bool:
        return int(state.get("attempt", 0)) < int(state.get("max_attempts", 1))

    @staticmethod
    def _iso(value: datetime) -> str:
        return value.isoformat()

    async def _append_event(
        self,
        uow: CortexUnitOfWork,
        *,
        job: JobRecord,
        level: str,
        event_type: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        # Optimization: Fetching the MAX sequence directly via SQL aggregation avoids N+1 memory loading of entire event lists
        max_sequence = await uow.job_events.get_max_sequence_no(job.job_id)
        next_sequence = max_sequence + 1
        await uow.job_events.add(
            JobEventRecord(
                job_id=job.job_id,
                sequence_no=next_sequence,
                level=level,
                event_type=event_type,
                event_at=utc_now(),
                message=message,
                details=details or {},
                trace_id=job.trace_id,
                span_id=job.span_id,
            )
        )
