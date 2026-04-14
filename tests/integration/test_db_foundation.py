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
    ActorRoleBindingRecord,
    AuthorizationDecisionRecord,
    AuthorizationPolicyRecord,
    DatasetRecord,
    DecisionEffect,
    DocumentArtifactRecord,
    DocumentChunkRecord,
    DocumentRecord,
    DocumentTagRecord,
    JobEventRecord,
    JobRecord,
    JobStatus,
    JobType,
    ObjectRecord,
    ObjectStatus,
    ObjectVersionRecord,
    ParseAttemptStatus,
    ParseEngineDeploymentMode,
    ParseEngineRecord,
    ParseEngineStatus,
    ParserProfileRecord,
    ParseRunAttemptRecord,
    ParseRunRecord,
    PermissionRecord,
    RolePermissionRecord,
    RoleRecord,
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
        "object_versions",
        "parser_engines",
        "parser_profiles",
        "documents",
        "document_artifacts",
        "document_tags",
        "document_chunks",
        "datasets",
        "jobs",
        "authorization_decisions",
        "parse_runs",
        "parse_run_attempts",
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
            permission = await uow.permissions.add(
                PermissionRecord(
                    permission_key="storage:download",
                    permission_kind="functional",
                    resource_type="object",
                    action_name="download",
                )
            )
            role = await uow.roles.add(
                RoleRecord(
                    role_id="role_001",
                    tenant_id=tenant.tenant_id,
                    role_key="storage_reader",
                    display_name="Storage Reader",
                    scope_level="tenant",
                )
            )
            role_permission = await uow.role_permissions.add(
                RolePermissionRecord(
                    role_id=role.role_id,
                    permission_key=permission.permission_key,
                    effect=DecisionEffect.ALLOW,
                )
            )
            binding = await uow.actor_role_bindings.add(
                ActorRoleBindingRecord(
                    binding_id="bind_001",
                    tenant_id=tenant.tenant_id,
                    actor_id=actor.actor_id,
                    role_id=role.role_id,
                )
            )
            policy = await uow.authorization_policies.add(
                AuthorizationPolicyRecord(
                    policy_id="policy_001",
                    tenant_id=tenant.tenant_id,
                    policy_key="allow-shared-download",
                    effect=DecisionEffect.ALLOW,
                    subject_selector={"actor_ids": [actor.actor_id]},
                    resource_selector={"resource_types": ["object"]},
                    condition={"attributes": {"classification": "internal"}},
                )
            )
            bucket = await uow.buckets.add(
                StorageBucketRecord(
                    bucket_id="bucket_001",
                    tenant_id=tenant.tenant_id,
                    bucket_name="cortex-alpha",
                    is_default=True,
                )
            )
            parser_engine = await uow.parser_engines.add(
                ParseEngineRecord(
                    engine_id="pengine_001",
                    engine_key="crawl4ai",
                    display_name="Crawl4AI",
                    engine_family="web_interactive",
                    deployment_mode=ParseEngineDeploymentMode.LOCAL,
                    status=ParseEngineStatus.ACTIVE,
                    supported_source_types=["url"],
                    capability_flags=["interactive_web"],
                )
            )
            parser_profile = await uow.parser_profiles.add(
                ParserProfileRecord(
                    profile_id="pprofile_001",
                    tenant_id=tenant.tenant_id,
                    profile_key="auto_default",
                    display_name="Auto Default",
                    routing_mode="ordered_fallback",
                    preferred_engine_id=parser_engine.engine_id,
                    allowed_engines=["crawl4ai"],
                    normalization={"schema_version": "cortex.parse.v1"},
                    fallback_policy={"mode": "ordered"},
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
                    status=ObjectStatus.AVAILABLE,
                )
            )
            object_version = await uow.object_versions.add(
                ObjectVersionRecord(
                    object_version_id="objver_001",
                    object_id=stored_object.object_id,
                    version_no=1,
                    size_bytes=stored_object.size_bytes,
                    checksum_sha256="a" * 64,
                    etag="etag-001",
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
                    source_object_id=stored_object.object_id,
                    language_code="en",
                    detected_mime_type="text/html",
                    content_hash_sha256="b" * 64,
                    access_level=AccessLevel.TENANT_PRIVATE,
                    metadata={"title": "Sample"},
                    audit={"profile": "auto_default"},
                )
            )
            artifact = await uow.document_artifacts.add(
                DocumentArtifactRecord(
                    document_id=document.document_id,
                    artifact_type="markdown",
                    object_id=stored_object.object_id,
                    artifact_ref=stored_object.object_key,
                    metadata={"role": "normalized"},
                )
            )
            document_tag = await uow.document_tags.add(
                DocumentTagRecord(
                    document_id=document.document_id,
                    tag="docs",
                )
            )
            chunk = await uow.document_chunks.add(
                DocumentChunkRecord(
                    chunk_id="chunk_001",
                    document_id=document.document_id,
                    chunk_index=0,
                    chunk_text="# Sample",
                    heading_path="Sample",
                    token_count=2,
                    char_count=8,
                    checksum_sha256="c" * 64,
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
            parse_run = await uow.parse_runs.add(
                ParseRunRecord(
                    parse_run_id="prun_001",
                    job_id=job.job_id,
                    source_kind=SourceType.URL,
                    parser_profile_id=parser_profile.profile_id,
                    selected_engine_id=parser_engine.engine_id,
                    trace_id="trace_001",
                    document_id=document.document_id,
                    source_url=document.source_uri,
                    source_ref=document.source_uri,
                    selection_policy={"preferred_engine_key": "crawl4ai"},
                    crawl_profile={"timeout_ms": 60000},
                    normalization={"schema_version": "cortex.parse.v1"},
                    output_profile={"llm_ready_mode": "markdown"},
                    fallback_chain=["crawl4ai"],
                    diagnostics={"selected_engine_key": "crawl4ai"},
                )
            )
            parse_run_attempt = await uow.parse_run_attempts.add(
                ParseRunAttemptRecord(
                    parse_run_id=parse_run.parse_run_id,
                    attempt_no=1,
                    engine_id=parser_engine.engine_id,
                    status=ParseAttemptStatus.SUCCEEDED,
                    trace_id="trace_001",
                    span_id="span_002",
                    engine_request={"source": "https://example.com/sample"},
                    engine_result={"title": "Sample"},
                    diagnostics={"duration_ms": 42},
                    started_at=datetime.now(UTC),
                    completed_at=datetime.now(UTC),
                )
            )
            job_event = await uow.job_events.add(
                JobEventRecord(
                    job_id=job.job_id,
                    sequence_no=1,
                    level="info",
                    event_type="job.running",
                    event_at=datetime.now(UTC),
                    message="Job started.",
                    trace_id="trace_001",
                    span_id="span_001",
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
            assert object_version.object_id == "obj_001"
            assert parser_engine.engine_key == "crawl4ai"
            assert parser_profile.profile_key == "auto_default"
            assert document.title == "Sample"
            assert artifact.artifact_type == "markdown"
            assert document_tag.tag == "docs"
            assert chunk.chunk_index == 0
            assert dataset.dataset_key == "default"
            assert job.trace_id == "trace_001"
            assert parse_run.document_id == "doc_001"
            assert parse_run_attempt.status is ParseAttemptStatus.SUCCEEDED
            assert role_permission.permission_key == "storage:download"
            assert binding.binding_scope == "tenant"
            assert policy.policy_key == "allow-shared-download"
            assert job_event.event_type == "job.running"
            assert decision.reason_code == "role_binding_match"

        async with CortexUnitOfWork(session_factory) as uow:
            loaded_tenant = await uow.tenants.get("tenant_001")
            loaded_actor = await uow.actors.get_by_ref(
                "tenant_001",
                actor_type="user",
                actor_ref="alice@example.com",
            )
            loaded_bucket = await uow.buckets.get_default("tenant_001")
            loaded_parser_engine = await uow.parser_engines.get_by_key("crawl4ai")
            loaded_parser_profile = await uow.parser_profiles.get_by_key(
                "tenant_001",
                "auto_default",
            )
            loaded_object = await uow.objects.get("obj_001")
            loaded_document = await uow.documents.get("doc_001")
            loaded_artifacts = await uow.document_artifacts.list_for_document("doc_001")
            loaded_tags = await uow.document_tags.list_for_document("doc_001")
            loaded_chunks = await uow.document_chunks.list_for_document("doc_001")
            loaded_object_version = await uow.object_versions.get_latest("obj_001")
            loaded_dataset = await uow.datasets.get_by_key("tenant_001", "default")
            loaded_job = await uow.jobs.get("job_001")
            loaded_parse_run = await uow.parse_runs.get_by_job("job_001")
            loaded_parse_attempts = await uow.parse_run_attempts.list_for_run("prun_001")
            loaded_permission = await uow.permissions.get("storage:download")
            loaded_roles = await uow.roles.list_for_tenant("tenant_001")
            loaded_bindings = await uow.actor_role_bindings.list_for_actor(
                "actor_001",
                tenant_id="tenant_001",
                resource_type="object",
                resource_id="obj_001",
                now=datetime.now(UTC),
            )
            loaded_role_permissions = await uow.role_permissions.list_for_role_ids(["role_001"])
            loaded_policies = await uow.authorization_policies.list_for_tenant("tenant_001")
            loaded_job_events = await uow.job_events.list_for_job("job_001")
            loaded_decisions = await uow.authorization_decisions.list_for_actor("actor_001")

            assert loaded_tenant is not None
            assert loaded_tenant.tenant_key == "alpha"
            assert loaded_actor is not None
            assert loaded_actor.display_name == "Alice"
            assert loaded_bucket is not None
            assert loaded_bucket.bucket_name == "cortex-alpha"
            assert loaded_parser_engine is not None
            assert loaded_parser_engine.deployment_mode is ParseEngineDeploymentMode.LOCAL
            assert loaded_parser_profile is not None
            assert loaded_parser_profile.preferred_engine_id == "pengine_001"
            assert loaded_object is not None
            assert loaded_object.access_level is AccessLevel.TENANT_SHARED
            assert loaded_object_version is not None
            assert loaded_object_version.version_no == 1
            assert loaded_document is not None
            assert loaded_document.audit["profile"] == "auto_default"
            assert len(loaded_artifacts) == 1
            assert loaded_artifacts[0].object_id == "obj_001"
            assert len(loaded_tags) == 1
            assert loaded_tags[0].tag == "docs"
            assert len(loaded_chunks) == 1
            assert loaded_chunks[0].heading_path == "Sample"
            assert loaded_dataset is not None
            assert loaded_dataset.access_level is AccessLevel.RESTRICTED
            assert loaded_job is not None
            assert loaded_job.status is JobStatus.RUNNING
            assert loaded_parse_run is not None
            assert loaded_parse_run.selected_engine_id == "pengine_001"
            assert len(loaded_parse_attempts) == 1
            assert loaded_parse_attempts[0].engine_result["title"] == "Sample"
            assert loaded_permission is not None
            assert loaded_permission.permission_kind == "functional"
            assert len(loaded_roles) == 1
            assert len(loaded_bindings) == 1
            assert loaded_bindings[0].role_id == "role_001"
            assert len(loaded_role_permissions) == 1
            assert loaded_role_permissions[0].effect is DecisionEffect.ALLOW
            assert len(loaded_policies) == 1
            assert loaded_policies[0].condition["attributes"]["classification"] == "internal"
            assert len(loaded_job_events) == 1
            assert loaded_job_events[0].span_id == "span_001"
            assert len(loaded_decisions) == 1
            assert loaded_decisions[0].effect is DecisionEffect.ALLOW
    finally:
        await engine.dispose()
