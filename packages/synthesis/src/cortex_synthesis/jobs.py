"""Async synthesis job control-plane helpers."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from cortex_common import NotFoundError, new_prefixed_id, normalize_idempotency_key, utc_now
from cortex_contracts import (
    JobStatus as ContractJobStatus,
)
from cortex_contracts import (
    JobType as ContractJobType,
)
from cortex_contracts import (
    SynthesisJobAccepted,
    SynthesisJobSubmitRequest,
    SynthesisRunResult,
    TelemetryContext,
)
from cortex_contracts import (
    SynthesisType as ContractSynthesisType,
)
from cortex_db import CortexUnitOfWork
from cortex_domain import (
    JobEventRecord,
    JobRecord,
    JobStatus,
    JobType,
    SynthesisRunRecord,
)
from cortex_domain import (
    SynthesisType as DomainSynthesisType,
)
from cortex_observability import get_trace_context

QUEUE_CONTEXT_KEY = "synthesis_worker"
DEFAULT_EXECUTION_TIMEOUT_SECONDS = 1800


class SynthesisJobControlService:
    async def submit(
        self,
        *,
        uow: CortexUnitOfWork,
        caller: Any,
        request: SynthesisJobSubmitRequest,
        idempotency_key: str | None = None,
        request_id: str | None = None,
    ) -> SynthesisJobAccepted:
        normalized_key = normalize_idempotency_key(idempotency_key) if idempotency_key else None
        if normalized_key is not None:
            existing = await uow.jobs.get_by_idempotency(
                caller.tenant_id,
                job_type=JobType.SYNTHESIS,
                idempotency_key=normalized_key,
            )
            if existing is not None:
                return self._accepted(existing, request)

        trace_context = get_trace_context()
        queue_state = self._initial_queue_state()
        now = utc_now()
        job = await uow.jobs.add(
            JobRecord(
                job_id=new_prefixed_id("job"),
                tenant_id=caller.tenant_id,
                job_type=JobType.SYNTHESIS,
                status=JobStatus.QUEUED,
                operation_name=f"synthesis.{request.synthesis_type.value}",
                submitted_at=now,
                request_id=request_id,
                trace_id=trace_context.get("trace_id"),
                span_id=trace_context.get("span_id"),
                idempotency_key=normalized_key,
                target_type="synthesis_source",
                target_id=request.source.dataset_id
                or request.source.object_id
                or request.source.type,
                request_payload=request.model_dump(mode="json"),
                telemetry_context={
                    "trace_id": trace_context.get("trace_id"),
                    "span_id": trace_context.get("span_id"),
                    "request_id": request_id,
                },
                deployment_context={QUEUE_CONTEXT_KEY: queue_state},
                submitted_by=caller.actor_id or caller.subject,
            )
        )
        await uow.synthesis_runs.add(
            SynthesisRunRecord(
                synthesis_run_id=new_prefixed_id("srun"),
                job_id=job.job_id,
                tenant_id=caller.tenant_id,
                dataset_id=request.source.dataset_id,
                synthesis_type=DomainSynthesisType(request.synthesis_type.value),
                engine_id=request.engine_id,
                profile_key=request.profile_key,
                source_ref=request.source.model_dump(mode="json"),
                config=request.config.model_dump(mode="json"),
                quality_summary={},
                output_summary={},
                trace_id=job.trace_id,
                span_id=job.span_id,
                created_by=caller.actor_id or caller.subject,
            )
        )
        await self._append_event(
            uow,
            job=job,
            level="info",
            event_type="synthesis.job.queued",
            message="Synthesis job queued.",
            details={
                "synthesis_type": request.synthesis_type.value,
                "engine_id": request.engine_id,
                **queue_state,
            },
        )
        return self._accepted(job, request)

    async def get_run_by_job(self, *, uow: CortexUnitOfWork, job_id: str) -> SynthesisRunRecord:
        run = await uow.synthesis_runs.get_by_job(job_id)
        if run is None:
            raise NotFoundError(f"Synthesis run for job `{job_id}` was not found.")
        return run

    async def get_completed_result(
        self, *, uow: CortexUnitOfWork, job_id: str
    ) -> SynthesisRunResult | None:
        job = await uow.jobs.get(job_id)
        if job is None:
            raise NotFoundError(f"Synthesis job `{job_id}` was not found.")
        if job.status is not JobStatus.SUCCEEDED:
            return None
        payload = job.result_payload.get("synthesis_result")
        if not isinstance(payload, dict):
            raise NotFoundError(f"Synthesis result for job `{job_id}` was not found.")
        return SynthesisRunResult.model_validate(payload)

    async def next_queued_job(self, *, uow: CortexUnitOfWork) -> JobRecord | None:
        jobs = await uow.jobs.list_queued(job_type=JobType.SYNTHESIS, limit=1)
        return jobs[0] if jobs else None

    async def recover_stale_leases(
        self,
        *,
        uow: CortexUnitOfWork,
        stale_before: datetime,
        limit: int = 100,
    ) -> int:
        recovered = 0
        stale_jobs = await uow.jobs.list_stale_running(
            job_type=JobType.SYNTHESIS,
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
            else:
                state["status"] = "failed"
                await uow.jobs.update_status(
                    job.job_id,
                    status=JobStatus.FAILED,
                    finished_at=utc_now(),
                    error_code="synthesis_worker_lease_expired",
                    error_message="Synthesis worker lease expired and retry budget was exhausted.",
                    deployment_context=self._with_queue_state(job, state),
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
            event_type="synthesis.job.started",
            message="Synthesis worker started execution.",
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
        result: SynthesisRunResult,
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
            result_payload={"synthesis_result": result.model_dump(mode="json")},
        )
        run = await self.get_run_by_job(uow=uow, job_id=job.job_id)
        run.engine_id = result.engine_id
        run.profile_key = result.profile_key
        run.quality_summary = {
            "quality_gates": [gate.model_dump(mode="json") for gate in result.quality_gates]
        }
        run.output_summary = result.summary.model_dump(mode="json")
        run.output_dataset_id = result.output_dataset_id
        run.output_object_id = _output_object_id(result, preferred_label="synthesis_output")
        await uow.synthesis_runs.update(run)
        await self._append_event(
            uow,
            job=job,
            level="info",
            event_type="synthesis.job.succeeded",
            message="Synthesis worker completed execution.",
            details={"engine_id": result.engine_id, "status": result.status},
        )

    async def record_failed(
        self, *, uow: CortexUnitOfWork, job: JobRecord, error: Exception
    ) -> str:
        state = self._queue_state(job)
        error_message = str(error) or error.__class__.__name__
        error_code = getattr(error, "code", None) or "synthesis_worker_failed"
        state["last_error"] = error_message
        state["last_error_code"] = error_code
        state["lease_owner"] = None
        state["lease_expires_at"] = None
        run = await self.get_run_by_job(uow=uow, job_id=job.job_id)
        run.output_summary = {
            "status": "failed",
            "error_code": error_code,
            "error_message": error_message,
        }
        if self._attempts_remaining(state):
            state["status"] = "queued"
            await uow.jobs.update_status(
                job.job_id,
                status=JobStatus.QUEUED,
                heartbeat_at=utc_now(),
                deployment_context=self._with_queue_state(job, state),
            )
            await uow.synthesis_runs.update(run)
            await self._append_event(
                uow,
                job=job,
                level="warning",
                event_type="synthesis.job.retry_scheduled",
                message="Synthesis worker scheduled the job for retry.",
                details=state,
            )
            return "retrying"
        state["status"] = "failed"
        state["completed_at"] = self._iso(utc_now())
        await uow.jobs.update_status(
            job.job_id,
            status=JobStatus.FAILED,
            finished_at=utc_now(),
            error_code=error_code,
            error_message=error_message,
            deployment_context=self._with_queue_state(job, state),
        )
        await uow.synthesis_runs.update(run)
        await self._append_event(
            uow,
            job=job,
            level="error",
            event_type="synthesis.job.failed",
            message="Synthesis worker failed execution.",
            details=state,
        )
        return "failed"

    @staticmethod
    def _accepted(job: JobRecord, request: SynthesisJobSubmitRequest) -> SynthesisJobAccepted:
        return SynthesisJobAccepted(
            job_id=job.job_id,
            job_type=ContractJobType.SYNTHESIS,
            status=ContractJobStatus(job.status.value),
            submitted_at=job.submitted_at,
            poll_url=f"/v1/jobs/{job.job_id}",
            result_url=f"/v1/synthesis/jobs/{job.job_id}/result",
            cancel_url=f"/v1/jobs/{job.job_id}/cancel",
            synthesis_type=ContractSynthesisType(request.synthesis_type.value),
            engine_id=request.engine_id,
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
        return SynthesisJobControlService._initial_queue_state()

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
        max_sequence_no = await uow.job_events.get_max_sequence_no(job.job_id)

        next_sequence = max_sequence_no + 1
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


def _output_object_id(result: SynthesisRunResult, *, preferred_label: str) -> str | None:
    preferred = [
        output.object_id
        for output in result.outputs
        if output.label == preferred_label and output.object_id.startswith("obj_")
    ]
    if preferred:
        return preferred[0]
    for output in result.outputs:
        if output.object_id.startswith("obj_"):
            return output.object_id
    return None
