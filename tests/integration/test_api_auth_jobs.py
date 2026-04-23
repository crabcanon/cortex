"""Integration tests for auth, health, and jobs endpoints."""

import asyncio
import base64
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from cortex_api.main import create_app
from cortex_common import load_settings
from cortex_contracts import X_REQUEST_ID_HEADER
from cortex_db import CortexUnitOfWork, create_database_engine, create_session_factory
from cortex_db.cli import main as db_migrate_main
from cortex_domain import JobEventRecord, JobRecord, JobStatus, JobType, TenantRecord
from fastapi.testclient import TestClient


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


def _dev_bearer_token(*, tenant_id: str, actor_id: str, scopes: list[str]) -> str:
    claims = {
        "sub": actor_id,
        "tenant_id": tenant_id,
        "actor_id": actor_id,
        "actor_ref": f"{actor_id}@example.com",
        "scope": " ".join(scopes),
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(claims, separators=(",", ":")).encode("utf-8")
    ).decode("ascii").rstrip("=")
    return f"Bearer dev:{encoded}"


async def _seed_api_fixture(db_path: Path) -> None:
    engine = create_database_engine(_async_sqlite_url(db_path))
    session_factory = create_session_factory(engine)
    try:
        async with CortexUnitOfWork(session_factory) as uow:
            await uow.tenants.add(
                TenantRecord(
                    tenant_id="tenant_api",
                    tenant_key="tenant_api",
                    display_name="Tenant API",
                    status="active",
                )
            )
            await uow.jobs.add(
                JobRecord(
                    job_id="job_api_001",
                    tenant_id="tenant_api",
                    job_type=JobType.PARSE,
                    status=JobStatus.RUNNING,
                    operation_name="parse_url",
                    submitted_at=datetime.now(UTC),
                    started_at=datetime.now(UTC),
                    trace_id="trace-job-api",
                    span_id="span-job-api",
                    request_id="req-job-api",
                )
            )
            await uow.job_events.add(
                JobEventRecord(
                    job_id="job_api_001",
                    sequence_no=1,
                    level="info",
                    event_type="job.running",
                    event_at=datetime.now(UTC),
                    message="Parse started.",
                    trace_id="trace-job-api",
                    span_id="span-job-api",
                )
            )
    finally:
        await engine.dispose()


def _build_client(
    monkeypatch: pytest.MonkeyPatch,
    db_path: Path,
    *,
    environment: str = "local",
    auth_mode: str = "dev",
) -> TestClient:
    monkeypatch.setenv("CORTEX_DB_DSN", _async_sqlite_url(db_path))
    monkeypatch.setenv("CORTEX_ENV", environment)
    monkeypatch.setenv("CORTEX_AUTH_MODE", auth_mode)
    monkeypatch.setenv("CORTEX_OTEL_ENABLED", "false")
    monkeypatch.setenv("CORTEX_CRAWL4AI_SKIP_PROBE", "1")
    load_settings.cache_clear()
    return TestClient(create_app())


def test_health_and_job_endpoints_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = _case_db_path("api-auth-jobs")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    asyncio.run(_seed_api_fixture(db_path))

    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_api",
            actor_id="alice",
            scopes=["health:read", "jobs:read", "jobs:cancel"],
        )
    }

    with _build_client(monkeypatch, db_path) as client:
        live_response = client.get("/v1/health/live", headers=headers)
        ready_response = client.get("/v1/health/ready", headers=headers)
        job_response = client.get("/v1/jobs/job_api_001", headers=headers)
        events_response = client.get("/v1/jobs/job_api_001/events", headers=headers)
        cancel_response = client.post("/v1/jobs/job_api_001/cancel", headers=headers)
        job_after_cancel = client.get("/v1/jobs/job_api_001", headers=headers)

    load_settings.cache_clear()

    assert live_response.status_code == 200
    assert live_response.json()["mode"] == "live"
    assert ready_response.status_code == 200
    assert ready_response.json()["checks"][0]["name"] == "relational-db"
    assert job_response.status_code == 200
    assert job_response.json()["status"] == "running"
    assert events_response.status_code == 200
    assert events_response.json()[0]["event_type"] == "job.running"
    assert cancel_response.status_code == 202
    assert cancel_response.json()["status"] == "cancelled"
    assert job_after_cancel.status_code == 200
    assert job_after_cancel.json()["status"] == "cancelled"
    assert X_REQUEST_ID_HEADER in cancel_response.headers


def test_missing_scope_returns_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = _case_db_path("api-auth-forbidden")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    asyncio.run(_seed_api_fixture(db_path))

    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_api",
            actor_id="bob",
            scopes=["health:read"],
        )
    }

    with _build_client(monkeypatch, db_path) as client:
        response = client.get("/v1/jobs/job_api_001", headers=headers)

    load_settings.cache_clear()

    assert response.status_code == 403
    assert response.json()["reason_code"] == "insufficient_scope"
    assert response.json()["required_scopes"] == ["jobs:read"]


def test_missing_bearer_token_returns_unauthorized(monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = _case_db_path("api-auth-unauthorized")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    asyncio.run(_seed_api_fixture(db_path))

    with _build_client(monkeypatch, db_path) as client:
        response = client.get("/v1/health/live")

    load_settings.cache_clear()

    assert response.status_code == 401
    assert response.json()["error_code"] == "missing_authorization"


def test_local_dev_token_endpoint_issues_swagger_ready_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = _case_db_path("api-dev-token-local")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])

    with _build_client(monkeypatch, db_path, environment="local", auth_mode="dev") as client:
        token_response = client.post(
            "/v1/dev/auth/token",
            json={
                "subject": "alice",
                "tenant_id": "tenant_api",
                "display_name": "Alice",
                "client_id": "swagger-ui",
            },
        )
        access_token = token_response.json()["access_token"]
        protected_response = client.get(
            "/v1/health/live",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        openapi = client.get("/openapi.json").json()

    load_settings.cache_clear()

    assert token_response.status_code == 200
    assert token_response.json()["token_format"] == "dev"
    assert token_response.json()["swagger_authorize_value"] == access_token
    assert token_response.json()["authorization_header"] == f"Bearer {access_token}"
    assert protected_response.status_code == 200
    assert "/v1/dev/auth/token" in openapi["paths"]


@pytest.mark.parametrize(
    ("environment", "auth_mode"),
    [
        ("prod", "dev"),
        ("local", "jwt"),
    ],
)
def test_local_dev_token_endpoint_is_not_mounted_outside_local_dev(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
    auth_mode: str,
) -> None:
    db_path = _case_db_path(f"api-dev-token-disabled-{environment}-{auth_mode}")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])

    with _build_client(
        monkeypatch,
        db_path,
        environment=environment,
        auth_mode=auth_mode,
    ) as client:
        response = client.post(
            "/v1/dev/auth/token",
            json={"subject": "alice", "tenant_id": "tenant_api"},
        )
        openapi = client.get("/openapi.json").json()

    load_settings.cache_clear()

    assert response.status_code == 404
    assert "/v1/dev/auth/token" not in openapi["paths"]
