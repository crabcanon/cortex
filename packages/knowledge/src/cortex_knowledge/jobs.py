"""Async knowledge job control-plane helpers."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from cortex_common import NotFoundError, new_prefixed_id, normalize_idempotency_key, utc_now
from cortex_contracts import (
    AddJobRequest,
    CognifyJobRequest,
    JobAccepted,
    MemifyJobRequest,
    TelemetryContext,
)
from cortex_contracts import (
    JobStatus as ContractJobStatus,
)
from cortex_contracts import (
    JobType as ContractJobType,
)
from cortex_db import CortexUnitOfWork
from cortex_domain import (
    DatasetRecord,
    JobEventRecord,
    JobRecord,
    JobStatus,
    JobType,
    KnowledgeRunRecord,
)
from cortex_observability import get_trace_context

QUEUE_CONTEXT_KEY = "knowledge_worker"
DEFAULT_EXECUTION_TIMEOUT_SECONDS = 900
KNOWLEDGE_JOB_TYPES = (
    JobType.KNOWLEDGE_ADD,
    JobType.KNOWLEDGE_COGNIFY,
    JobType.KNOWLEDGE_MEMIFY,
)


class KnowledgeJobControlService:
    """Submit and manage queued Knowledge jobs without binding to a queue vendor."""

    async def submit_add(
        self,
        *,
        uow: CortexUnitOfWork,
        caller: Any,
        dataset: DatasetRecord,
        request: AddJobRequest,
        idempotency_key: str | None = None,
        request_id: str | None = None,
    ) -> JobAccepted:
        return await self._submit(
            uow=uow,
            caller=caller,
            dataset=dataset,
            job_type=JobType.KNOWLEDGE_ADD,
            operation_name="knowledge.add",
            request_payload=request.model_dump(mode="json"),
            idempotency_key=idempotency_key,
            request_id=request_id,
        )

    async def submit_cognify(
        self,
        *,
        uow: CortexUnitOfWork,
        caller: Any,
        dataset: DatasetRecord,
        request: CognifyJobRequest,
        idempotency_key: str | None = None,
        request_id: str | None = None,
    ) -> JobAccepted:
        return await self._submit(
            uow=uow,
            caller=caller,
            dataset=dataset,
            job_type=JobType.KNOWLEDGE_COGNIFY,
            operation_name="knowledge.cognify",
            request_payload=request.model_dump(mode="json"),
            idempotency_key=idempotency_key,
            request_id=request_id,
        )

    async def submit_memify(
        self,
        *,
        uow: CortexUnitOfWork,
        caller: Any,
        dataset: DatasetRecord,
        request: MemifyJobRequest,
        idempotency_key: str | None = None,
        request_id: str | None = None,
    ) -> JobAccepted:
        return await self._submit(
            uow=uow,
            caller=caller,
            dataset=dataset,
            job_type=JobType.KNOWLEDGE_MEMIFY,
            operation_name="knowledge.memify",
            request_payload=request.model_dump(mode="json"),
            idempotency_key=idempotency_key,
            request_id=request_id,
        )

    async def get_run_by_job(
        self,
        *,
        uow: CortexUnitOfWork,
        job_id: str,
    ) -> KnowledgeRunRecord:
        run = await uow.knowledge_runs.get_by_job(job_id)
        if run is None:
            raise NotFoundError(f"Knowledge run for job `{job_id}` was not found.")
        return run

    async def next_queued_job(self, *, uow: CortexUnitOfWork) -> JobRecord | None:
        jobs = await uow.jobs.list_queued_for_types(job_types=KNOWLEDGE_JOB_TYPES, limit=1)
        return jobs[0] if jobs else None

    async def recover_stale_leases(
        self,
        *,
        uow: CortexUnitOfWork,
        stale_before: datetime,
        limit: int = 100,
    ) -> int:
        recovered = 0
        stale_jobs = await uow.jobs.list_stale_running_for_types(
            job_types=KNOWLEDGE_JOB_TYPES,
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
                    event_type=f"{self._event_prefix(job.job_type)}.lease_recovered",
                    message="Stale knowledge worker lease recovered and job requeued.",
                    details=state,
                )
            else:
                state["status"] = "failed"
                await uow.jobs.update_status(
                    job.job_id,
                    status=JobStatus.FAILED,
                    finished_at=utc_now(),
                    error_code="knowledge_worker_lease_expired",
                    error_message="Knowledge worker lease expired and retry budget was exhausted.",
                    deployment_context=self._with_queue_state(job, state),
                )
                await self._append_event(
                    uow,
                    job=job,
                    level="error",
                    event_type=f"{self._event_prefix(job.job_type)}.lease_expired",
                    message="Stale knowledge worker lease expired with no retry budget left.",
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
        recover_stale: bool = True,
    ) -> JobRecord | None:
        now = utc_now()
        if recover_stale:
            await self.recover_stale_leases(
                uow=uow,
                stale_before=now - timedelta(seconds=lease_seconds),
            )

        job = await self.next_queued_job(uow=uow)
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
            event_type=f"{self._event_prefix(job.job_type)}.started",
            message="Knowledge worker started execution.",
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
        result_summary: dict[str, Any],
    ) -> None:
        state = self._queue_state(job)
        state["status"] = "succeeded"
        state["completed_at"] = self._iso(utc_now())
        state["lease_owner"] = None
        state["lease_expires_at"] = None
        updated = await uow.jobs.update_status(
            job.job_id,
            status=JobStatus.SUCCEEDED,
            deployment_context=self._with_queue_state(job, state),
            result_payload=result_summary,
        )
        run = await self.get_run_by_job(uow=uow, job_id=job.job_id)
        run.result_summary = dict(result_summary)
        run.deployment_context = self._with_queue_state(job, state)
        await uow.knowledge_runs.update(run)
        await self._append_event(
            uow,
            job=updated or job,
            level="info",
            event_type=f"{self._event_prefix(job.job_type)}.succeeded",
            message="Knowledge worker completed execution.",
            details=result_summary,
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
        state["last_error_code"] = getattr(error, "code", "knowledge_worker_failed")
        state["lease_owner"] = None
        state["lease_expires_at"] = None
        run = await self.get_run_by_job(uow=uow, job_id=job.job_id)
        run.deployment_context = self._with_queue_state(job, state)
        run.result_summary = {
            "status": "failed",
            "error_code": getattr(error, "code", "knowledge_worker_failed"),
            "error_message": str(error),
        }
        if self._attempts_remaining(state):
            state["status"] = "queued"
            await uow.jobs.update_status(
                job.job_id,
                status=JobStatus.QUEUED,
                heartbeat_at=utc_now(),
                deployment_context=self._with_queue_state(job, state),
            )
            await uow.knowledge_runs.update(run)
            await self._append_event(
                uow,
                job=job,
                level="warning",
                event_type=f"{self._event_prefix(job.job_type)}.retry_scheduled",
                message="Knowledge worker scheduled the job for retry.",
                details=state,
            )
            return "retrying"

        state["status"] = "failed"
        state["completed_at"] = self._iso(utc_now())
        await uow.jobs.update_status(
            job.job_id,
            status=JobStatus.FAILED,
            finished_at=utc_now(),
            error_code=getattr(error, "code", "knowledge_worker_failed"),
            error_message=str(error),
            deployment_context=self._with_queue_state(job, state),
        )
        await uow.knowledge_runs.update(run)
        await self._append_event(
            uow,
            job=job,
            level="error",
            event_type=f"{self._event_prefix(job.job_type)}.failed",
            message="Knowledge worker failed execution.",
            details=state,
        )
        return "failed"

    async def _submit(
        self,
        *,
        uow: CortexUnitOfWork,
        caller: Any,
        dataset: DatasetRecord,
        job_type: JobType,
        operation_name: str,
        request_payload: dict[str, Any],
        idempotency_key: str | None,
        request_id: str | None,
    ) -> JobAccepted:
        normalized_key = normalize_idempotency_key(idempotency_key) if idempotency_key else None
        if normalized_key is not None:
            existing = await uow.jobs.get_by_idempotency(
                caller.tenant_id,
                job_type=job_type,
                idempotency_key=normalized_key,
            )
            if existing is not None:
                return self._accepted(existing)

        now = utc_now()
        trace_context = get_trace_context()
        queue_state = self._initial_queue_state()
        job = await uow.jobs.add(
            JobRecord(
                job_id=new_prefixed_id("job"),
                tenant_id=caller.tenant_id,
                job_type=job_type,
                status=JobStatus.QUEUED,
                operation_name=operation_name,
                priority=5,
                idempotency_key=normalized_key,
                target_type="dataset",
                target_id=dataset.dataset_id,
                submitted_at=now,
                request_id=request_id,
                trace_id=trace_context.get("trace_id"),
                span_id=trace_context.get("span_id"),
                request_payload=request_payload,
                telemetry_context={
                    "trace_id": trace_context.get("trace_id"),
                    "span_id": trace_context.get("span_id"),
                    "request_id": request_id,
                },
                deployment_context={QUEUE_CONTEXT_KEY: queue_state},
                submitted_by=caller.actor_id or caller.subject,
            )
        )
        await uow.knowledge_runs.add(
            KnowledgeRunRecord(
                knowledge_run_id=new_prefixed_id("krun"),
                job_id=job.job_id,
                dataset_id=dataset.dataset_id,
                operation_name=operation_name,
                trace_id=job.trace_id,
                request_payload=request_payload,
                result_summary={},
                telemetry_context=job.telemetry_context,
                deployment_context={QUEUE_CONTEXT_KEY: queue_state},
                experiment_context=job.experiment_context,
            )
        )
        await self._append_event(
            uow,
            job=job,
            level="info",
            event_type=f"{self._event_prefix(job.job_type)}.queued",
            message="Knowledge job queued.",
            details={
                "dataset_id": dataset.dataset_id,
                "dataset_key": dataset.dataset_key,
                **queue_state,
            },
        )
        return self._accepted(job)

    @staticmethod
    def _accepted(job: JobRecord) -> JobAccepted:
        return JobAccepted(
            job_id=job.job_id,
            job_type=ContractJobType(job.job_type.value),
            status=ContractJobStatus(job.status.value),
            submitted_at=job.submitted_at,
            poll_url=f"/v1/jobs/{job.job_id}",
            cancel_url=f"/v1/jobs/{job.job_id}/cancel",
            telemetry=TelemetryContext(
                trace_id=job.trace_id,
                span_id=job.span_id,
                request_id=job.request_id,
            ),
        )

    @staticmethod
    def _initial_queue_state() -> dict[str, Any]:
        return {
            "attempt": 0,
            "max_attempts": 1,
            "execution_timeout_seconds": DEFAULT_EXECUTION_TIMEOUT_SECONDS,
            "status": "queued",
            "lease_owner": None,
            "lease_expires_at": None,
            "heartbeat_at": None,
        }

    @staticmethod
    def _queue_state(job: JobRecord) -> dict[str, Any]:
        state = job.deployment_context.get(QUEUE_CONTEXT_KEY)
        if isinstance(state, dict):
            return dict(state)
        return KnowledgeJobControlService._initial_queue_state()

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

    @staticmethod
    def _event_prefix(job_type: JobType) -> str:
        return {
            JobType.KNOWLEDGE_ADD: "knowledge.add",
            JobType.KNOWLEDGE_COGNIFY: "knowledge.cognify",
            JobType.KNOWLEDGE_MEMIFY: "knowledge.memify",
        }[job_type]

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
        next_sequence = (await uow.job_events.get_max_sequence_no(job.job_id)) + 1
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
