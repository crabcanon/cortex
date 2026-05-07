"""Synthesis worker bootstrap and execution loop."""

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
from cortex_contracts import SynthesisJobSubmitRequest
from cortex_db import (
    CortexUnitOfWork,
    SessionFactory,
    create_database_engine,
    create_session_factory,
)
from cortex_domain import JobRecord
from cortex_storage import StorageService
from cortex_synthesis import SynthesisJobControlService, SynthesisService, build_synthesis_service
from sqlalchemy.ext.asyncio import AsyncEngine

from .artifacts import WorkerStorageCaller, persist_synthesis_output
from .hydration import hydrate_synthesis_request


@dataclass(slots=True)
class SynthesisWorkerRunResult:
    status: str
    job_id: str | None = None
    synthesis_run_id: str | None = None
    message: str | None = None


@dataclass(slots=True)
class SynthesisWorkerConfig:
    worker_id: str
    lease_seconds: int = 300
    heartbeat_interval_seconds: int = 30

    @classmethod
    def create(cls, worker_id: str | None = None) -> SynthesisWorkerConfig:
        lease_seconds = _int_env("CORTEX_SYNTHESIS_WORKER_LEASE_SECONDS", 300)
        heartbeat_interval_seconds = _int_env(
            "CORTEX_SYNTHESIS_WORKER_HEARTBEAT_INTERVAL_SECONDS",
            min(30, max(5, lease_seconds // 3)),
        )
        return cls(
            worker_id=worker_id or new_prefixed_id("sworker"),
            lease_seconds=lease_seconds,
            heartbeat_interval_seconds=min(heartbeat_interval_seconds, lease_seconds),
        )


class SynthesisWorker:
    def __init__(
        self,
        *,
        session_factory: SessionFactory,
        synthesis_service: SynthesisService,
        job_service: SynthesisJobControlService | None = None,
        storage_service: StorageService | None = None,
        config: SynthesisWorkerConfig | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._synthesis_service = synthesis_service
        self._job_service = job_service or SynthesisJobControlService()
        self._storage_service = storage_service
        self._config = config or SynthesisWorkerConfig.create()

    async def run_once(self) -> SynthesisWorkerRunResult:
        async with CortexUnitOfWork(self._session_factory) as uow:
            job = await self._job_service.claim_next_job(
                uow=uow,
                worker_id=self._config.worker_id,
                lease_seconds=self._config.lease_seconds,
            )
            if job is None:
                return SynthesisWorkerRunResult(status="idle", message="No queued synthesis jobs.")
            run = await self._job_service.get_run_by_job(uow=uow, job_id=job.job_id)
            timeout_seconds = self._execution_timeout_seconds(job)
            del run

        stop_heartbeat = asyncio.Event()
        heartbeat_task = asyncio.create_task(
            self._heartbeat_until_stopped(job.job_id, stop_heartbeat)
        )
        try:
            async with CortexUnitOfWork(self._session_factory) as uow:
                current_job = await uow.jobs.get(job.job_id)
                if current_job is None:
                    return SynthesisWorkerRunResult(
                        status="failed",
                        job_id=job.job_id,
                        message="Claimed synthesis job disappeared before execution.",
                    )
                request = SynthesisJobSubmitRequest.model_validate(current_job.request_payload)
                request = await hydrate_synthesis_request(
                    uow=uow,
                    storage_service=self._storage_service,
                    request=request,
                )
                started_at = monotonic()
                try:
                    result = await asyncio.wait_for(
                        self._synthesis_service.run(request),
                        timeout=timeout_seconds,
                    )
                except TimeoutError as exc:
                    if _elapsed_reached_timeout(started_at, timeout_seconds):
                        raise CortexError(
                            code="synthesis_worker_timeout",
                            detail=(
                                "Synthesis job exceeded timeout budget of "
                                f"{timeout_seconds} seconds."
                            ),
                            status_code=504,
                        ) from exc
                    raise
                result.job_id = current_job.job_id
                run = await self._job_service.get_run_by_job(uow=uow, job_id=current_job.job_id)
                result.synthesis_run_id = run.synthesis_run_id
                result = await persist_synthesis_output(
                    uow=uow,
                    storage_service=self._storage_service,
                    caller=WorkerStorageCaller(
                        tenant_id=current_job.tenant_id,
                        subject=current_job.submitted_by or self._config.worker_id,
                        actor_id=current_job.submitted_by,
                    ),
                    request=request,
                    result=result,
                )
                await self._job_service.record_succeeded(uow=uow, job=current_job, result=result)
                return SynthesisWorkerRunResult(
                    status="succeeded",
                    job_id=current_job.job_id,
                    synthesis_run_id=run.synthesis_run_id,
                )
        except Exception as exc:
            return await self._record_failure(job.job_id, exc)
        finally:
            stop_heartbeat.set()
            await self._await_heartbeat_stop(heartbeat_task)

    async def _record_failure(self, job_id: str, error: Exception) -> SynthesisWorkerRunResult:
        async with CortexUnitOfWork(self._session_factory) as uow:
            latest = await uow.jobs.get(job_id)
            if latest is None:
                return SynthesisWorkerRunResult(status="failed", job_id=job_id, message=str(error))
            transition = await self._job_service.record_failed(uow=uow, job=latest, error=error)
            run = await self._job_service.get_run_by_job(uow=uow, job_id=job_id)
            return SynthesisWorkerRunResult(
                status=transition,
                job_id=job_id,
                synthesis_run_id=run.synthesis_run_id,
                message=str(error),
            )

    async def _heartbeat_until_stopped(self, job_id: str, stop_heartbeat: asyncio.Event) -> None:
        while not stop_heartbeat.is_set():
            try:
                await asyncio.wait_for(
                    stop_heartbeat.wait(), timeout=self._config.heartbeat_interval_seconds
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

    @staticmethod
    def _execution_timeout_seconds(job: JobRecord) -> int:
        queue_state = job.deployment_context.get("synthesis_worker")
        if not isinstance(queue_state, dict):
            return 1800
        timeout_seconds = queue_state.get("execution_timeout_seconds")
        if isinstance(timeout_seconds, int | float):
            return max(1, int(timeout_seconds))
        return 1800


@dataclass(slots=True)
class SynthesisWorkerRuntime:
    worker: SynthesisWorker
    engine: AsyncEngine

    async def close(self) -> None:
        await self.engine.dispose()


def build_worker(settings: CortexSettings | None = None) -> SynthesisWorkerRuntime:
    loaded_settings = settings or load_settings()
    runtime_config = load_runtime_config(loaded_settings.runtime.path)
    engine = create_database_engine(loaded_settings.database.dsn)
    session_factory = create_session_factory(engine)
    worker = SynthesisWorker(
        session_factory=session_factory,
        synthesis_service=build_synthesis_service(loaded_settings.synthesis, runtime_config),
        storage_service=StorageService(loaded_settings.s3),
        config=SynthesisWorkerConfig.create(),
    )
    return SynthesisWorkerRuntime(worker=worker, engine=engine)


def bootstrap_message() -> str:
    return "cortex synthesis worker bootstrap ready"


def _int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return max(1, default)
    try:
        return max(1, int(raw_value))
    except ValueError:
        return max(1, default)


def _elapsed_reached_timeout(started_at: float, timeout_seconds: int) -> bool:
    return monotonic() - started_at >= max(0.0, float(timeout_seconds) - 1.0)
