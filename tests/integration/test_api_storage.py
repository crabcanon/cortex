"""Integration tests for storage endpoints."""

import base64
import json
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from cortex_api.main import create_app
from cortex_common import load_settings
from cortex_contracts import X_REQUEST_ID_HEADER, MultipartPartUpload, PresignedRequestDescriptor
from cortex_db.cli import main as db_migrate_main
from cortex_storage import StorageService
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


def _dev_bearer_token(
    *,
    tenant_id: str,
    actor_id: str,
    scopes: list[str],
    roles: list[str] | None = None,
) -> str:
    claims = {
        "sub": actor_id,
        "tenant_id": tenant_id,
        "actor_id": actor_id,
        "actor_ref": f"{actor_id}@example.com",
        "scope": " ".join(scopes),
        "roles": roles or [],
    }
    encoded = (
        base64.urlsafe_b64encode(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
        .decode("ascii")
        .rstrip("=")
    )
    return f"Bearer dev:{encoded}"


class FakeObjectStoreClient:
    def __init__(self) -> None:
        self.buckets: set[str] = set()
        self.single_part_objects: dict[tuple[str, str], dict[str, Any]] = {}
        self.put_objects: dict[tuple[str, str], bytes] = {}

    def ensure_bucket(self, bucket_name: str) -> None:
        self.buckets.add(bucket_name)

    def create_single_part_upload(
        self,
        *,
        bucket_name: str,
        object_key: str,
        content_type: str,
        expires_in: int,
    ) -> PresignedRequestDescriptor:
        self.single_part_objects[(bucket_name, object_key)] = {
            "ContentType": content_type,
            "ETag": f"etag-{object_key}",
        }
        return PresignedRequestDescriptor(
            method="PUT",
            url=f"https://storage.test/{bucket_name}/{object_key}?expires={expires_in}",
            headers={"Content-Type": content_type},
        )

    def put_object(
        self,
        *,
        bucket_name: str,
        object_key: str,
        body: bytes,
        content_type: str,
        metadata: dict[str, str],
    ) -> dict[str, Any]:
        self.put_objects[(bucket_name, object_key)] = body
        self.single_part_objects[(bucket_name, object_key)] = {
            "ContentType": content_type,
            "ContentLength": len(body),
            "ETag": f"etag-{object_key}",
            "Metadata": metadata,
        }
        return {
            "ETag": f"etag-{object_key}",
            "VersionId": "version-direct-001",
        }

    def create_multipart_upload(
        self,
        *,
        bucket_name: str,
        object_key: str,
        content_type: str,
        metadata: dict[str, str],
    ) -> str:
        self.buckets.add(bucket_name)
        return "provider-upload-001"

    def create_multipart_part_upload(
        self,
        *,
        bucket_name: str,
        object_key: str,
        provider_upload_id: str,
        part_number: int,
        expires_in: int,
    ) -> MultipartPartUpload:
        return MultipartPartUpload(
            part_number=part_number,
            method="PUT",
            url=(
                f"https://storage.test/{bucket_name}/{object_key}"
                f"?uploadId={provider_upload_id}&partNumber={part_number}&expires={expires_in}"
            ),
            headers={},
        )

    def complete_multipart_upload(
        self,
        *,
        bucket_name: str,
        object_key: str,
        provider_upload_id: str,
        parts: Sequence[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "ETag": f"etag-{provider_upload_id}-{len(parts)}",
            "VersionId": "version-001",
        }

    def create_download_request(
        self,
        *,
        bucket_name: str,
        object_key: str,
        disposition: str,
        expires_in: int,
    ) -> PresignedRequestDescriptor:
        return PresignedRequestDescriptor(
            method="GET",
            url=(
                f"https://storage.test/{bucket_name}/{object_key}"
                f"?disposition={disposition}&expires={expires_in}"
            ),
            headers={},
        )

    def head_object(
        self,
        *,
        bucket_name: str,
        object_key: str,
    ) -> dict[str, Any]:
        return dict(self.single_part_objects.get((bucket_name, object_key), {}))

    def get_object_bytes(
        self,
        *,
        bucket_name: str,
        object_key: str,
    ) -> bytes:
        return self.put_objects[(bucket_name, object_key)]


@contextmanager
def _build_client(
    monkeypatch: pytest.MonkeyPatch,
    db_path: Path,
    *,
    direct_upload_max_bytes: int | None = None,
) -> Iterator[TestClient]:
    monkeypatch.setenv("CORTEX_DB_DSN", _async_sqlite_url(db_path))
    monkeypatch.setenv("CORTEX_AUTH_MODE", "dev")
    monkeypatch.setenv("CORTEX_OTEL_ENABLED", "false")
    monkeypatch.setenv("CORTEX_COGNEE_ENABLED", "false")
    monkeypatch.setenv("CORTEX_CRAWL4AI_SKIP_PROBE", "1")
    if direct_upload_max_bytes is not None:
        monkeypatch.setenv(
            "CORTEX_STORAGE_DIRECT_UPLOAD_MAX_BYTES",
            str(direct_upload_max_bytes),
        )
    load_settings.cache_clear()
    app = create_app()
    with TestClient(app) as client:
        app.state.storage_service = StorageService(
            app.state.settings.s3,
            object_store=FakeObjectStoreClient(),
        )
        yield client
    load_settings.cache_clear()


def test_storage_single_part_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = _case_db_path("api-storage-single")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_storage",
            actor_id="alice",
            scopes=["storage:write", "storage:read", "storage:download"],
        )
    }

    with _build_client(monkeypatch, db_path) as client:
        create_response = client.post(
            "/v1/storage/uploads",
            headers=headers,
            json={
                "filename": "sample.md",
                "metadata": {"source": "user"},
                "tags": ["docs"],
                "access_policy": {"access_level": "tenant_private"},
            },
        )
        upload_id = create_response.json()["upload_id"]
        object_id = create_response.json()["object_id"]
        complete_response = client.post(
            f"/v1/storage/uploads/{upload_id}/complete",
            headers=headers,
            json={},
        )
        object_response = client.get(f"/v1/storage/objects/{object_id}", headers=headers)
        download_response = client.get(
            f"/v1/storage/objects/{object_id}/download-url",
            headers=headers,
            params={"ttl_seconds": 300, "disposition": "attachment"},
        )

    assert create_response.status_code == 201
    assert create_response.json()["upload_mode"] == "single_part"
    assert create_response.json()["single_part"]["method"] == "PUT"
    assert create_response.json()["single_part"]["headers"]["Content-Type"] == "text/markdown"
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "available"
    assert complete_response.json()["current_version_id"].startswith("objver_")
    assert object_response.status_code == 200
    assert object_response.json()["content_type"] == "text/markdown"
    assert object_response.json()["metadata"]["source"] == "user"
    assert object_response.json()["tags"] == ["docs"]
    assert object_response.json()["size_bytes"] == 0
    assert download_response.status_code == 200
    assert download_response.json()["method"] == "GET"
    assert X_REQUEST_ID_HEADER in download_response.headers


def test_storage_small_file_direct_upload(monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = _case_db_path("api-storage-file")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_storage",
            actor_id="alice",
            scopes=["storage:write", "storage:read"],
        )
    }

    with _build_client(monkeypatch, db_path) as client:
        response = client.post(
            "/v1/storage/files",
            headers=headers,
            files={"file": ("README.md", b"# Cortex\n", "application/octet-stream")},
            data={
                "metadata_json": '{"source":"swagger-demo"}',
                "access_policy_json": '{"access_level":"tenant_shared"}',
                "tags": "docs,product",
            },
        )

    payload = response.json()
    assert response.status_code == 201
    assert payload["status"] == "available"
    assert payload["filename"] == "README.md"
    assert payload["content_type"] == "text/markdown"
    assert payload["size_bytes"] == len(b"# Cortex\n")
    assert payload["metadata"] == {"source": "swagger-demo"}
    assert payload["tags"] == ["docs", "product"]
    assert payload["access_policy"]["access_level"] == "tenant_shared"
    assert payload["current_version_id"].startswith("objver_")


def test_storage_small_file_direct_upload_rejects_oversized_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = _case_db_path("api-storage-file-too-large")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_storage",
            actor_id="alice",
            scopes=["storage:write"],
        )
    }

    with _build_client(monkeypatch, db_path, direct_upload_max_bytes=3) as client:
        response = client.post(
            "/v1/storage/files",
            headers=headers,
            files={"file": ("tiny.txt", b"abcd", "text/plain")},
        )

    assert response.status_code == 413
    assert response.json()["error_code"] == "direct_upload_too_large"


def test_storage_small_file_direct_upload_rejects_checksum_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = _case_db_path("api-storage-file-checksum")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_storage",
            actor_id="alice",
            scopes=["storage:write"],
        )
    }

    with _build_client(monkeypatch, db_path) as client:
        response = client.post(
            "/v1/storage/files",
            headers=headers,
            files={"file": ("tiny.txt", b"hello", "text/plain")},
            data={"checksum_sha256": "0" * 64},
        )

    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"
    assert "checksum_sha256" in response.json()["detail"]


def test_large_upload_uses_multipart(monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = _case_db_path("api-storage-multipart")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_storage",
            actor_id="alice",
            scopes=["storage:write"],
        )
    }

    with _build_client(monkeypatch, db_path) as client:
        response = client.post(
            "/v1/storage/uploads",
            headers=headers,
            json={
                "filename": "archive.bin",
                "size_bytes": 20_000_000,
                "metadata": {"source": "batch"},
            },
        )

    assert response.status_code == 201
    assert response.json()["upload_mode"] == "multipart"
    assert len(response.json()["multipart_parts"]) == 3


def test_unknown_size_defaults_to_single_part(monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = _case_db_path("api-storage-unknown-size")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_storage",
            actor_id="alice",
            scopes=["storage:write"],
        )
    }

    with _build_client(monkeypatch, db_path) as client:
        response = client.post(
            "/v1/storage/uploads",
            headers=headers,
            json={
                "filename": "archive.bin",
                "metadata": {"source": "unknown-size"},
            },
        )

    assert response.status_code == 201
    assert response.json()["upload_mode"] == "single_part"
    assert response.json()["single_part"]["headers"]["Content-Type"] == "application/octet-stream"


def test_download_without_scope_returns_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = _case_db_path("api-storage-forbidden")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    full_headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_storage",
            actor_id="alice",
            scopes=["storage:write", "storage:read", "storage:download"],
        )
    }
    limited_headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_storage",
            actor_id="alice",
            scopes=["storage:read"],
        )
    }

    with _build_client(monkeypatch, db_path) as client:
        create_response = client.post(
            "/v1/storage/uploads",
            headers=full_headers,
            json={
                "filename": "secret.txt",
                "size_bytes": 128,
                "access_policy": {"access_level": "tenant_private"},
            },
        )
        object_id = create_response.json()["object_id"]
        client.post(
            f"/v1/storage/uploads/{object_id}/complete",
            headers=full_headers,
            json={},
        )
        response = client.get(
            f"/v1/storage/objects/{object_id}/download-url",
            headers=limited_headers,
        )

    assert response.status_code == 403
    assert response.json()["reason_code"] == "insufficient_scope"
    assert response.json()["required_scopes"] == ["storage:download"]
