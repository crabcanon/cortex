"""Parse worker bootstrap and execution loop."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from time import monotonic

from cortex_common import (
    CortexError,
    CortexSettings,
    load_runtime_config,
    load_settings,
    new_prefixed_id,
)
from cortex_contracts import ParseJobRequest
from cortex_db import (
    CortexUnitOfWork,
    SessionFactory,
    create_database_engine,
    create_session_factory,
)
from cortex_domain import JobRecord
from cortex_parse import (
    ParseJobControlService,
    ParseService,
    build_parse_service,
    prepare_crawl4ai_playwright_runtime,
)
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass(slots=True)
class WorkerCaller:
    subject: str
    tenant_id: str
    actor_id: str | None = None


@dataclass(slots=True)
class ParseWorkerRunResult:
    status: str
    job_id: str | None = None
    document_id: str | None = None
    message: str | None = None


@dataclass(slots=True)
class ParseWorkerConfig:
    worker_id: str
    lease_seconds: int = 300
    heartbeat_interval_seconds: int = 30
    execution_timeout_seconds: int | None = None
    supported_engine_keys: set[str] | None = None

    @classmethod
    def create(cls, worker_id: str | None = None) -> ParseWorkerConfig:
        lease_seconds = _int_env("CORTEX_PARSE_WORKER_LEASE_SECONDS", 300)
        heartbeat_interval_seconds = _int_env(
            "CORTEX_PARSE_WORKER_HEARTBEAT_INTERVAL_SECONDS",
            min(30, max(5, lease_seconds // 3)),
        )
        return cls(
            worker_id=worker_id or new_prefixed_id("pworker"),
            lease_seconds=lease_seconds,
            heartbeat_interval_seconds=min(heartbeat_interval_seconds, lease_seconds),
            execution_timeout_seconds=_optional_int_env(
                "CORTEX_PARSE_WORKER_EXECUTION_TIMEOUT_SECONDS"
            ),
            supported_engine_keys=_parse_engine_key_set(
                os.getenv("CORTEX_PARSE_WORKER_ENGINE_KEYS")
            ),
        )


class ParseWorker:
    """Poll and execute queued parse jobs."""

    def __init__(
        self,
        *,
        session_factory: SessionFactory,
        parse_service: ParseService,
        job_service: ParseJobControlService | None = None,
        config: ParseWorkerConfig | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._parse_service = parse_service
        self._job_service = job_service or ParseJobControlService()
        self._config = config or ParseWorkerConfig.create()

    async def run_once(self) -> ParseWorkerRunResult:
        async with CortexUnitOfWork(self._session_factory) as uow:
            job = await self._job_service.claim_next_job(
                uow=uow,
                worker_id=self._config.worker_id,
                lease_seconds=self._config.lease_seconds,
                supported_engine_keys=self._config.supported_engine_keys,
            )
            if job is None:
                return ParseWorkerRunResult(status="idle", message="No queued parse jobs.")
            request = ParseJobRequest.model_validate(job.request_payload)
            caller = self._caller(job)
            timeout_seconds = self._execution_timeout_seconds(job, request)

        stop_heartbeat = asyncio.Event()
        heartbeat_task = asyncio.create_task(
            self._heartbeat_until_stopped(job.job_id, stop_heartbeat)
        )
        try:
            async with CortexUnitOfWork(self._session_factory) as uow:
                current_job = await uow.jobs.get(job.job_id)
                if current_job is None:
                    return ParseWorkerRunResult(
                        status="failed",
                        job_id=job.job_id,
                        message="Claimed parse job disappeared before execution.",
                    )
                started_at = monotonic()
                try:
                    result = await asyncio.wait_for(
                        self._parse_service.execute_existing_job(
                            uow=uow,
                            caller=caller,
                            job=current_job,
                            request=request,
                        ),
                        timeout=timeout_seconds,
                    )
                except TimeoutError as exc:
                    if _elapsed_reached_timeout(started_at, timeout_seconds):
                        raise CortexError(
                            code="parse_worker_timeout",
                            detail=(
                                f"Parse job exceeded timeout budget of {timeout_seconds} seconds."
                            ),
                            status_code=504,
                        ) from exc
                    raise
                await self._job_service.record_succeeded(
                    uow=uow,
                    job=current_job,
                    result=result,
                )
                return ParseWorkerRunResult(
                    status="succeeded",
                    job_id=job.job_id,
                    document_id=result.document.document_id,
                )
        except Exception as exc:
            return await self._record_failure(job.job_id, exc)
        finally:
            stop_heartbeat.set()
            await self._await_heartbeat_stop(heartbeat_task)

    async def _record_failure(self, job_id: str, error: Exception) -> ParseWorkerRunResult:
        async with CortexUnitOfWork(self._session_factory) as uow:
            latest = await uow.jobs.get(job_id)
            if latest is None:
                return ParseWorkerRunResult(status="failed", job_id=job_id, message=str(error))
            transition = await self._job_service.record_failed(uow=uow, job=latest, error=error)
            return ParseWorkerRunResult(status=transition, job_id=job_id, message=str(error))

    async def _heartbeat_until_stopped(
        self,
        job_id: str,
        stop_heartbeat: asyncio.Event,
    ) -> None:
        while not stop_heartbeat.is_set():
            try:
                await asyncio.wait_for(
                    stop_heartbeat.wait(),
                    timeout=self._config.heartbeat_interval_seconds,
                )
            except TimeoutError:
                async with CortexUnitOfWork(self._session_factory) as uow:
                    await self._job_service.refresh_heartbeat(
                        uow=uow,
                        job_id=job_id,
                        worker_id=self._config.worker_id,
                        lease_seconds=self._config.lease_seconds,
                    )

    @staticmethod
    async def _await_heartbeat_stop(task: asyncio.Task[None]) -> None:
        try:
            await task
        except Exception:
            return

    def _execution_timeout_seconds(
        self,
        job: JobRecord,
        request: ParseJobRequest,
    ) -> int:
        if self._config.execution_timeout_seconds is not None:
            return self._config.execution_timeout_seconds
        queue_state = job.deployment_context.get("parse_worker")
        if isinstance(queue_state, dict):
            timeout_seconds = queue_state.get("execution_timeout_seconds")
            if isinstance(timeout_seconds, int | float):
                return max(1, int(timeout_seconds))
        return max(1, request.timeout_seconds)

    @staticmethod
    def _caller(job: JobRecord) -> WorkerCaller:
        subject = job.submitted_by or "parse-worker"
        return WorkerCaller(
            subject=subject,
            actor_id=job.submitted_by,
            tenant_id=job.tenant_id,
        )


@dataclass(slots=True)
class ParseWorkerRuntime:
    worker: ParseWorker
    engine: AsyncEngine

    async def close(self) -> None:
        await self.engine.dispose()


def build_worker(settings: CortexSettings | None = None) -> ParseWorkerRuntime:
    loaded_settings = settings or load_settings()
    runtime_config = load_runtime_config(loaded_settings.runtime.path)
    prepare_crawl4ai_playwright_runtime(runtime_config)
    engine = create_database_engine(loaded_settings.database.dsn)
    session_factory = create_session_factory(engine)
    worker = ParseWorker(
        session_factory=session_factory,
        parse_service=build_parse_service(loaded_settings.parse, runtime_config),
        config=ParseWorkerConfig.create(),
    )
    return ParseWorkerRuntime(worker=worker, engine=engine)


def bootstrap_message() -> str:
    """Return a stable bootstrap message for smoke tests."""
    return "cortex parse worker bootstrap ready"


def _parse_engine_key_set(value: str | None) -> set[str] | None:
    if value is None:
        return None
    keys = {item.strip().lower() for item in value.split(",") if item.strip()}
    return keys or None


def _int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return max(1, default)
    try:
        return max(1, int(raw_value))
    except ValueError:
        return max(1, default)


def _optional_int_env(name: str) -> int | None:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return None
    try:
        return max(1, int(raw_value))
    except ValueError:
        return None


def _elapsed_reached_timeout(started_at: float, timeout_seconds: int) -> bool:
    return monotonic() - started_at >= max(0.0, float(timeout_seconds) - 1.0)
