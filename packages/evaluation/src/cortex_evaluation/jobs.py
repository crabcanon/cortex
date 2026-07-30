"""Async evaluation job control-plane helpers."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, TypeVar

from cortex_common import (
    NotFoundError,
    ValidationError,
    new_prefixed_id,
    normalize_idempotency_key,
    utc_now,
)
from cortex_contracts import (
    EvalJobAccepted,
    EvalJobSubmitRequest,
    EvalMetricResult,
    EvalRunResult,
    EvalSyncRequest,
    TelemetryContext,
)
from cortex_contracts import (
    EvalType as ContractEvalType,
)
from cortex_contracts import (
    JobStatus as ContractJobStatus,
)
from cortex_contracts import (
    JobType as ContractJobType,
)
from cortex_db import CortexUnitOfWork
from cortex_domain import (
    EvalRunMetricRecord,
    EvalRunRecord,
    JobEventRecord,
    JobRecord,
    JobStatus,
    JobType,
)
from cortex_domain import (
    EvalType as DomainEvalType,
)
from cortex_observability import get_trace_context

QUEUE_CONTEXT_KEY = "evaluation_worker"
DEFAULT_EXECUTION_TIMEOUT_SECONDS = 1800
_SECRET_LIKE_PATTERN = re.compile(
    r"(?i)"
    r"("
    r"\"?(?:api[_ -]?key|authorization|bearer|access[_ -]?token)\"?"
    r"(?:\s+provided)?\s*[:=]?\s*"
    r")"
    r"(['\"]?)"
    r"("
    r"sk-(?:or-v1-)?[A-Za-z0-9_-]{8,}"
    r"|AIza[A-Za-z0-9_\-*]{8,}"
    r"|[A-Za-z0-9_-]{4,}\*{4,}[A-Za-z0-9_-]{2,}"
    r")"
    r"(['\"]?)"
)
_EvalRequestT = TypeVar("_EvalRequestT", bound=EvalSyncRequest)


class EvaluationJobControlService:
    async def submit(
        self,
        *,
        uow: CortexUnitOfWork,
        caller: Any,
        request: EvalJobSubmitRequest,
        idempotency_key: str | None = None,
        request_id: str | None = None,
    ) -> EvalJobAccepted:
        normalized_key = normalize_idempotency_key(idempotency_key) if idempotency_key else None
        if normalized_key is not None:
            existing = await uow.jobs.get_by_idempotency(
                caller.tenant_id,
                job_type=JobType.EVAL,
                idempotency_key=normalized_key,
            )
            if existing is not None:
                return self._accepted(existing, request)

        await self._validate_request_references(uow=uow, caller=caller, request=request)
        trace_context = get_trace_context()
        queue_state = self._initial_queue_state()
        now = utc_now()
        job_id = new_prefixed_id("job")
        request = ensure_evalscope_task_id(request, job_id)
        job = await uow.jobs.add(
            JobRecord(
                job_id=job_id,
                tenant_id=caller.tenant_id,
                job_type=JobType.EVAL,
                status=JobStatus.QUEUED,
                operation_name=f"evaluation.{request.eval_type.value}",
                submitted_at=now,
                request_id=request_id,
                trace_id=trace_context.get("trace_id"),
                span_id=trace_context.get("span_id"),
                idempotency_key=normalized_key,
                target_type=request.target.type if request.target else "evaluation_target",
                target_id=request.target.endpoint_url
                if request.target
                else request.input.dataset_id,
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
        await uow.eval_runs.add(
            EvalRunRecord(
                eval_run_id=new_prefixed_id("erun"),
                job_id=job.job_id,
                tenant_id=caller.tenant_id,
                dataset_id=request.input.dataset_id,
                eval_type=DomainEvalType(request.eval_type.value),
                engine_id=request.engine_id,
                profile_key=request.profile_key,
                input_ref=request.input.model_dump(mode="json"),
                target_ref=_redact_sensitive_value(
                    request.target.model_dump(mode="json") if request.target else {}
                ),
                metrics_config=[metric.model_dump(mode="json") for metric in request.metrics],
                summary_results={},
                sample_summary={},
                trace_id=job.trace_id,
                span_id=job.span_id,
                created_by=caller.actor_id or caller.subject,
            )
        )
        await self._append_event(
            uow,
            job=job,
            level="info",
            event_type="evaluation.job.queued",
            message="Evaluation job queued.",
            details={
                "eval_type": request.eval_type.value,
                "engine_id": request.engine_id,
                **queue_state,
            },
        )
        return self._accepted(job, request)

    async def create_sync_run(
        self,
        *,
        uow: CortexUnitOfWork,
        caller: Any,
        request: EvalSyncRequest,
        request_id: str | None = None,
    ) -> JobRecord:
        await self._validate_request_references(uow=uow, caller=caller, request=request)
        trace_context = get_trace_context()
        queue_state = self._initial_queue_state()
        now = utc_now()
        job_id = new_prefixed_id("job")
        request = ensure_evalscope_task_id(request, job_id)
        queue_state["attempt"] = 1
        queue_state["max_attempts"] = 1
        queue_state["status"] = "running"
        queue_state["heartbeat_at"] = self._iso(now)
        job = await uow.jobs.add(
            JobRecord(
                job_id=job_id,
                tenant_id=caller.tenant_id,
                job_type=JobType.EVAL,
                status=JobStatus.RUNNING,
                operation_name=f"evaluation.{request.eval_type.value}.sync",
                submitted_at=now,
                started_at=now,
                heartbeat_at=now,
                request_id=request_id,
                trace_id=trace_context.get("trace_id"),
                span_id=trace_context.get("span_id"),
                target_type=request.target.type if request.target else "evaluation_target",
                target_id=request.target.endpoint_url
                if request.target
                else request.input.dataset_id,
                request_payload=_redact_sensitive_value(request.model_dump(mode="json")),
                telemetry_context={
                    "trace_id": trace_context.get("trace_id"),
                    "span_id": trace_context.get("span_id"),
                    "request_id": request_id,
                },
                deployment_context={QUEUE_CONTEXT_KEY: queue_state},
                submitted_by=caller.actor_id or caller.subject,
            )
        )
        await uow.eval_runs.add(
            EvalRunRecord(
                eval_run_id=new_prefixed_id("erun"),
                job_id=job.job_id,
                tenant_id=caller.tenant_id,
                dataset_id=request.input.dataset_id,
                eval_type=DomainEvalType(request.eval_type.value),
                engine_id=request.engine_id,
                profile_key=request.profile_key,
                input_ref=request.input.model_dump(mode="json"),
                target_ref=_redact_sensitive_value(
                    request.target.model_dump(mode="json") if request.target else {}
                ),
                metrics_config=[metric.model_dump(mode="json") for metric in request.metrics],
                summary_results={},
                sample_summary={},
                trace_id=job.trace_id,
                span_id=job.span_id,
                created_by=caller.actor_id or caller.subject,
            )
        )
        await self._append_event(
            uow,
            job=job,
            level="info",
            event_type="evaluation.sync.started",
            message="Synchronous evaluation run started.",
            details={
                "eval_type": request.eval_type.value,
                "engine_id": request.engine_id,
                **queue_state,
            },
        )
        return job

    async def get_run_by_job(self, *, uow: CortexUnitOfWork, job_id: str) -> EvalRunRecord:
        run = await uow.eval_runs.get_by_job(job_id)
        if run is None:
            raise NotFoundError(f"Evaluation run for job `{job_id}` was not found.")
        return run

    async def get_completed_result(
        self, *, uow: CortexUnitOfWork, job_id: str
    ) -> EvalRunResult | None:
        job = await uow.jobs.get(job_id)
        if job is None:
            raise NotFoundError(f"Evaluation job `{job_id}` was not found.")
        if job.status is not JobStatus.SUCCEEDED:
            return None
        payload = job.result_payload.get("eval_result")
        if not isinstance(payload, dict):
            raise NotFoundError(f"Evaluation result for job `{job_id}` was not found.")
        return EvalRunResult.model_validate(payload)

    async def next_queued_job(self, *, uow: CortexUnitOfWork) -> JobRecord | None:
        jobs = await uow.jobs.list_queued(job_type=JobType.EVAL, limit=1)
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
            job_type=JobType.EVAL,
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
                    error_code="evaluation_worker_lease_expired",
                    error_message="Evaluation worker lease expired and retry budget was exhausted.",
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
            event_type="evaluation.job.started",
            message="Evaluation worker started execution.",
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
        result: EvalRunResult,
    ) -> None:
        state = self._queue_state(job)
        completed_at = utc_now()
        state["status"] = "succeeded"
        state["completed_at"] = self._iso(completed_at)
        state["lease_owner"] = None
        state["lease_expires_at"] = None
        await uow.jobs.update_status(
            job.job_id,
            status=JobStatus.SUCCEEDED,
            finished_at=completed_at,
            deployment_context=self._with_queue_state(job, state),
            result_payload={"eval_result": result.model_dump(mode="json")},
        )
        run = await self.get_run_by_job(uow=uow, job_id=job.job_id)
        run.engine_id = result.engine_id
        run.profile_key = result.profile_key
        run.summary_results = result.summary.model_dump(mode="json")
        run.sample_summary = result.samples.model_dump(mode="json") if result.samples else {}
        run.report_object_id = _artifact_object_id(result, preferred_label="evaluation_report")
        await uow.eval_runs.update(run)
        await uow.eval_run_metrics.replace_for_run(
            run.eval_run_id,
            [
                _metric_record(run.eval_run_id, index, metric)
                for index, metric in enumerate(result.metrics, start=1)
            ],
        )
        await self._append_event(
            uow,
            job=job,
            level="info",
            event_type="evaluation.job.succeeded",
            message="Evaluation worker completed execution.",
            details={"engine_id": result.engine_id, "status": result.status},
        )

    async def record_failed(
        self, *, uow: CortexUnitOfWork, job: JobRecord, error: Exception
    ) -> str:
        error_message = _redact_error_message(str(error) or error.__class__.__name__)
        error_code = getattr(error, "code", None) or "evaluation_worker_failed"
        state = self._queue_state(job)
        state["last_error"] = error_message
        state["last_error_code"] = error_code
        state["lease_owner"] = None
        state["lease_expires_at"] = None
        run = await self.get_run_by_job(uow=uow, job_id=job.job_id)
        run.summary_results = {
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
            await uow.eval_runs.update(run)
            await self._append_event(
                uow,
                job=job,
                level="warning",
                event_type="evaluation.job.retry_scheduled",
                message="Evaluation worker scheduled the job for retry.",
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
        await uow.eval_runs.update(run)
        await self._append_event(
            uow,
            job=job,
            level="error",
            event_type="evaluation.job.failed",
            message="Evaluation worker failed execution.",
            details=state,
        )
        return "failed"

    @staticmethod
    def _accepted(job: JobRecord, request: EvalJobSubmitRequest) -> EvalJobAccepted:
        return EvalJobAccepted(
            job_id=job.job_id,
            job_type=ContractJobType.EVAL,
            status=ContractJobStatus(job.status.value),
            submitted_at=job.submitted_at,
            poll_url=f"/v1/jobs/{job.job_id}",
            result_url=f"/v1/eval/jobs/{job.job_id}/result",
            cancel_url=f"/v1/jobs/{job.job_id}/cancel",
            eval_type=ContractEvalType(request.eval_type.value),
            engine_id=request.engine_id,
            telemetry=TelemetryContext(
                trace_id=job.trace_id,
                span_id=job.span_id,
                request_id=job.request_id,
            ),
        )

    @staticmethod
    async def _validate_request_references(
        *,
        uow: CortexUnitOfWork,
        caller: Any,
        request: EvalSyncRequest,
    ) -> None:
        input_type = request.input.type.strip().lower()
        dataset_id = request.input.dataset_id
        if input_type == "dataset" and not dataset_id:
            raise ValidationError(
                "Evaluation input type `dataset` requires `input.dataset_id`.",
                extra={
                    "field_errors": [
                        {
                            "field": "body.input.dataset_id",
                            "message": "Field required when input.type is `dataset`.",
                        }
                    ]
                },
            )
        if not dataset_id:
            return
        dataset = await uow.datasets.get(dataset_id)
        if dataset is None or dataset.tenant_id != caller.tenant_id:
            raise NotFoundError(
                (
                    f"Evaluation dataset `{dataset_id}` was not found or is not "
                    "accessible for this tenant."
                ),
                extra={
                    "field_errors": [
                        {
                            "field": "body.input.dataset_id",
                            "message": (
                                "Create the dataset first, use an accessible dataset id, "
                                "or provide inline `input.test_cases` / object-backed input."
                            ),
                        }
                    ]
                },
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
        return EvaluationJobControlService._initial_queue_state()

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
        # Bolt ⚡: O(1) DB MAX() query instead of loading up to 1000 records into memory
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


def _metric_record(
    eval_run_id: str, metric_index: int, metric: EvalMetricResult
) -> EvalRunMetricRecord:
    return EvalRunMetricRecord(
        eval_run_id=eval_run_id,
        metric_index=metric_index,
        metric_key=metric.metric_key,
        engine_id=metric.engine_id or "unknown",
        native_metric_key=metric.native_metric_key,
        status=metric.status,
        score=metric.score,
        threshold=metric.threshold,
        unit=metric.unit,
        sample_size=metric.sample_size,
        details=metric.details,
    )


def ensure_evalscope_task_id(
    request: _EvalRequestT,
    job_id: str,
) -> _EvalRequestT:
    """Attach the Cortex job id as EvalScope service task id if absent."""

    if _has_evalscope_task_id(request.engine_options):
        return request
    options = dict(request.engine_options)
    options["evalscope_task_id"] = job_id
    request.engine_options = options
    return request


def _has_evalscope_task_id(engine_options: dict[str, Any]) -> bool:
    for key in ("evalscope_task_id", "task_id", "cortex_job_id", "job_id"):
        value = engine_options.get(key)
        if isinstance(value, str) and value.strip():
            return True
    return False


def _redact_error_message(message: str) -> str:
    return _SECRET_LIKE_PATTERN.sub(r"\1\2<redacted>\4", message)


def _redact_sensitive_value(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if _is_sensitive_key(str(key)):
                redacted[key] = "<redacted>" if item else item
            else:
                redacted[key] = _redact_sensitive_value(item)
        return redacted
    if isinstance(value, list):
        return [_redact_sensitive_value(item) for item in value]
    if isinstance(value, str):
        return _redact_error_message(value)
    return value


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return normalized in {"api_key", "authorization", "access_token", "bearer_token"} or (
        "secret" in normalized or "api_key" in normalized
    )


def _artifact_object_id(result: EvalRunResult, *, preferred_label: str) -> str | None:
    preferred = [
        artifact.object_id
        for artifact in result.artifacts
        if artifact.label == preferred_label and artifact.object_id.startswith("obj_")
    ]
    if preferred:
        return preferred[0]
    for artifact in result.artifacts:
        if artifact.object_id.startswith("obj_"):
            return artifact.object_id
    return None
