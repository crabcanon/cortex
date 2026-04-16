"""End-to-end integration tests for the main Cortex API workflow."""

import asyncio
import base64
import json
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pytest
from cortex_api.main import create_app
from cortex_common import load_settings
from cortex_contracts import (
    X_REQUEST_ID_HEADER,
    MultipartPartUpload,
    ParseEngineDeploymentMode,
    ParseEngineDescriptor,
    ParseEngineStatus,
    ParseInputKind,
    PresignedRequestDescriptor,
)
from cortex_db import CortexUnitOfWork, create_database_engine, create_session_factory
from cortex_db.cli import main as db_migrate_main
from cortex_domain import (
    DatasetItemRecord,
    DatasetRecord,
    DocumentRecord,
    JobEventRecord,
    KnowledgeRunRecord,
    ObjectRecord,
    ParseRunAttemptRecord,
    ParseRunRecord,
    SearchHitRecord,
    SearchRequestRecord,
)
from cortex_knowledge import (
    CogneeRuntimeDescriptor,
    KnowledgeDatasetService,
    KnowledgeJobControlService,
    KnowledgeOperationService,
    KnowledgeSearchService,
)
from cortex_parse import (
    EngineExecutionContext,
    EngineExecutionResult,
    ParseEngineProtocol,
    ParseEngineRegistry,
    ParseProfileLoader,
    ParseRequestCompiler,
    ParseScenePreset,
    ParseService,
)
from cortex_storage import StorageService
from cortex_worker_knowledge import KnowledgeWorker, KnowledgeWorkerConfig
from cortex_worker_parse import ParseWorker, ParseWorkerConfig
from fastapi import FastAPI
from fastapi.testclient import TestClient


@dataclass(slots=True)
class _PersistedE2EState:
    object_record: ObjectRecord
    parse_run: ParseRunRecord
    document: DocumentRecord
    parse_attempts: list[ParseRunAttemptRecord]
    knowledge_run: KnowledgeRunRecord
    dataset: DatasetRecord
    dataset_items: list[DatasetItemRecord]
    search_request: SearchRequestRecord
    search_hits: list[SearchHitRecord]
    parse_events: list[JobEventRecord]
    add_events: list[JobEventRecord]


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
    encoded = base64.urlsafe_b64encode(
        json.dumps(claims, separators=(",", ":")).encode("utf-8")
    ).decode("ascii").rstrip("=")
    return f"Bearer dev:{encoded}"


class _FakeObjectStoreClient:
    def __init__(self) -> None:
        self.buckets: set[str] = set()

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
        return PresignedRequestDescriptor(
            method="PUT",
            url=f"https://storage.test/{bucket_name}/{object_key}?expires={expires_in}",
            headers={"Content-Type": content_type},
        )

    def create_multipart_upload(
        self,
        *,
        bucket_name: str,
        object_key: str,
        content_type: str,
        metadata: dict[str, str],
    ) -> str:
        del content_type, metadata
        self.buckets.add(bucket_name)
        return f"provider-{object_key}"

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
        del bucket_name, object_key
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


class _E2EParseEngine(ParseEngineProtocol):
    @property
    def descriptor(self) -> ParseEngineDescriptor:
        return ParseEngineDescriptor(
            engine_key="e2e_parse_engine",
            display_name="E2E Parse Engine",
            engine_family="test",
            deployment_mode=ParseEngineDeploymentMode.LOCAL,
            status=ParseEngineStatus.ACTIVE,
            supported_source_types=["object", "url"],
            supported_formats=["text/markdown", "text/html"],
            capabilities=["markdown", "metadata"],
        )

    async def execute(self, context: EngineExecutionContext) -> EngineExecutionResult:
        canonical_url = context.source.canonical_url or "https://example.com/guides/cortex"
        object_id = context.source.object_id or "unknown-object"
        return EngineExecutionResult(
            markdown=(
                "# Cortex Guide\n\n"
                "Cortex unifies upload, parse, and knowledge workflows into one API chain.\n\n"
                "## Main Path\n\n"
                "Upload the source, parse it into Markdown, ingest the document, then search it."
            ),
            source_format="text/markdown",
            detected_mime_type=context.source.expected_content_type or "text/markdown",
            metadata={
                "title": "Cortex Guide",
                "language": "en",
                "summary": "Unified storage, parse, and knowledge workflow guide.",
                "category_tags": ["guide", "workflow"],
                "labels": ["e2e", "main-path"],
            },
            final_url=canonical_url,
            http_status=200,
            content_length_bytes=384,
            parser_version="e2e-parse-1.0",
            engine_payload_summary={"source_object_id": object_id},
        )


class _FakeKnowledgeRuntime:
    def __init__(self) -> None:
        self._descriptor = CogneeRuntimeDescriptor(
            provider_key="fake_cognee",
            display_name="Fake Cognee",
            status="active",
            capabilities=["add", "cognify", "memify", "search"],
            version="test-1.0",
        )
        self.calls: list[tuple[str, str | None, dict[str, object]]] = []

    @property
    def descriptor(self) -> CogneeRuntimeDescriptor:
        return self._descriptor

    async def add(self, *, dataset: str, payload: dict[str, object]) -> dict[str, object]:
        self.calls.append(("add", dataset, dict(payload)))
        inputs = payload.get("inputs")
        object_count = 0
        document_count = 0
        if isinstance(inputs, list):
            for item in inputs:
                if not isinstance(item, dict):
                    continue
                if item.get("input_type") == "object_id":
                    object_count += 1
                if item.get("input_type") == "document_id":
                    document_count += 1
        return {
            "dataset": dataset,
            "accepted_inputs": len(inputs) if isinstance(inputs, list) else 0,
            "counters": {
                "objects": object_count,
                "documents": document_count,
            },
        }

    async def cognify(self, *, dataset: str, payload: dict[str, object]) -> dict[str, object]:
        self.calls.append(("cognify", dataset, dict(payload)))
        return {"dataset": dataset, "counters": {"chunks": 2, "graph_nodes": 1, "graph_edges": 1}}

    async def memify(self, *, dataset: str, payload: dict[str, object]) -> dict[str, object]:
        self.calls.append(("memify", dataset, dict(payload)))
        return {"dataset": dataset, "counters": {"graph_nodes": 1, "graph_edges": 1}}

    async def search(self, *, payload: dict[str, object]) -> dict[str, object]:
        self.calls.append(("search", None, dict(payload)))
        filters = payload.get("filters")
        document_id = None
        object_id = None
        if isinstance(filters, dict):
            document_ids = filters.get("document_ids")
            object_ids = filters.get("object_ids")
            if isinstance(document_ids, list) and document_ids:
                document_id = str(document_ids[0])
            if isinstance(object_ids, list) and object_ids:
                object_id = str(object_ids[0])
        query_text = str(payload.get("query_text", ""))
        return {
            "answer": f"Cortex guide answer: {query_text}",
            "context_items": [
                {
                    "rank": 1,
                    "hit_type": "chunk",
                    "score": 0.97,
                    "source_id": "chunk_ctx_1",
                    "document_id": document_id,
                    "object_id": object_id,
                    "title": "Cortex Guide",
                    "snippet": "Cortex unifies upload, parse, and knowledge workflows.",
                    "citation": {
                        "source_url": "https://example.com/guides/cortex",
                        "document_id": document_id,
                        "chunk_id": "chunk_ctx_1",
                    },
                    "metadata": {"engine": "fake_cognee"},
                }
            ],
            "graph_paths": [
                {
                    "nodes": [
                        {"id": document_id or "doc_unknown", "label": "Document"},
                        {"id": object_id or "obj_unknown", "label": "Object"},
                    ],
                    "edges": [
                        {
                            "source": object_id or "obj_unknown",
                            "target": document_id or "doc_unknown",
                            "type": "parsed_into",
                        }
                    ],
                }
            ],
        }


def _build_parse_service(profiles_dir: Path) -> ParseService:
    registry = ParseEngineRegistry()
    registry.register(_E2EParseEngine())
    return ParseService(
        registry=registry,
        profile_loader=ParseProfileLoader(profiles_dir),
        default_profile_ref="e2e_profile",
    )


def _build_parse_compiler() -> ParseRequestCompiler:
    return ParseRequestCompiler(
        {"e2e_parse_engine"},
        presets=(
            ParseScenePreset(
                engine_key="e2e_parse_engine",
                scene_id="balanced",
                profile_ref="e2e_profile",
                description="E2E default scene.",
                source_kinds=(
                    ParseInputKind.URL,
                    ParseInputKind.URI,
                    ParseInputKind.OBJECT,
                ),
            ),
        ),
        default_scene_by_engine={"e2e_parse_engine": "balanced"},
    )


@contextmanager
def _build_client(
    monkeypatch: pytest.MonkeyPatch,
    db_path: Path,
    profiles_dir: Path,
) -> Iterator[tuple[TestClient, _FakeKnowledgeRuntime]]:
    monkeypatch.setenv("CORTEX_DB_DSN", _async_sqlite_url(db_path))
    monkeypatch.setenv("CORTEX_AUTH_MODE", "dev")
    monkeypatch.setenv("CORTEX_OTEL_ENABLED", "false")
    monkeypatch.setenv("CORTEX_COGNEE_ENABLED", "false")
    load_settings.cache_clear()
    app = create_app()
    fake_runtime = _FakeKnowledgeRuntime()
    with TestClient(app) as client:
        app.state.storage_service = StorageService(
            app.state.settings.s3,
            object_store=_FakeObjectStoreClient(),
        )
        app.state.parse_service = _build_parse_service(profiles_dir)
        app.state.parse_request_compiler = _build_parse_compiler()
        app.state.knowledge_service = KnowledgeDatasetService(fake_runtime)
        app.state.knowledge_job_service = KnowledgeJobControlService()
        app.state.knowledge_search_service = KnowledgeSearchService(fake_runtime)
        yield client, fake_runtime
    load_settings.cache_clear()


async def _load_persisted_state(
    db_path: Path,
    *,
    object_id: str,
    parse_job_id: str,
    add_job_id: str,
    search_request_id: str,
) -> _PersistedE2EState:
    engine = create_database_engine(_async_sqlite_url(db_path))
    session_factory = create_session_factory(engine)
    try:
        async with CortexUnitOfWork(session_factory) as uow:
            object_record = await uow.objects.get(object_id)
            assert object_record is not None

            parse_run = await uow.parse_runs.get_by_job(parse_job_id)
            assert parse_run is not None
            assert parse_run.document_id is not None

            document = await uow.documents.get(parse_run.document_id)
            assert document is not None
            parse_attempts = await uow.parse_run_attempts.list_for_run(parse_run.parse_run_id)

            knowledge_run = await uow.knowledge_runs.get_by_job(add_job_id)
            assert knowledge_run is not None
            dataset = await uow.datasets.get(knowledge_run.dataset_id)
            assert dataset is not None
            dataset_items = await uow.dataset_items.list_for_dataset(dataset.dataset_id)

            search_request = await uow.search_requests.get(search_request_id)
            assert search_request is not None
            search_hits = await uow.search_hits.list_for_request(search_request_id)

            parse_events = await uow.job_events.list_for_job(parse_job_id, limit=20)
            add_events = await uow.job_events.list_for_job(add_job_id, limit=20)

            return _PersistedE2EState(
                object_record=object_record,
                parse_run=parse_run,
                document=document,
                parse_attempts=parse_attempts,
                knowledge_run=knowledge_run,
                dataset=dataset,
                dataset_items=dataset_items,
                search_request=search_request,
                search_hits=search_hits,
                parse_events=parse_events,
                add_events=add_events,
            )
    finally:
        await engine.dispose()


def test_e2e_upload_parse_add_search_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    case_dir = _case_dir("api-e2e-main-path")
    db_path = case_dir / "cortex.db"
    profiles_dir = case_dir / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    (profiles_dir / "e2e_profile.yaml").write_text(
        "\n".join(
            [
                "profile_ref: e2e_profile",
                "display_name: E2E Profile",
                "routing_mode: ordered_fallback",
                "preferred_engine_key: e2e_parse_engine",
                "allowed_engines: [e2e_parse_engine]",
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
            tenant_id="tenant_e2e",
            actor_id="alice",
            scopes=[
                "storage:write",
                "storage:read",
                "storage:download",
                "parse:read",
                "parse:write",
                "knowledge:read",
                "knowledge:write",
                "jobs:read",
            ],
        )
    }

    with _build_client(monkeypatch, db_path, profiles_dir) as built:
        client, runtime = built
        app = cast(FastAPI, client.app)
        assert client.portal is not None

        upload_response = client.post(
            "/v1/storage/uploads",
            headers=headers,
            json={
                "filename": "guide.md",
                "content_type": "text/markdown",
                "size_bytes": 768,
                "metadata": {"workflow": "main-path", "source": "e2e"},
                "tags": ["guide", "e2e"],
                "access_policy": {"access_level": "tenant_shared"},
            },
        )
        upload_id = upload_response.json()["upload_id"]
        object_id = upload_response.json()["object_id"]

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

        parse_job_response = client.post(
            "/v1/parse/jobs",
            headers={**headers, "Idempotency-Key": "e2e-parse-job-001"},
            json={
                "source": {
                    "object_id": object_id,
                    "filename": "guide.md",
                    "canonical_url": "https://example.com/guides/cortex",
                    "mime_type": "text/markdown",
                },
                "engine_id": "e2e_parse_engine",
            },
        )
        parse_job_id = parse_job_response.json()["job_id"]
        pending_parse_result = client.get(
            f"/v1/parse/jobs/{parse_job_id}/result",
            headers=headers,
        )

        parse_worker = ParseWorker(
            session_factory=app.state.session_factory,
            parse_service=app.state.parse_service,
            config=ParseWorkerConfig(worker_id="e2e-parse-worker", lease_seconds=30),
        )
        parse_worker_result = client.portal.call(parse_worker.run_once)

        completed_parse_result = client.get(
            f"/v1/parse/jobs/{parse_job_id}/result",
            headers=headers,
        )
        document_id = completed_parse_result.json()["document"]["document_id"]

        dataset_response = client.post(
            "/v1/knowledge/datasets",
            headers=headers,
            json={
                "dataset_key": "cortex_guide_e2e",
                "display_name": "Cortex Guide E2E",
                "metadata": {"workflow": "main-path"},
                "access_policy": {"access_level": "tenant_shared"},
            },
        )
        dataset_id = dataset_response.json()["dataset_id"]

        add_job_response = client.post(
            "/v1/knowledge/add/jobs",
            headers={**headers, "Idempotency-Key": "e2e-add-job-001"},
            json={
                "dataset_id": dataset_id,
                "inputs": [
                    {
                        "input_type": "object_id",
                        "object_id": object_id,
                        "label": "Uploaded object",
                    },
                    {
                        "input_type": "document_id",
                        "document_id": document_id,
                        "label": "Parsed document",
                    },
                ],
            },
        )
        add_job_id = add_job_response.json()["job_id"]
        pending_add_job = client.get(f"/v1/jobs/{add_job_id}", headers=headers)

        knowledge_worker = KnowledgeWorker(
            session_factory=app.state.session_factory,
            operation_service=KnowledgeOperationService(runtime, app.state.knowledge_service),
            config=KnowledgeWorkerConfig(worker_id="e2e-knowledge-worker", lease_seconds=30),
        )
        knowledge_worker_result = client.portal.call(knowledge_worker.run_once)

        completed_add_job = client.get(f"/v1/jobs/{add_job_id}", headers=headers)
        dataset_after_add = client.get(
            f"/v1/knowledge/datasets/{dataset_id}",
            headers=headers,
        )

        search_response = client.post(
            "/v1/knowledge/search",
            headers=headers,
            json={
                "query_text": "What does the guide say about Cortex workflows?",
                "dataset_ids": [dataset_id],
                "search_type": "GRAPH_COMPLETION",
                "include_graph_paths": True,
                "filters": {
                    "document_ids": [document_id],
                    "object_ids": [object_id],
                },
            },
        )
        search_request_id = search_response.json()["request_id"]

    persisted = asyncio.run(
        _load_persisted_state(
            db_path,
            object_id=object_id,
            parse_job_id=parse_job_id,
            add_job_id=add_job_id,
            search_request_id=search_request_id,
        )
    )

    assert upload_response.status_code == 201
    assert upload_response.json()["upload_mode"] == "single_part"
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "available"
    assert object_response.status_code == 200
    assert object_response.json()["metadata"]["workflow"] == "main-path"
    assert object_response.json()["tags"] == ["guide", "e2e"]
    assert download_response.status_code == 200
    assert X_REQUEST_ID_HEADER in download_response.headers

    assert parse_job_response.status_code == 202
    assert pending_parse_result.status_code == 202
    assert parse_worker_result.status == "succeeded"
    assert completed_parse_result.status_code == 200
    assert completed_parse_result.json()["document"]["title"] == "Cortex Guide"
    assert completed_parse_result.json()["document"]["source_object_id"] == object_id
    assert completed_parse_result.json()["diagnostics"]["selected_engine_key"] == "e2e_parse_engine"

    assert dataset_response.status_code == 201
    assert add_job_response.status_code == 202
    assert pending_add_job.status_code == 200
    assert pending_add_job.json()["status"] == "queued"
    assert knowledge_worker_result.status == "succeeded"
    assert completed_add_job.status_code == 200
    assert completed_add_job.json()["status"] == "succeeded"
    assert dataset_after_add.status_code == 200
    assert dataset_after_add.json()["counters"]["objects"] == 1
    assert dataset_after_add.json()["counters"]["documents"] == 1

    assert search_response.status_code == 200
    assert search_response.json()["dataset_scope"] == [dataset_id]
    assert search_response.json()["answer"].startswith("Cortex guide answer:")
    assert len(search_response.json()["context_items"]) == 1
    assert len(search_response.json()["graph_paths"]) == 1
    assert X_REQUEST_ID_HEADER in search_response.headers

    assert [call[0] for call in runtime.calls] == ["add", "search"]
    assert persisted.object_record.status.value == "available"
    assert persisted.parse_run.job_id == parse_job_id
    assert persisted.parse_run.document_id == document_id
    assert persisted.document.source_object_id == object_id
    assert persisted.document.title == "Cortex Guide"
    assert len(persisted.parse_attempts) == 1
    assert persisted.parse_attempts[0].status.value == "succeeded"
    assert persisted.knowledge_run.result_summary["items_added"] == 2
    assert persisted.dataset.metadata["counters"]["objects"] == 1
    assert persisted.dataset.metadata["counters"]["documents"] == 1
    assert {(item.item_type, item.item_id) for item in persisted.dataset_items} == {
        ("object", object_id),
        ("document", document_id),
    }
    assert persisted.search_request.dataset_scope == [dataset_id]
    assert persisted.search_hits[0].document_id == document_id
    assert persisted.search_hits[0].object_id == object_id
    assert [event.event_type for event in persisted.parse_events] == [
        "parse.job.queued",
        "parse.job.started",
        "parse.job.succeeded",
    ]
    assert [event.event_type for event in persisted.add_events] == [
        "knowledge.add.queued",
        "knowledge.add.started",
        "knowledge.add.succeeded",
    ]
