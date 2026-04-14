"""Knowledge worker bootstrap and execution loop."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from cortex_common import CortexError, CortexSettings, load_settings, new_prefixed_id
from cortex_db import (
    CortexUnitOfWork,
    SessionFactory,
    create_database_engine,
    create_session_factory,
)
from cortex_domain import JobRecord
from cortex_knowledge import (
    KnowledgeDatasetService,
    KnowledgeJobControlService,
    KnowledgeOperationService,
    build_cognee_runtime,
)
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass(slots=True)
class WorkerCaller:
    subject: str
    tenant_id: str
    actor_id: str | None = None


@dataclass(slots=True)
class KnowledgeWorkerRunResult:
    status: str
    job_id: str | None = None
    knowledge_run_id: str | None = None
    dataset_id: str | None = None
    message: str | None = None


@dataclass(slots=True)
class KnowledgeWorkerConfig:
    worker_id: str
    lease_seconds: int = 60
    heartbeat_interval_seconds: int = 15

    @classmethod
    def create(cls, worker_id: str | None = None) -> KnowledgeWorkerConfig:
        return cls(worker_id=worker_id or new_prefixed_id("kworker"))


class KnowledgeWorker:
    """Poll and execute queued Knowledge jobs."""

    def __init__(
        self,
        *,
        session_factory: SessionFactory,
        operation_service: KnowledgeOperationService,
        job_service: KnowledgeJobControlService | None = None,
        config: KnowledgeWorkerConfig | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._operation_service = operation_service
        self._job_service = job_service or KnowledgeJobControlService()
        self._config = config or KnowledgeWorkerConfig.create()

    async def run_once(self) -> KnowledgeWorkerRunResult:
        async with CortexUnitOfWork(self._session_factory) as uow:
            job = await self._job_service.claim_next_job(
                uow=uow,
                worker_id=self._config.worker_id,
                lease_seconds=self._config.lease_seconds,
            )
            if job is None:
                return KnowledgeWorkerRunResult(
                    status="idle",
                    message="No queued knowledge jobs.",
                )
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
                    return KnowledgeWorkerRunResult(
                        status="failed",
                        job_id=job.job_id,
                        message="Claimed knowledge job disappeared before execution.",
                    )
                result = await asyncio.wait_for(
                    self._operation_service.execute_job(
                        uow=uow,
                        job=current_job,
                    ),
                    timeout=timeout_seconds,
                )
                await self._job_service.record_succeeded(
                    uow=uow,
                    job=current_job,
                    result_summary=result.result_summary,
                )
                return KnowledgeWorkerRunResult(
                    status="succeeded",
                    job_id=current_job.job_id,
                    knowledge_run_id=result.knowledge_run_id,
                    dataset_id=result.dataset_id,
                )
        except TimeoutError:
            error = CortexError(
                code="knowledge_worker_timeout",
                detail=(
                    "Knowledge job exceeded timeout budget of "
                    f"{timeout_seconds} seconds."
                ),
                status_code=504,
            )
            return await self._record_failure(job.job_id, error)
        except Exception as exc:
            return await self._record_failure(job.job_id, exc)
        finally:
            stop_heartbeat.set()
            await self._await_heartbeat_stop(heartbeat_task)

    async def _record_failure(
        self,
        job_id: str,
        error: Exception,
    ) -> KnowledgeWorkerRunResult:
        async with CortexUnitOfWork(self._session_factory) as uow:
            latest = await uow.jobs.get(job_id)
            if latest is None:
                return KnowledgeWorkerRunResult(
                    status="failed",
                    job_id=job_id,
                    message=str(error),
                )
            transition = await self._job_service.record_failed(
                uow=uow,
                job=latest,
                error=error,
            )
            run = await self._job_service.get_run_by_job(uow=uow, job_id=job_id)
            return KnowledgeWorkerRunResult(
                status=transition,
                job_id=job_id,
                knowledge_run_id=run.knowledge_run_id,
                dataset_id=run.dataset_id,
                message=str(error),
            )

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

    @staticmethod
    def _execution_timeout_seconds(job: JobRecord) -> int:
        queue_state = job.deployment_context.get("knowledge_worker")
        if not isinstance(queue_state, dict):
            return 900
        timeout_seconds = queue_state.get("execution_timeout_seconds")
        if isinstance(timeout_seconds, int | float):
            return max(1, int(timeout_seconds))
        return 900

    @staticmethod
    def _caller(job: JobRecord) -> WorkerCaller:
        subject = job.submitted_by or "knowledge-worker"
        return WorkerCaller(
            subject=subject,
            actor_id=job.submitted_by,
            tenant_id=job.tenant_id,
        )


@dataclass(slots=True)
class KnowledgeWorkerRuntime:
    worker: KnowledgeWorker
    engine: AsyncEngine

    async def close(self) -> None:
        await self.engine.dispose()


def build_worker(settings: CortexSettings | None = None) -> KnowledgeWorkerRuntime:
    loaded_settings = settings or load_settings()
    engine = create_database_engine(loaded_settings.database.dsn)
    session_factory = create_session_factory(engine)
    runtime = build_cognee_runtime(loaded_settings.cognee)
    dataset_service = KnowledgeDatasetService(runtime)
    worker = KnowledgeWorker(
        session_factory=session_factory,
        operation_service=KnowledgeOperationService(runtime, dataset_service),
        config=KnowledgeWorkerConfig.create(),
    )
    return KnowledgeWorkerRuntime(worker=worker, engine=engine)


def bootstrap_message() -> str:
    """Return a stable bootstrap message for smoke tests."""
    return "cortex knowledge worker bootstrap ready"
