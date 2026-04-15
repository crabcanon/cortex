"""Integration tests for the optional built-in token issuance endpoint."""

import time
from pathlib import Path

import pytest
from cortex_api.main import create_app
from cortex_common import load_settings
from cortex_contracts import X_CORTEX_ISSUER_SECRET_HEADER
from cortex_db.cli import main as db_migrate_main
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


def _build_client(
    monkeypatch: pytest.MonkeyPatch,
    *,
    db_path: Path,
    auth_mode: str,
    issuer_enabled: bool = True,
) -> TestClient:
    monkeypatch.setenv("CORTEX_DB_DSN", _async_sqlite_url(db_path))
    monkeypatch.setenv("CORTEX_AUTH_MODE", auth_mode)
    monkeypatch.setenv(
        "CORTEX_AUTH_TOKEN_ISSUER_ENABLED",
        "true" if issuer_enabled else "false",
    )
    monkeypatch.setenv("CORTEX_AUTH_TOKEN_ISSUER_BOOTSTRAP_SECRET", "bootstrap-secret")
    monkeypatch.setenv(
        "CORTEX_AUTH_JWT_SHARED_SECRET",
        "jwt-shared-secret-0123456789abcdef",
    )
    monkeypatch.setenv("CORTEX_OTEL_ENABLED", "false")
    load_settings.cache_clear()
    return TestClient(create_app())


def _issue_token(client: TestClient) -> str:
    response = client.post(
        "/v1/auth/token",
        headers={X_CORTEX_ISSUER_SECRET_HEADER: "bootstrap-secret"},
        json={
            "subject": "alice",
            "tenant_id": "tenant_api",
            "scopes": ["health:read"],
            "roles": ["admin"],
        },
    )
    assert response.status_code == 200
    return f"Bearer {response.json()['access_token']}"


def test_dev_token_endpoint_issues_token_usable_on_protected_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = _case_db_path("api-auth-token-dev")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])

    with _build_client(monkeypatch, db_path=db_path, auth_mode="dev") as client:
        bearer = _issue_token(client)
        response = client.get("/v1/health/live", headers={"Authorization": bearer})

    load_settings.cache_clear()
    assert response.status_code == 200
    assert response.json()["mode"] == "live"


def test_jwt_token_endpoint_issues_token_usable_on_protected_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = _case_db_path("api-auth-token-jwt")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])

    with _build_client(monkeypatch, db_path=db_path, auth_mode="jwt") as client:
        bearer = _issue_token(client)
        response = client.get("/v1/health/live", headers={"Authorization": bearer})

    load_settings.cache_clear()
    assert response.status_code == 200
    assert response.json()["mode"] == "live"


def test_token_endpoint_returns_unavailable_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = _case_db_path("api-auth-token-disabled")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])

    with _build_client(
        monkeypatch,
        db_path=db_path,
        auth_mode="dev",
        issuer_enabled=False,
    ) as client:
        response = client.post(
            "/v1/auth/token",
            headers={X_CORTEX_ISSUER_SECRET_HEADER: "bootstrap-secret"},
            json={
                "subject": "alice",
                "tenant_id": "tenant_api",
                "scopes": ["health:read"],
            },
        )

    load_settings.cache_clear()
    assert response.status_code == 503
    assert response.json()["error_code"] == "token_issuer_disabled"
