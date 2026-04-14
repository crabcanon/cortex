"""Docker-backed integration tests for the local runtime stack."""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import httpx
import psycopg
import pytest
from cortex_common import S3Settings
from cortex_contracts import (
    AccessLevel as ContractAccessLevel,
)
from cortex_contracts import (
    AccessPolicy,
    AddJobRequest,
    DownloadDisposition,
    KnowledgeDatasetCreateRequest,
    KnowledgeInput,
    KnowledgeInputType,
    ParseEngineDeploymentMode,
    ParseEngineDescriptor,
    ParseEngineStatus,
    ParseInputKind,
    ParseJobRequest,
    ParserSelection,
    ParseSource,
    StorageUploadCompleteRequest,
    StorageUploadCreateRequest,
)
from cortex_db import CortexUnitOfWork, create_database_engine, create_session_factory
from cortex_db.cli import main as db_migrate_main
from cortex_domain import JobStatus, TenantRecord
from cortex_knowledge import (
    CogneeRuntimeDescriptor,
    KnowledgeDatasetService,
    KnowledgeJobControlService,
    KnowledgeOperationService,
)
from cortex_parse import (
    EngineExecutionContext,
    EngineExecutionResult,
    ParseEngineProtocol,
    ParseEngineRegistry,
    ParseJobControlService,
    ParseProfileLoader,
    ParseService,
)
from cortex_storage import StorageService
from cortex_worker_knowledge import KnowledgeWorker, KnowledgeWorkerConfig
from cortex_worker_parse import ParseWorker, ParseWorkerConfig
from psycopg import sql
from sqlalchemy import create_engine, inspect

pytestmark = pytest.mark.runtime_stack


@dataclass(slots=True)
class _RuntimeStackConfig:
    postgres_host: str
    postgres_port: int
    postgres_user: str
    postgres_password: str
    postgres_admin_db: str
    minio_endpoint: str
    minio_bucket: str
    minio_access_key: str
    minio_secret_key: str

    @property
    def admin_sync_dsn(self) -> str:
        return (
            "postgresql+psycopg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_admin_db}"
        )

    @property
    def admin_driverless_dsn(self) -> str:
        return (
            "postgresql://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_admin_db}"
        )

    def sync_dsn(self, database_name: str) -> str:
        return (
            "postgresql+psycopg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{database_name}"
        )

    def async_dsn(self, database_name: str) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{database_name}"
        )


def _stack_enabled() -> bool:
    return os.getenv("CORTEX_RUNTIME_STACK", "").strip() == "1"


if not _stack_enabled():
    pytest.skip(
        "runtime stack tests require CORTEX_RUNTIME_STACK=1",
        allow_module_level=True,
    )


def _load_stack_config() -> _RuntimeStackConfig:
    return _RuntimeStackConfig(
        postgres_host=os.getenv("CORTEX_STACK_POSTGRES_HOST", "127.0.0.1"),
        postgres_port=int(os.getenv("CORTEX_STACK_POSTGRES_PORT", "5432")),
        postgres_user=os.getenv("CORTEX_STACK_POSTGRES_USER", "cortex"),
        postgres_password=os.getenv("CORTEX_STACK_POSTGRES_PASSWORD", "cortex"),
        postgres_admin_db=os.getenv("CORTEX_STACK_POSTGRES_DB", "cortex"),
        minio_endpoint=os.getenv("CORTEX_STACK_MINIO_ENDPOINT", "http://127.0.0.1:9000"),
        minio_bucket=os.getenv("CORTEX_STACK_MINIO_BUCKET", "cortex-local"),
        minio_access_key=os.getenv("CORTEX_STACK_MINIO_ACCESS_KEY", "minioadmin"),
        minio_secret_key=os.getenv("CORTEX_STACK_MINIO_SECRET_KEY", "minioadmin"),
    )


@contextmanager
def _temporary_postgres_database(prefix: str) -> Iterator[tuple[str, str]]:
    config = _load_stack_config()
    database_name = f"{prefix}_{time.time_ns()}".replace("-", "_")
    with psycopg.connect(config.admin_driverless_dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
            )
    try:
        yield config.sync_dsn(database_name), config.async_dsn(database_name)
    finally:
        with psycopg.connect(config.admin_driverless_dsn, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s AND pid <> pg_backend_pid()
                    """,
                    (database_name,),
                )
                cur.execute(
                    sql.SQL("DROP DATABASE IF EXISTS {}").format(
                        sql.Identifier(database_name)
                    )
                )


def _case_dir(name: str) -> Path:
    root = Path("runtime-test-data")
    root.mkdir(parents=True, exist_ok=True)
    case_dir = root / f"{name}-{time.time_ns()}"
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir


class _RuntimeParseEngine(ParseEngineProtocol):
    @property
    def descriptor(self) -> ParseEngineDescriptor:
        return ParseEngineDescriptor(
            engine_key="runtime_test_engine",
            display_name="Runtime Test Engine",
            engine_family="test",
            deployment_mode=ParseEngineDeploymentMode.LOCAL,
            status=ParseEngineStatus.ACTIVE,
            supported_source_types=["url"],
            supported_formats=["text/html"],
            capabilities=["markdown"],
        )

    async def execute(self, context: EngineExecutionContext) -> EngineExecutionResult:
        del context
        return EngineExecutionResult(
            markdown="# Runtime Parse\n\nHello from PostgreSQL.",
            source_format="text/html",
            detected_mime_type="text/html",
            metadata={
                "title": "Runtime Parse",
                "language": "en",
                "category_tags": ["runtime"],
                "labels": ["postgres"],
            },
            final_url="https://example.com/runtime",
            http_status=200,
            content_length_bytes=256,
            parser_version="runtime-test-1.0",
            engine_payload_summary={"mode": "runtime"},
        )


class _RuntimeKnowledgeRuntime:
    def __init__(self) -> None:
        self.calls: list[str] = []

    @property
    def descriptor(self) -> CogneeRuntimeDescriptor:
        return CogneeRuntimeDescriptor(
            provider_key="runtime_fake_cognee",
            display_name="Runtime Fake Cognee",
            status="active",
            capabilities=["add"],
            version="runtime-1.0",
        )

    async def add(self, *, dataset: str, payload: dict[str, object]) -> dict[str, object]:
        self.calls.append("add")
        inputs = payload.get("inputs")
        item_count = len(inputs) if isinstance(inputs, list) else 0
        return {
            "dataset": dataset,
            "accepted_inputs": item_count,
            "counters": {"objects": 1, "documents": 1},
        }

    async def cognify(self, *, dataset: str, payload: dict[str, object]) -> dict[str, object]:
        raise AssertionError(f"unexpected cognify call for dataset {dataset}: {payload}")

    async def memify(self, *, dataset: str, payload: dict[str, object]) -> dict[str, object]:
        raise AssertionError(f"unexpected memify call for dataset {dataset}: {payload}")

    async def search(self, *, payload: dict[str, object]) -> dict[str, object]:
        raise AssertionError(f"unexpected search call: {payload}")


def _build_parse_service(profiles_dir: Path) -> ParseService:
    registry = ParseEngineRegistry()
    registry.register(_RuntimeParseEngine())
    return ParseService(
        registry=registry,
        profile_loader=ParseProfileLoader(profiles_dir),
        default_profile_ref="runtime_profile",
    )


def test_postgres_migration_and_repository_round_trip() -> None:
    with _temporary_postgres_database("cortex_it_repo") as (sync_dsn, async_dsn):
        db_migrate_main(["upgrade", "head", "--db-url", sync_dsn])

        engine = create_engine(sync_dsn)
        try:
            tables = set(inspect(engine).get_table_names())
        finally:
            engine.dispose()

        assert {
            "tenants",
            "actors",
            "objects",
            "datasets",
            "jobs",
            "parse_runs",
            "knowledge_runs",
            "search_requests",
        }.issubset(tables)

        async def _round_trip() -> None:
            async_engine = create_database_engine(async_dsn)
            session_factory = create_session_factory(async_engine)
            try:
                async with CortexUnitOfWork(session_factory) as uow:
                    tenant = await uow.tenants.add(
                        TenantRecord(
                            tenant_id="tenant_pg",
                            tenant_key="tenant_pg",
                            display_name="Tenant PG",
                            status="active",
                        )
                    )
                    loaded = await uow.tenants.get(tenant.tenant_id)
                    assert loaded is not None
                    assert loaded.tenant_key == "tenant_pg"
            finally:
                await async_engine.dispose()

        asyncio.run(_round_trip())


def test_minio_storage_presigned_upload_download_round_trip() -> None:
    config = _load_stack_config()
    with _temporary_postgres_database("cortex_it_storage") as (sync_dsn, async_dsn):
        db_migrate_main(["upgrade", "head", "--db-url", sync_dsn])

        async def _run() -> None:
            async_engine = create_database_engine(async_dsn)
            session_factory = create_session_factory(async_engine)
            try:
                service = StorageService(
                    S3Settings.model_validate(
                        {
                            "endpoint": config.minio_endpoint,
                            "region": "us-east-1",
                            "bucket": config.minio_bucket,
                            "access_key": config.minio_access_key,
                            "secret_key": config.minio_secret_key,
                            "force_path_style": True,
                            "auto_create_bucket": True,
                        }
                    )
                )
                caller = SimpleNamespace(
                    tenant_id="tenant_runtime_storage",
                    actor_id="alice",
                    subject="alice",
                )
                payload = b"hello from minio runtime stack"

                async with CortexUnitOfWork(session_factory) as uow:
                    session = await service.create_upload_session(
                        uow=uow,
                        caller=caller,
                        request=StorageUploadCreateRequest(
                            filename="runtime.txt",
                            content_type="text/plain",
                            size_bytes=len(payload),
                            access_policy=AccessPolicy(
                                access_level=ContractAccessLevel.TENANT_PRIVATE
                            ),
                        ),
                    )

                assert session.single_part is not None
                put_response = httpx.put(
                    session.single_part.url,
                    content=payload,
                    headers=session.single_part.headers,
                    timeout=30,
                )
                assert put_response.status_code in {200, 204}

                async with CortexUnitOfWork(session_factory) as uow:
                    stored = await service.complete_upload_session(
                        uow=uow,
                        upload_id=session.upload_id,
                        request=StorageUploadCompleteRequest(),
                    )
                    download = await service.create_download_url(
                        uow=uow,
                        object_id=stored.object_id,
                        ttl_seconds=300,
                        disposition=DownloadDisposition.ATTACHMENT,
                    )

                get_response = httpx.get(download.url, headers=download.headers, timeout=30)
                assert get_response.status_code == 200
                assert get_response.content == payload
            finally:
                await async_engine.dispose()

        asyncio.run(_run())


def test_parse_worker_executes_against_postgres() -> None:
    case_dir = _case_dir("runtime-parse-postgres")
    profiles_dir = case_dir / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    (profiles_dir / "runtime_profile.yaml").write_text(
        "\n".join(
            [
                "profile_ref: runtime_profile",
                "display_name: Runtime Profile",
                "routing_mode: ordered_fallback",
                "preferred_engine_key: runtime_test_engine",
                "allowed_engines: [runtime_test_engine]",
            ]
        ),
        encoding="utf-8",
    )

    with _temporary_postgres_database("cortex_it_parse") as (sync_dsn, async_dsn):
        db_migrate_main(["upgrade", "head", "--db-url", sync_dsn])

        async def _run() -> None:
            async_engine = create_database_engine(async_dsn)
            session_factory = create_session_factory(async_engine)
            try:
                caller = SimpleNamespace(
                    tenant_id="tenant_runtime_parse",
                    actor_id="alice",
                    subject="alice",
                )
                job_service = ParseJobControlService()
                async with CortexUnitOfWork(session_factory) as uow:
                    accepted = await job_service.submit(
                        uow=uow,
                        caller=caller,
                        request=ParseJobRequest(
                            source=ParseSource(
                                input_kind=ParseInputKind.URL,
                                url="https://example.com/runtime-parse",
                                expected_content_type="text/html",
                            ),
                            parser=ParserSelection(profile_ref="runtime_profile"),
                        ),
                        request_id="req-runtime-parse",
                    )

                worker = ParseWorker(
                    session_factory=session_factory,
                    parse_service=_build_parse_service(profiles_dir),
                    config=ParseWorkerConfig(worker_id="runtime-parse-worker", lease_seconds=30),
                )
                result = await worker.run_once()
                assert result.status == "succeeded"
                assert result.job_id == accepted.job_id

                async with CortexUnitOfWork(session_factory) as uow:
                    job = await uow.jobs.get(accepted.job_id)
                    assert job is not None
                    assert job.status is JobStatus.SUCCEEDED
                    parse_result = await job_service.get_completed_result(
                        uow=uow,
                        job_id=accepted.job_id,
                    )
                    assert parse_result is not None
                    assert parse_result.document.title == "Runtime Parse"
            finally:
                await async_engine.dispose()

        asyncio.run(_run())


def test_knowledge_worker_executes_against_postgres() -> None:
    runtime = _RuntimeKnowledgeRuntime()

    with _temporary_postgres_database("cortex_it_knowledge") as (sync_dsn, async_dsn):
        db_migrate_main(["upgrade", "head", "--db-url", sync_dsn])

        async def _run() -> None:
            async_engine = create_database_engine(async_dsn)
            session_factory = create_session_factory(async_engine)
            try:
                dataset_service = KnowledgeDatasetService(runtime)
                job_service = KnowledgeJobControlService()
                operation_service = KnowledgeOperationService(runtime, dataset_service)
                caller = SimpleNamespace(
                    tenant_id="tenant_runtime_knowledge",
                    actor_id="alice",
                    subject="alice",
                )

                async with CortexUnitOfWork(session_factory) as uow:
                    dataset = await dataset_service.create_dataset(
                        uow=uow,
                        caller=caller,
                        request=KnowledgeDatasetCreateRequest(
                            dataset_key="runtime_docs",
                            display_name="Runtime Docs",
                            access_policy=AccessPolicy(
                                access_level=ContractAccessLevel.TENANT_SHARED
                            ),
                        ),
                    )
                    dataset_record = await dataset_service.resolve_dataset(
                        uow=uow,
                        tenant_id=caller.tenant_id,
                        dataset_id=dataset.dataset_id,
                    )
                    accepted = await job_service.submit_add(
                        uow=uow,
                        caller=caller,
                        dataset=dataset_record,
                        request=AddJobRequest(
                            dataset_id=dataset.dataset_id,
                            inputs=[
                                KnowledgeInput(
                                    input_type=KnowledgeInputType.TEXT,
                                    text="runtime knowledge note",
                                )
                            ],
                        ),
                        request_id="req-runtime-knowledge",
                    )

                worker = KnowledgeWorker(
                    session_factory=session_factory,
                    operation_service=operation_service,
                    config=KnowledgeWorkerConfig(
                        worker_id="runtime-knowledge-worker",
                        lease_seconds=30,
                    ),
                )
                result = await worker.run_once()
                assert result.status == "succeeded"
                assert result.job_id == accepted.job_id

                async with CortexUnitOfWork(session_factory) as uow:
                    job = await uow.jobs.get(accepted.job_id)
                    run = await uow.knowledge_runs.get_by_job(accepted.job_id)
                    refreshed_dataset = await uow.datasets.get(dataset.dataset_id)
                    assert job is not None
                    assert job.status is JobStatus.SUCCEEDED
                    assert run is not None
                    assert run.result_summary["items_added"] == 1
                    assert refreshed_dataset is not None
                    assert refreshed_dataset.metadata["counters"]["documents"] == 1
                    assert runtime.calls == ["add"]
            finally:
                await async_engine.dispose()

        asyncio.run(_run())
