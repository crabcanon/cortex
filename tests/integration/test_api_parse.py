"""Integration tests for parse endpoints."""

import asyncio
import base64
import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from typing import cast

import pytest
from cortex_api import lifespan as api_lifespan
from cortex_api.main import create_app
from cortex_common import CortexError, load_settings, utc_now
from cortex_contracts import (
    X_REQUEST_ID_HEADER,
    ParseEngineDeploymentMode,
    ParseEngineDescriptor,
    ParseEngineStatus,
    ParseInputKind,
)
from cortex_db import CortexUnitOfWork, create_database_engine, create_session_factory
from cortex_db.cli import main as db_migrate_main
from cortex_domain import JobStatus
from cortex_parse import (
    EngineExecutionContext,
    EngineExecutionResult,
    ParseEngineProtocol,
    ParseEngineRegistry,
    ParseJobControlService,
    ParseProfileLoader,
    ParseRequestCompiler,
    ParseScenePreset,
    ParseService,
)
from cortex_worker_parse import ParseWorker, ParseWorkerConfig
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _case_dir(name: str) -> Path:
    root = Path("runtime-test-data")
    root.mkdir(parents=True, exist_ok=True)
    case_dir = root / f"{name}-{time.time_ns()}"
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir


def _sync_sqlite_url(db_path: Path) -> str:
    return f"sqlite:///{db_path.as_posix()}"


def _async_sqlite_url(db_path: Path) -> str:
    return f"sqlite+aiosqlite:///{db_path.as_posix()}"


def _dev_bearer_token(*, tenant_id: str, actor_id: str, scopes: list[str]) -> str:
    claims = {
        "sub": actor_id,
        "tenant_id": tenant_id,
        "actor_id": actor_id,
        "actor_ref": f"{actor_id}@example.com",
        "scope": " ".join(scopes),
    }
    encoded = (
        base64.urlsafe_b64encode(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
        .decode("ascii")
        .rstrip("=")
    )
    return f"Bearer dev:{encoded}"


class _ApiParseEngine(ParseEngineProtocol):
    @property
    def descriptor(self) -> ParseEngineDescriptor:
        return ParseEngineDescriptor(
            engine_key="api_test_engine",
            display_name="API Test Engine",
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
            markdown="# API Parse\n\nHello from the parse API.",
            source_format="text/html",
            detected_mime_type="text/html",
            metadata={
                "title": "API Parse",
                "language": "en",
                "category_tags": ["api"],
                "labels": ["parse"],
            },
            final_url="https://example.com/final",
            http_status=200,
            content_length_bytes=1024,
            parser_version="api-test-1.0",
            engine_payload_summary={"mode": "sync"},
        )


class _FailingParseEngine(ParseEngineProtocol):
    @property
    def descriptor(self) -> ParseEngineDescriptor:
        return ParseEngineDescriptor(
            engine_key="failing_engine",
            display_name="Failing Engine",
            engine_family="test",
            deployment_mode=ParseEngineDeploymentMode.LOCAL,
            status=ParseEngineStatus.ACTIVE,
            supported_source_types=["url"],
            supported_formats=["text/html"],
            capabilities=["markdown"],
        )

    async def execute(self, context: EngineExecutionContext) -> EngineExecutionResult:
        del context
        raise CortexError(code="engine_unavailable", detail="engine unavailable", status_code=502)


class _SlowParseEngine(_ApiParseEngine):
    @property
    def descriptor(self) -> ParseEngineDescriptor:
        return ParseEngineDescriptor(
            engine_key="slow_engine",
            display_name="Slow Engine",
            engine_family="test",
            deployment_mode=ParseEngineDeploymentMode.LOCAL,
            status=ParseEngineStatus.ACTIVE,
            supported_source_types=["url"],
            supported_formats=["text/html"],
            capabilities=["markdown"],
        )

    async def execute(self, context: EngineExecutionContext) -> EngineExecutionResult:
        await asyncio.sleep(2)
        return await super().execute(context)


class _DoclingTestEngine(_ApiParseEngine):
    @property
    def descriptor(self) -> ParseEngineDescriptor:
        return ParseEngineDescriptor(
            engine_key="docling",
            display_name="Docling Test Engine",
            engine_family="document_local",
            deployment_mode=ParseEngineDeploymentMode.LOCAL,
            status=ParseEngineStatus.ACTIVE,
            supported_source_types=["url", "uri", "object"],
            supported_formats=["application/pdf"],
            capabilities=["markdown"],
        )


def _build_parse_service(
    profiles_dir: Path,
    engine: ParseEngineProtocol | None = None,
) -> ParseService:
    registry = ParseEngineRegistry()
    registry.register(engine or _ApiParseEngine())
    return ParseService(
        registry=registry,
        profile_loader=ParseProfileLoader(profiles_dir),
        default_profile_ref="test_profile",
    )


def _build_parse_compiler(
    *engine_keys: str,
    profile_ref: str = "test_profile",
    retry_attempts: int = 3,
    timeout_seconds: int = 45,
) -> ParseRequestCompiler:
    presets = tuple(
        ParseScenePreset(
            engine_key=engine_key,
            scene_id="balanced",
            profile_ref=profile_ref,
            description=f"Test preset for {engine_key}.",
            source_kinds=(
                ParseInputKind.URL,
                ParseInputKind.URI,
                ParseInputKind.OBJECT,
            ),
            timeout_seconds=timeout_seconds,
            crawl={"retry_policy": {"max_attempts": retry_attempts}},
        )
        for engine_key in engine_keys
    )
    return ParseRequestCompiler(
        set(engine_keys),
        presets=presets,
        default_scene_by_engine={engine_key: "balanced" for engine_key in engine_keys},
    )


@contextmanager
def _build_client(
    monkeypatch: pytest.MonkeyPatch,
    db_path: Path,
    profiles_dir: Path,
) -> Iterator[TestClient]:
    monkeypatch.setenv("CORTEX_DB_DSN", _async_sqlite_url(db_path))
    monkeypatch.setenv("CORTEX_AUTH_MODE", "dev")
    monkeypatch.setenv("CORTEX_OTEL_ENABLED", "false")
    monkeypatch.setattr(
        api_lifespan,
        "prepare_crawl4ai_playwright_runtime",
        lambda *args, **kwargs: None,
    )
    load_settings.cache_clear()
    app = create_app()
    with TestClient(app) as client:
        app.state.parse_service = _build_parse_service(profiles_dir)
        app.state.parse_request_compiler = _build_parse_compiler("api_test_engine")
        yield client
    load_settings.cache_clear()


def test_parse_api_lists_catalog_and_runs_sync_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    case_dir = _case_dir("api-parse")
    db_path = case_dir / "cortex.db"
    profiles_dir = case_dir / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    (profiles_dir / "test_profile.yaml").write_text(
        "\n".join(
            [
                "profile_ref: test_profile",
                "display_name: Test Profile",
                "routing_mode: ordered_fallback",
                "preferred_engine_key: api_test_engine",
                "allowed_engines: [api_test_engine]",
                "fallback_policy:",
                "  enabled: true",
                "  mode: ordered",
                "  on_error: try_next",
                "  max_engine_attempts: 1",
            ]
        ),
        encoding="utf-8",
    )
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])

    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_parse_api",
            actor_id="alice",
            scopes=["parse:read", "parse:write"],
        )
    }

    with _build_client(monkeypatch, db_path, profiles_dir) as client:
        engines_response = client.get("/v1/parse/engines", headers=headers)
        profiles_response = client.get("/v1/parse/profiles", headers=headers)
        sync_response = client.post(
            "/v1/parse/sync",
            headers=headers,
            json={
                "sources": ["https://docs.cognee.ai/core-concepts/overview"],
                "engine_id": "auto",
            },
        )

    assert engines_response.status_code == 200
    assert engines_response.json()["engines"][0]["engine_key"] == "api_test_engine"
    assert engines_response.json()["engines"][0]["default_scene_id"] == "balanced"
    assert engines_response.json()["engines"][0]["supported_scene_ids"] == ["balanced"]
    assert engines_response.json()["engines"][0]["default_profile_ref"] == "test_profile"
    assert profiles_response.status_code == 200
    assert profiles_response.json()["profiles"][0]["profile_ref"] == "test_profile"
    assert sync_response.status_code == 200
    assert sync_response.json()["engine_id"] == "auto"
    assert sync_response.json()["results"][0]["document"]["title"] == "API Parse"
    assert (
        sync_response.json()["results"][0]["document"]["parser"]["engine_key"] == "api_test_engine"
    )
    assert (
        sync_response.json()["results"][0]["diagnostics"]["selected_engine_key"]
        == "api_test_engine"
    )
    assert sync_response.json()["results"][0]["job_id"].startswith("job_")
    assert X_REQUEST_ID_HEADER in sync_response.headers


def test_parse_sync_requires_parse_write_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    case_dir = _case_dir("api-parse-forbidden")
    db_path = case_dir / "cortex.db"
    profiles_dir = case_dir / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    (profiles_dir / "test_profile.yaml").write_text(
        "\n".join(
            [
                "profile_ref: test_profile",
                "display_name: Test Profile",
                "allowed_engines: [api_test_engine]",
            ]
        ),
        encoding="utf-8",
    )
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])

    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_parse_api",
            actor_id="bob",
            scopes=["parse:read"],
        )
    }

    with _build_client(monkeypatch, db_path, profiles_dir) as client:
        response = client.post(
            "/v1/parse/sync",
            headers=headers,
            json={
                "sources": ["https://docs.cognee.ai/core-concepts/overview"],
                "engine_id": "api_test_engine",
            },
        )

    assert response.status_code == 403
    assert response.json()["reason_code"] == "insufficient_scope"
    assert response.json()["required_scopes"] == ["parse:write"]


def test_parse_sync_surfaces_attempt_failure_details(monkeypatch: pytest.MonkeyPatch) -> None:
    case_dir = _case_dir("api-parse-sync-failure")
    db_path = case_dir / "cortex.db"
    profiles_dir = case_dir / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    (profiles_dir / "test_profile.yaml").write_text(
        "\n".join(
            [
                "profile_ref: test_profile",
                "display_name: Test Profile",
                "preferred_engine_key: failing_engine",
                "allowed_engines: [failing_engine]",
            ]
        ),
        encoding="utf-8",
    )
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])

    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_parse_sync_failure",
            actor_id="alice",
            scopes=["parse:read", "parse:write"],
        )
    }

    with _build_client(monkeypatch, db_path, profiles_dir) as client:
        app = cast(FastAPI, client.app)
        app.state.parse_service = _build_parse_service(profiles_dir, _FailingParseEngine())
        app.state.parse_request_compiler = _build_parse_compiler("failing_engine")
        response = client.post(
            "/v1/parse/sync",
            headers=headers,
            json={
                "sources": ["https://example.com/failure"],
                "engine_id": "failing_engine",
            },
        )

    assert response.status_code == 502
    assert response.json()["error_code"] == "parse_failed"
    assert "failing_engine:engine_unavailable" in response.json()["detail"]
    assert "engine unavailable" in response.json()["detail"]


async def _run_parse_worker_once(db_path: Path, profiles_dir: Path) -> None:
    engine = create_database_engine(_async_sqlite_url(db_path))
    session_factory = create_session_factory(engine)
    try:
        worker = ParseWorker(
            session_factory=session_factory,
            parse_service=_build_parse_service(profiles_dir),
            config=ParseWorkerConfig(worker_id="worker-success", lease_seconds=30),
        )
        result = await worker.run_once()
        assert result.status == "succeeded"
        assert result.document_id is not None
    finally:
        await engine.dispose()


def test_async_parse_job_submit_worker_and_result(monkeypatch: pytest.MonkeyPatch) -> None:
    case_dir = _case_dir("api-parse-async")
    db_path = case_dir / "cortex.db"
    profiles_dir = case_dir / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    (profiles_dir / "test_profile.yaml").write_text(
        "\n".join(
            [
                "profile_ref: test_profile",
                "display_name: Test Profile",
                "routing_mode: ordered_fallback",
                "preferred_engine_key: api_test_engine",
                "allowed_engines: [api_test_engine]",
            ]
        ),
        encoding="utf-8",
    )
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])

    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_parse_async",
            actor_id="alice",
            scopes=["parse:read", "parse:write", "jobs:read"],
        ),
        "Idempotency-Key": "parse-job-001",
    }

    with _build_client(monkeypatch, db_path, profiles_dir) as client:
        app = cast(FastAPI, client.app)
        app.state.parse_request_compiler = _build_parse_compiler("api_test_engine")
        accepted_response = client.post(
            "/v1/parse/jobs",
            headers=headers,
            json={
                "sources": ["https://docs.cognee.ai/core-concepts/overview"],
                "engine_id": "auto",
                "priority": 7,
            },
        )
        duplicate_response = client.post(
            "/v1/parse/jobs",
            headers=headers,
            json={
                "sources": ["https://docs.cognee.ai/core-concepts/overview"],
                "engine_id": "auto",
                "priority": 7,
            },
        )
        job_id = accepted_response.json()["jobs"][0]["job_id"]
        pending_result = client.get(f"/v1/parse/jobs/{job_id}/result", headers=headers)
        asyncio.run(_run_parse_worker_once(db_path, profiles_dir))
        completed_result = client.get(f"/v1/parse/jobs/{job_id}/result", headers=headers)
        events_response = client.get(f"/v1/jobs/{job_id}/events", headers=headers)

    assert accepted_response.status_code == 202
    assert accepted_response.json()["jobs"][0]["status"] == "queued"
    assert duplicate_response.status_code == 202
    assert duplicate_response.json()["jobs"][0]["job_id"] == job_id
    assert pending_result.status_code == 409
    assert pending_result.json()["status"] == "queued"
    assert completed_result.status_code == 200
    assert completed_result.json()["document"]["title"] == "API Parse"
    assert completed_result.json()["diagnostics"]["selected_engine_key"] == "api_test_engine"
    assert [event["event_type"] for event in events_response.json()] == [
        "parse.job.queued",
        "parse.job.started",
        "parse.job.succeeded",
    ]


async def _run_worker_once_with_engine(
    db_path: Path,
    profiles_dir: Path,
    engine_impl: ParseEngineProtocol,
    *,
    worker_id: str,
    lease_seconds: int = 30,
    supported_engine_keys: set[str] | None = None,
) -> str:
    engine = create_database_engine(_async_sqlite_url(db_path))
    session_factory = create_session_factory(engine)
    try:
        worker = ParseWorker(
            session_factory=session_factory,
            parse_service=_build_parse_service(profiles_dir, engine_impl),
            config=ParseWorkerConfig(
                worker_id=worker_id,
                lease_seconds=lease_seconds,
                heartbeat_interval_seconds=10,
                supported_engine_keys=supported_engine_keys,
            ),
        )
        result = await worker.run_once()
        if result.status != "idle":
            assert result.job_id is not None
        return result.status
    finally:
        await engine.dispose()


async def _age_claimed_job(db_path: Path, *, worker_id: str, lease_seconds: int) -> str:
    engine = create_database_engine(_async_sqlite_url(db_path))
    session_factory = create_session_factory(engine)
    try:
        async with CortexUnitOfWork(session_factory) as uow:
            job_service = ParseJobControlService()
            claimed = await job_service.claim_next_job(
                uow=uow,
                worker_id=worker_id,
                lease_seconds=lease_seconds,
                recover_stale=False,
            )
            assert claimed is not None
            stale_heartbeat = utc_now() - timedelta(seconds=120)
            queue_state = dict(claimed.deployment_context["parse_worker"])
            queue_state["heartbeat_at"] = stale_heartbeat.isoformat()
            queue_state["lease_expires_at"] = stale_heartbeat.isoformat()
            queue_state["lease_owner"] = worker_id
            await uow.jobs.update_status(
                claimed.job_id,
                status=JobStatus.RUNNING,
                heartbeat_at=stale_heartbeat,
                deployment_context={"parse_worker": queue_state},
            )
            return claimed.job_id
    finally:
        await engine.dispose()


def test_parse_worker_retries_then_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    case_dir = _case_dir("api-parse-retry")
    db_path = case_dir / "cortex.db"
    profiles_dir = case_dir / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    (profiles_dir / "test_profile.yaml").write_text(
        "\n".join(
            [
                "profile_ref: test_profile",
                "display_name: Test Profile",
                "preferred_engine_key: failing_engine",
                "allowed_engines: [failing_engine]",
            ]
        ),
        encoding="utf-8",
    )
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_parse_retry",
            actor_id="alice",
            scopes=["parse:read", "parse:write", "jobs:read"],
        )
    }

    with _build_client(monkeypatch, db_path, profiles_dir) as client:
        app = cast(FastAPI, client.app)
        app.state.parse_request_compiler = _build_parse_compiler(
            "failing_engine",
            retry_attempts=2,
        )
        accepted_response = client.post(
            "/v1/parse/jobs",
            headers=headers,
            json={
                "sources": ["https://example.com/retry"],
                "engine_id": "failing_engine",
            },
        )
        job_id = accepted_response.json()["jobs"][0]["job_id"]
        first_status = asyncio.run(
            _run_worker_once_with_engine(
                db_path,
                profiles_dir,
                _FailingParseEngine(),
                worker_id="worker-retry-1",
            )
        )
        retry_status = client.get(f"/v1/jobs/{job_id}", headers=headers)
        second_status = asyncio.run(
            _run_worker_once_with_engine(
                db_path,
                profiles_dir,
                _FailingParseEngine(),
                worker_id="worker-retry-2",
            )
        )
        failed_status = client.get(f"/v1/jobs/{job_id}", headers=headers)
        events_response = client.get(f"/v1/jobs/{job_id}/events", headers=headers)

    assert first_status == "retrying"
    assert retry_status.json()["status"] == "queued"
    assert second_status == "failed"
    assert failed_status.json()["status"] == "failed"
    assert "failing_engine:engine_unavailable" in failed_status.json()["error"]["message"]
    assert [event["event_type"] for event in events_response.json()] == [
        "parse.job.queued",
        "parse.job.started",
        "parse.job.retry_scheduled",
        "parse.job.started",
        "parse.job.failed",
    ]
    assert "engine unavailable" in events_response.json()[-1]["details"]["last_error"]


def test_parse_worker_only_claims_supported_engine_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_dir = _case_dir("api-parse-engine-filter")
    db_path = case_dir / "cortex.db"
    profiles_dir = case_dir / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    (profiles_dir / "test_profile.yaml").write_text(
        "\n".join(
            [
                "profile_ref: test_profile",
                "display_name: Test Profile",
                "preferred_engine_key: docling",
                "allowed_engines: [docling]",
            ]
        ),
        encoding="utf-8",
    )
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_parse_engine_filter",
            actor_id="alice",
            scopes=["parse:read", "parse:write", "jobs:read"],
        )
    }

    with _build_client(monkeypatch, db_path, profiles_dir) as client:
        app = cast(FastAPI, client.app)
        app.state.parse_request_compiler = _build_parse_compiler("docling")
        accepted_response = client.post(
            "/v1/parse/jobs",
            headers=headers,
            json={
                "sources": ["https://example.com/doc.pdf"],
                "engine_id": "docling",
            },
        )
        job_id = accepted_response.json()["jobs"][0]["job_id"]
        slim_worker_status = asyncio.run(
            _run_worker_once_with_engine(
                db_path,
                profiles_dir,
                _ApiParseEngine(),
                worker_id="slim-worker",
                supported_engine_keys={"api_test_engine"},
            )
        )
        queued_status = client.get(f"/v1/jobs/{job_id}", headers=headers)
        docling_worker_status = asyncio.run(
            _run_worker_once_with_engine(
                db_path,
                profiles_dir,
                _DoclingTestEngine(),
                worker_id="docling-worker",
                supported_engine_keys={"docling"},
            )
        )
        completed_result = client.get(f"/v1/parse/jobs/{job_id}/result", headers=headers)

    assert slim_worker_status == "idle"
    assert queued_status.json()["status"] == "queued"
    assert docling_worker_status == "succeeded"
    assert completed_result.status_code == 200
    assert completed_result.json()["diagnostics"]["selected_engine_key"] == "docling"


def test_parse_worker_timeout_fails_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    case_dir = _case_dir("api-parse-timeout")
    db_path = case_dir / "cortex.db"
    profiles_dir = case_dir / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    (profiles_dir / "test_profile.yaml").write_text(
        "\n".join(
            [
                "profile_ref: test_profile",
                "display_name: Test Profile",
                "preferred_engine_key: slow_engine",
                "allowed_engines: [slow_engine]",
            ]
        ),
        encoding="utf-8",
    )
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_parse_timeout",
            actor_id="alice",
            scopes=["parse:read", "parse:write", "jobs:read"],
        )
    }

    with _build_client(monkeypatch, db_path, profiles_dir) as client:
        app = cast(FastAPI, client.app)
        app.state.parse_request_compiler = _build_parse_compiler(
            "slow_engine",
            retry_attempts=1,
            timeout_seconds=1,
        )
        accepted_response = client.post(
            "/v1/parse/jobs",
            headers=headers,
            json={
                "sources": ["https://example.com/slow"],
                "engine_id": "slow_engine",
            },
        )
        job_id = accepted_response.json()["jobs"][0]["job_id"]
        worker_status = asyncio.run(
            _run_worker_once_with_engine(
                db_path,
                profiles_dir,
                _SlowParseEngine(),
                worker_id="worker-timeout",
            )
        )
        failed_status = client.get(f"/v1/jobs/{job_id}", headers=headers)
        events_response = client.get(f"/v1/jobs/{job_id}/events", headers=headers)

    assert worker_status == "failed"
    assert failed_status.json()["status"] == "failed"
    assert failed_status.json()["error"]["code"] == "parse_worker_timeout"
    assert events_response.json()[-1]["event_type"] == "parse.job.failed"


def test_parse_worker_recovers_stale_lease(monkeypatch: pytest.MonkeyPatch) -> None:
    case_dir = _case_dir("api-parse-stale-lease")
    db_path = case_dir / "cortex.db"
    profiles_dir = case_dir / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    (profiles_dir / "test_profile.yaml").write_text(
        "\n".join(
            [
                "profile_ref: test_profile",
                "display_name: Test Profile",
                "preferred_engine_key: api_test_engine",
                "allowed_engines: [api_test_engine]",
            ]
        ),
        encoding="utf-8",
    )
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_parse_stale",
            actor_id="alice",
            scopes=["parse:read", "parse:write", "jobs:read"],
        )
    }

    with _build_client(monkeypatch, db_path, profiles_dir) as client:
        app = cast(FastAPI, client.app)
        app.state.parse_request_compiler = _build_parse_compiler(
            "api_test_engine",
            retry_attempts=2,
        )
        accepted_response = client.post(
            "/v1/parse/jobs",
            headers=headers,
            json={
                "sources": ["https://example.com/stale"],
                "engine_id": "api_test_engine",
            },
        )
        job_id = accepted_response.json()["jobs"][0]["job_id"]
        claimed_job_id = asyncio.run(
            _age_claimed_job(db_path, worker_id="stuck-worker", lease_seconds=1)
        )
        worker_status = asyncio.run(
            _run_worker_once_with_engine(
                db_path,
                profiles_dir,
                _ApiParseEngine(),
                worker_id="recovery-worker",
                lease_seconds=1,
            )
        )
        completed_result = client.get(f"/v1/parse/jobs/{job_id}/result", headers=headers)
        events_response = client.get(f"/v1/jobs/{job_id}/events", headers=headers)

    assert claimed_job_id == job_id
    assert worker_status == "succeeded"
    assert completed_result.status_code == 200
    assert "parse.job.lease_recovered" in [event["event_type"] for event in events_response.json()]
