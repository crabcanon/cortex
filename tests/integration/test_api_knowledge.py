"""Integration tests for knowledge dataset, jobs, and search endpoints."""

import asyncio
import base64
import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import pytest
from cortex_api.main import create_app
from cortex_common import load_settings
from cortex_contracts import X_REQUEST_ID_HEADER
from cortex_db import CortexUnitOfWork, create_database_engine, create_session_factory
from cortex_db.cli import main as db_migrate_main
from cortex_domain import (
    DatasetItemRecord,
    DatasetRecord,
    JobEventRecord,
    JobRecord,
    KnowledgeRunRecord,
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
from cortex_worker_knowledge import KnowledgeWorker, KnowledgeWorkerConfig
from fastapi.testclient import TestClient


@dataclass(slots=True)
class _PersistedKnowledgeState:
    job: JobRecord
    run: KnowledgeRunRecord
    dataset: DatasetRecord
    items: list[DatasetItemRecord]
    events: list[JobEventRecord]


@dataclass(slots=True)
class _PersistedSearchState:
    request: SearchRequestRecord
    hits: list[SearchHitRecord]


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
        item_count = len(inputs) if isinstance(inputs, list) else 0
        return {
            "dataset": dataset,
            "accepted_inputs": item_count,
            "counters": {"objects": 1, "documents": 1},
        }

    async def cognify(self, *, dataset: str, payload: dict[str, object]) -> dict[str, object]:
        self.calls.append(("cognify", dataset, dict(payload)))
        return {
            "dataset": dataset,
            "counters": {"chunks": 3, "graph_nodes": 2, "graph_edges": 1},
        }

    async def memify(self, *, dataset: str, payload: dict[str, object]) -> dict[str, object]:
        self.calls.append(("memify", dataset, dict(payload)))
        return {
            "dataset": dataset,
            "pipeline": payload.get("pipeline"),
            "counters": {"graph_nodes": 1, "graph_edges": 2},
        }

    async def search(self, *, payload: dict[str, object]) -> dict[str, object]:
        self.calls.append(("search", None, dict(payload)))
        query_text = str(payload.get("query_text", ""))
        return {
            "answer": f"answer:{query_text}",
            "context_items": [
                {
                    "rank": 1,
                    "hit_type": "chunk",
                    "score": 0.91,
                    "source_id": "chunk_1",
                    "document_id": "doc_1",
                    "title": "Chunk 1",
                    "snippet": f"context for {query_text}",
                    "citation": {
                        "source_url": "https://example.com/docs",
                        "document_id": "doc_1",
                        "chunk_id": "chunk_1",
                    },
                    "metadata": {"engine": "fake"},
                },
                {
                    "rank": 2,
                    "hit_type": "graph_node",
                    "score": 0.62,
                    "source_id": "node_1",
                    "title": "Entity Node",
                    "snippet": "Graph entity hit",
                    "metadata": {"kind": "entity"},
                },
            ],
            "graph_paths": [
                {
                    "nodes": [
                        {"id": "node_1", "label": "Product"},
                        {"id": "node_2", "label": "Rule"},
                    ],
                    "edges": [
                        {"source": "node_1", "target": "node_2", "type": "related_to"}
                    ],
                }
            ],
        }


@contextmanager
def _build_client(
    monkeypatch: pytest.MonkeyPatch,
    db_path: Path,
    runtime: _FakeKnowledgeRuntime | None = None,
) -> Iterator[tuple[TestClient, _FakeKnowledgeRuntime]]:
    monkeypatch.setenv("CORTEX_DB_DSN", _async_sqlite_url(db_path))
    monkeypatch.setenv("CORTEX_AUTH_MODE", "dev")
    monkeypatch.setenv("CORTEX_OTEL_ENABLED", "false")
    monkeypatch.setenv("CORTEX_COGNEE_ENABLED", "false")
    load_settings.cache_clear()
    app = create_app()
    fake_runtime = runtime or _FakeKnowledgeRuntime()
    with TestClient(app) as client:
        app.state.knowledge_service = KnowledgeDatasetService(fake_runtime)
        app.state.knowledge_job_service = KnowledgeJobControlService()
        app.state.knowledge_search_service = KnowledgeSearchService(fake_runtime)
        yield client, fake_runtime
    load_settings.cache_clear()


async def _run_knowledge_worker_once(
    db_path: Path,
    runtime: _FakeKnowledgeRuntime,
    *,
    worker_id: str,
) -> str:
    engine = create_database_engine(_async_sqlite_url(db_path))
    session_factory = create_session_factory(engine)
    try:
        worker = KnowledgeWorker(
            session_factory=session_factory,
            operation_service=KnowledgeOperationService(
                runtime,
                KnowledgeDatasetService(runtime),
            ),
            config=KnowledgeWorkerConfig(worker_id=worker_id, lease_seconds=30),
        )
        result = await worker.run_once()
        assert result.job_id is not None or result.status == "idle"
        return result.status
    finally:
        await engine.dispose()


async def _load_persisted_knowledge_state(
    db_path: Path,
    job_id: str,
) -> _PersistedKnowledgeState:
    engine = create_database_engine(_async_sqlite_url(db_path))
    session_factory = create_session_factory(engine)
    try:
        async with CortexUnitOfWork(session_factory) as uow:
            job = await uow.jobs.get(job_id)
            assert job is not None
            run = await uow.knowledge_runs.get_by_job(job_id)
            assert run is not None
            dataset = await uow.datasets.get(run.dataset_id)
            assert dataset is not None
            items = await uow.dataset_items.list_for_dataset(run.dataset_id)
            events = await uow.job_events.list_for_job(job_id, limit=20)
            return _PersistedKnowledgeState(
                job=job,
                run=run,
                dataset=dataset,
                items=items,
                events=events,
            )
    finally:
        await engine.dispose()


async def _load_search_state(db_path: Path, request_id: str) -> _PersistedSearchState:
    engine = create_database_engine(_async_sqlite_url(db_path))
    session_factory = create_session_factory(engine)
    try:
        async with CortexUnitOfWork(session_factory) as uow:
            request = await uow.search_requests.get(request_id)
            assert request is not None
            hits = await uow.search_hits.list_for_request(request_id)
            return _PersistedSearchState(request=request, hits=hits)
    finally:
        await engine.dispose()


def test_knowledge_dataset_create_and_get_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = _case_db_path("api-knowledge-dataset")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_knowledge",
            actor_id="alice",
            scopes=["knowledge:write", "knowledge:read"],
        )
    }

    with _build_client(monkeypatch, db_path) as built:
        client, _runtime = built
        create_response = client.post(
            "/v1/knowledge/datasets",
            headers=headers,
            json={
                "dataset_key": "product_docs",
                "display_name": "Product Docs",
                "description": "Primary product knowledge base.",
                "tags": ["docs", "product"],
                "metadata": {"domain": "product"},
            },
        )
        dataset_id = create_response.json()["dataset_id"]
        get_response = client.get(f"/v1/knowledge/datasets/{dataset_id}", headers=headers)

    assert create_response.status_code == 201
    assert create_response.json()["dataset_key"] == "product_docs"
    assert create_response.json()["status"] == "active"
    assert create_response.json()["retention_class"] == "standard"
    assert create_response.json()["tags"] == ["docs", "product"]
    assert create_response.json()["metadata"]["domain"] == "product"
    assert get_response.status_code == 200
    assert get_response.json()["dataset_id"] == dataset_id
    assert get_response.json()["counters"]["documents"] == 0
    assert X_REQUEST_ID_HEADER in get_response.headers


def test_private_dataset_denies_other_actor(monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = _case_db_path("api-knowledge-private")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    owner_headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_knowledge",
            actor_id="alice",
            scopes=["knowledge:write", "knowledge:read"],
        )
    }
    reader_headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_knowledge",
            actor_id="bob",
            scopes=["knowledge:read"],
        )
    }

    with _build_client(monkeypatch, db_path) as built:
        client, _runtime = built
        create_response = client.post(
            "/v1/knowledge/datasets",
            headers=owner_headers,
            json={
                "dataset_key": "private_docs",
                "display_name": "Private Docs",
            },
        )
        dataset_id = create_response.json()["dataset_id"]
        get_response = client.get(f"/v1/knowledge/datasets/{dataset_id}", headers=reader_headers)

    assert create_response.status_code == 201
    assert get_response.status_code == 403
    assert get_response.json()["reason_code"] == "resource_access_denied"


def test_shared_dataset_allows_same_tenant_reader(monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = _case_db_path("api-knowledge-shared")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    owner_headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_knowledge",
            actor_id="alice",
            scopes=["knowledge:write", "knowledge:read"],
        )
    }
    reader_headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_knowledge",
            actor_id="bob",
            scopes=["knowledge:read"],
        )
    }

    with _build_client(monkeypatch, db_path) as built:
        client, _runtime = built
        create_response = client.post(
            "/v1/knowledge/datasets",
            headers=owner_headers,
            json={
                "dataset_key": "shared_docs",
                "display_name": "Shared Docs",
                "access_policy": {"access_level": "tenant_shared"},
            },
        )
        dataset_id = create_response.json()["dataset_id"]
        get_response = client.get(f"/v1/knowledge/datasets/{dataset_id}", headers=reader_headers)

    assert create_response.status_code == 201
    assert get_response.status_code == 200
    assert get_response.json()["dataset_key"] == "shared_docs"


def test_add_job_submit_worker_and_persist_run(monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = _case_db_path("api-knowledge-add")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_knowledge_jobs",
            actor_id="alice",
            scopes=["knowledge:write", "knowledge:read", "jobs:read"],
        ),
        "Idempotency-Key": "knowledge-add-001",
    }

    with _build_client(monkeypatch, db_path) as built:
        client, runtime = built
        dataset_response = client.post(
            "/v1/knowledge/datasets",
            headers=headers,
            json={
                "dataset_key": "kb_docs",
                "display_name": "KB Docs",
                "access_policy": {"access_level": "tenant_shared"},
            },
        )
        dataset_id = dataset_response.json()["dataset_id"]
        accepted_response = client.post(
            "/v1/knowledge/add/jobs",
            headers=headers,
            json={
                "dataset_id": dataset_id,
                "inputs": [
                    {"input_type": "object_id", "object_id": "obj_123", "label": "Raw PDF"},
                    {"input_type": "document_id", "document_id": "doc_123"},
                    {
                        "input_type": "text",
                        "text": "A short note about the product.",
                        "label": "Inline note",
                    },
                ],
            },
        )
        duplicate_response = client.post(
            "/v1/knowledge/add/jobs",
            headers=headers,
            json={
                "dataset_key": "kb_docs",
                "inputs": [
                    {"input_type": "object_id", "object_id": "obj_123", "label": "Raw PDF"},
                    {"input_type": "document_id", "document_id": "doc_123"},
                    {
                        "input_type": "text",
                        "text": "A short note about the product.",
                        "label": "Inline note",
                    },
                ],
            },
        )
        job_id = accepted_response.json()["job_id"]
        pre_status = client.get(f"/v1/jobs/{job_id}", headers=headers)
        worker_status = asyncio.run(
            _run_knowledge_worker_once(
                db_path,
                runtime,
                worker_id="knowledge-worker-success",
            )
        )
        post_status = client.get(f"/v1/jobs/{job_id}", headers=headers)
        events_response = client.get(f"/v1/jobs/{job_id}/events", headers=headers)
        dataset_after = client.get(f"/v1/knowledge/datasets/{dataset_id}", headers=headers)

    persisted = asyncio.run(_load_persisted_knowledge_state(db_path, job_id))

    assert dataset_response.status_code == 201
    assert accepted_response.status_code == 202
    assert accepted_response.json()["status"] == "queued"
    assert duplicate_response.status_code == 202
    assert duplicate_response.json()["job_id"] == job_id
    assert pre_status.status_code == 200
    assert pre_status.json()["status"] == "queued"
    assert worker_status == "succeeded"
    assert post_status.status_code == 200
    assert post_status.json()["status"] == "succeeded"
    assert dataset_after.json()["counters"]["objects"] == 1
    assert dataset_after.json()["counters"]["documents"] == 1
    assert [event["event_type"] for event in events_response.json()] == [
        "knowledge.add.queued",
        "knowledge.add.started",
        "knowledge.add.succeeded",
    ]
    assert len(runtime.calls) == 1
    assert runtime.calls[0][0] == "add"
    assert persisted.run.result_summary["items_added"] == 3
    assert len(persisted.items) == 3
    assert persisted.dataset.metadata["counters"]["objects"] == 1


def test_cognify_and_memify_jobs_update_run_trajectory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = _case_db_path("api-knowledge-cognify-memify")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_knowledge_graph",
            actor_id="alice",
            scopes=["knowledge:write", "knowledge:read", "jobs:read"],
        )
    }

    with _build_client(monkeypatch, db_path) as built:
        client, runtime = built
        dataset_response = client.post(
            "/v1/knowledge/datasets",
            headers=headers,
            json={
                "dataset_key": "graph_docs",
                "display_name": "Graph Docs",
                "access_policy": {"access_level": "tenant_shared"},
            },
        )
        dataset_id = dataset_response.json()["dataset_id"]
        cognify_response = client.post(
            "/v1/knowledge/cognify/jobs",
            headers=headers,
            json={"dataset_id": dataset_id},
        )
        cognify_job_id = cognify_response.json()["job_id"]
        memify_response = client.post(
            "/v1/knowledge/memify/jobs",
            headers=headers,
            json={"dataset_id": dataset_id, "pipeline": "triplet_embeddings"},
        )
        memify_job_id = memify_response.json()["job_id"]

        first_status = asyncio.run(
            _run_knowledge_worker_once(db_path, runtime, worker_id="knowledge-worker-1")
        )
        second_status = asyncio.run(
            _run_knowledge_worker_once(db_path, runtime, worker_id="knowledge-worker-2")
        )
        cognify_job = client.get(f"/v1/jobs/{cognify_job_id}", headers=headers)
        memify_job = client.get(f"/v1/jobs/{memify_job_id}", headers=headers)
        dataset_after = client.get(f"/v1/knowledge/datasets/{dataset_id}", headers=headers)
        memify_events = client.get(f"/v1/jobs/{memify_job_id}/events", headers=headers)

    cognify_state = asyncio.run(_load_persisted_knowledge_state(db_path, cognify_job_id))
    memify_state = asyncio.run(_load_persisted_knowledge_state(db_path, memify_job_id))

    assert dataset_response.status_code == 201
    assert cognify_response.status_code == 202
    assert memify_response.status_code == 202
    assert first_status == "succeeded"
    assert second_status == "succeeded"
    assert cognify_job.json()["status"] == "succeeded"
    assert memify_job.json()["status"] == "succeeded"
    assert dataset_after.json()["counters"]["chunks"] == 3
    assert dataset_after.json()["counters"]["graph_nodes"] == 3
    assert dataset_after.json()["counters"]["graph_edges"] == 3
    assert cognify_state.run.result_summary["counter_delta"]["chunks"] == 3
    assert memify_state.run.result_summary["pipeline"] == "triplet_embeddings"
    assert [event["event_type"] for event in memify_events.json()] == [
        "knowledge.memify.queued",
        "knowledge.memify.started",
        "knowledge.memify.succeeded",
    ]
    assert [call[0] for call in runtime.calls] == ["cognify", "memify"]


def test_search_persists_request_hits_and_graph_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = _case_db_path("api-knowledge-search")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_knowledge_search",
            actor_id="alice",
            scopes=["knowledge:write", "knowledge:read"],
        )
    }

    with _build_client(monkeypatch, db_path) as built:
        client, runtime = built
        dataset_response = client.post(
            "/v1/knowledge/datasets",
            headers=headers,
            json={
                "dataset_key": "search_docs",
                "display_name": "Search Docs",
                "access_policy": {"access_level": "tenant_shared"},
            },
        )
        dataset_id = dataset_response.json()["dataset_id"]
        search_response = client.post(
            "/v1/knowledge/search",
            headers=headers,
            json={
                "query_text": "what is the coding rule",
                "dataset_ids": [dataset_id],
                "search_type": "GRAPH_COMPLETION",
                "include_graph_paths": True,
            },
        )

    persisted = asyncio.run(_load_search_state(db_path, search_response.json()["request_id"]))

    assert dataset_response.status_code == 201
    assert search_response.status_code == 200
    assert search_response.json()["answer"] == "answer:what is the coding rule"
    assert search_response.json()["dataset_scope"] == [dataset_id]
    assert len(search_response.json()["context_items"]) == 2
    assert len(search_response.json()["graph_paths"]) == 1
    assert runtime.calls[-1][0] == "search"
    assert persisted.request.dataset_scope == [dataset_id]
    assert persisted.request.answer_text == "answer:what is the coding rule"
    assert len(persisted.hits) == 2
    assert persisted.hits[0].citation["chunk_id"] == "chunk_1"


def test_search_denies_private_dataset_for_other_actor(monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = _case_db_path("api-knowledge-search-private")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    owner_headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_knowledge_search",
            actor_id="alice",
            scopes=["knowledge:write", "knowledge:read"],
        )
    }
    reader_headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_knowledge_search",
            actor_id="bob",
            scopes=["knowledge:read"],
        )
    }

    with _build_client(monkeypatch, db_path) as built:
        client, _runtime = built
        dataset_response = client.post(
            "/v1/knowledge/datasets",
            headers=owner_headers,
            json={
                "dataset_key": "search_private_docs",
                "display_name": "Search Private Docs",
            },
        )
        dataset_id = dataset_response.json()["dataset_id"]
        search_response = client.post(
            "/v1/knowledge/search",
            headers=reader_headers,
            json={
                "query_text": "should fail",
                "dataset_ids": [dataset_id],
            },
        )

    assert dataset_response.status_code == 201
    assert search_response.status_code == 403
    assert search_response.json()["reason_code"] == "resource_access_denied"
