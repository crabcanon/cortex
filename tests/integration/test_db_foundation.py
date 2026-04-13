"""Integration tests for the Phase C database foundation."""

import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from cortex_db import CortexUnitOfWork, create_database_engine, create_session_factory
from cortex_db.cli import main as db_migrate_main
from cortex_domain import (
    AccessLevel,
    ActorRecord,
    AuthorizationDecisionRecord,
    DatasetRecord,
    DecisionEffect,
    DocumentRecord,
    JobRecord,
    JobStatus,
    JobType,
    ObjectRecord,
    SourceType,
    StorageBucketRecord,
    TenantRecord,
)
from sqlalchemy import create_engine, inspect


def _case_db_path(name: str) -> Path:
    root = Path("runtime-test-data")
    root.mkdir(parents=True, exist_ok=True)
    case_dir = root / f"{name}-{time.time_ns()}"
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir / "cortex.db"


def _sync_sqlite_url(db_path: Path) -> str:
    return f"sqlite:///{db_path.as_posix()}"


def _async_sqlite_url(db_path: Path) -> str:
    return f"sqlite+aiosqlite:///{db_path.as_posix()}"


def test_baseline_migration_creates_expected_tables() -> None:
    db_path = _case_db_path("baseline")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])

    engine = create_engine(_sync_sqlite_url(db_path))
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    assert {
        "tenants",
        "actors",
        "permissions",
        "storage_buckets",
        "objects",
        "documents",
        "datasets",
        "jobs",
        "authorization_decisions",
        "parse_runs",
        "knowledge_runs",
        "search_requests",
    }.issubset(tables)


@pytest.mark.asyncio
async def test_unit_of_work_and_repositories_round_trip() -> None:
    db_path = _case_db_path("repositories")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])

    engine = create_database_engine(_async_sqlite_url(db_path))
    session_factory = create_session_factory(engine)

    try:
        async with CortexUnitOfWork(session_factory) as uow:
            tenant = await uow.tenants.add(
                TenantRecord(
                    tenant_id="tenant_001",
                    tenant_key="alpha",
                    display_name="Alpha",
                    status="active",
                )
            )
            actor = await uow.actors.add(
                ActorRecord(
                    actor_id="actor_001",
                    tenant_id=tenant.tenant_id,
                    actor_type="user",
                    actor_ref="alice@example.com",
                    display_name="Alice",
                )
            )
            await uow.permissions.add(
                permission_key="storage:download",
                permission_kind="functional",
                resource_type="object",
                action_name="download",
            )
            bucket = await uow.buckets.add(
                StorageBucketRecord(
                    bucket_id="bucket_001",
                    tenant_id=tenant.tenant_id,
                    bucket_name="cortex-alpha",
                    is_default=True,
                )
            )
            stored_object = await uow.objects.add(
                ObjectRecord(
                    object_id="obj_001",
                    tenant_id=tenant.tenant_id,
                    bucket_id=bucket.bucket_id,
                    object_key="docs/sample.md",
                    filename="sample.md",
                    content_type="text/markdown",
                    size_bytes=128,
                    access_level=AccessLevel.TENANT_SHARED,
                )
            )
            document = await uow.documents.add(
                DocumentRecord(
                    document_id="doc_001",
                    tenant_id=tenant.tenant_id,
                    source_type=SourceType.URL,
                    source_format="text/html",
                    title="Sample",
                    source_uri="https://example.com/sample",
                    canonical_url="https://example.com/sample",
                    access_level=AccessLevel.TENANT_PRIVATE,
                    metadata={"title": "Sample"},
                    audit={"profile": "auto_default"},
                )
            )
            dataset = await uow.datasets.add(
                DatasetRecord(
                    dataset_id="dst_001",
                    tenant_id=tenant.tenant_id,
                    dataset_key="default",
                    display_name="Default",
                    access_level=AccessLevel.RESTRICTED,
                )
            )
            job = await uow.jobs.add(
                JobRecord(
                    job_id="job_001",
                    tenant_id=tenant.tenant_id,
                    job_type=JobType.PARSE,
                    status=JobStatus.RUNNING,
                    operation_name="parse.document",
                    submitted_at=datetime.now(UTC),
                    started_at=datetime.now(UTC),
                    request_id="req_001",
                    trace_id="trace_001",
                )
            )
            decision = await uow.authorization_decisions.add(
                AuthorizationDecisionRecord(
                    decision_id="dec_001",
                    tenant_id=tenant.tenant_id,
                    actor_id=actor.actor_id,
                    permission_key="storage:download",
                    effect=DecisionEffect.ALLOW,
                    reason_code="role_binding_match",
                    resource_type="object",
                    resource_id=stored_object.object_id,
                    trace_id="trace_001",
                    request_id="req_001",
                )
            )

            assert stored_object.object_key == "docs/sample.md"
            assert document.title == "Sample"
            assert dataset.dataset_key == "default"
            assert job.trace_id == "trace_001"
            assert decision.reason_code == "role_binding_match"

        async with CortexUnitOfWork(session_factory) as uow:
            loaded_tenant = await uow.tenants.get("tenant_001")
            loaded_actor = await uow.actors.get_by_ref(
                "tenant_001",
                actor_type="user",
                actor_ref="alice@example.com",
            )
            loaded_bucket = await uow.buckets.get_default("tenant_001")
            loaded_object = await uow.objects.get("obj_001")
            loaded_document = await uow.documents.get("doc_001")
            loaded_dataset = await uow.datasets.get_by_key("tenant_001", "default")
            loaded_job = await uow.jobs.get("job_001")
            loaded_decisions = await uow.authorization_decisions.list_for_actor("actor_001")

            assert loaded_tenant is not None
            assert loaded_tenant.tenant_key == "alpha"
            assert loaded_actor is not None
            assert loaded_actor.display_name == "Alice"
            assert loaded_bucket is not None
            assert loaded_bucket.bucket_name == "cortex-alpha"
            assert loaded_object is not None
            assert loaded_object.access_level is AccessLevel.TENANT_SHARED
            assert loaded_document is not None
            assert loaded_document.audit["profile"] == "auto_default"
            assert loaded_dataset is not None
            assert loaded_dataset.access_level is AccessLevel.RESTRICTED
            assert loaded_job is not None
            assert loaded_job.status is JobStatus.RUNNING
            assert len(loaded_decisions) == 1
            assert loaded_decisions[0].effect is DecisionEffect.ALLOW
    finally:
        await engine.dispose()
