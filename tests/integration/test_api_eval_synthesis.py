"""Integration tests for evaluation and synthesis endpoints."""

import asyncio
import base64
import json
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

import pytest
from cortex_api.main import create_app
from cortex_common import load_settings, utc_now
from cortex_contracts import (
    EvalEngineDescriptor,
    EvalMetricResult,
    EvalRunResult,
    EvalSampleCounters,
    EvalScoreCard,
    EvalSyncRequest,
    EvalType,
    MultipartPartUpload,
    PresignedRequestDescriptor,
    StoredArtifactRef,
    SynthesisEngineDescriptor,
    SynthesisQualityResult,
    SynthesisRunResult,
    SynthesisSummary,
    SynthesisSyncRequest,
    SynthesisType,
)
from cortex_db import CortexUnitOfWork, create_database_engine, create_session_factory
from cortex_db.cli import main as db_migrate_main
from cortex_domain import AccessLevel, DatasetItemRecord, DatasetRecord
from cortex_evaluation import (
    EvaluationEngineProtocol,
    EvaluationEngineRegistry,
    EvaluationJobControlService,
    EvaluationService,
    default_eval_metric_catalog,
)
from cortex_storage import StorageService
from cortex_synthesis import (
    SynthesisEngineProtocol,
    SynthesisEngineRegistry,
    SynthesisJobControlService,
    SynthesisService,
)
from cortex_worker_evaluation import EvaluationWorker, EvaluationWorkerConfig
from cortex_worker_synthesis import SynthesisWorker, SynthesisWorkerConfig
from fastapi import FastAPI
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


class _FakeObjectStoreClient:
    def __init__(self) -> None:
        self.buckets: set[str] = set()
        self.objects: dict[tuple[str, str], bytes] = {}
        self.metadata: dict[tuple[str, str], dict[str, Any]] = {}

    def ensure_bucket(self, bucket_name: str) -> None:
        self.buckets.add(bucket_name)

    def put_object(
        self,
        *,
        bucket_name: str,
        object_key: str,
        body: bytes,
        content_type: str,
        metadata: dict[str, str],
    ) -> dict[str, Any]:
        self.buckets.add(bucket_name)
        self.objects[(bucket_name, object_key)] = body
        self.metadata[(bucket_name, object_key)] = {
            "ContentType": content_type,
            "ContentLength": len(body),
            "Metadata": metadata,
        }
        return {"ETag": f"etag-{object_key}", "VersionId": "version-direct-001"}

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
        del object_key, content_type, metadata
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
        del bucket_name, object_key
        return {"ETag": f"etag-{provider_upload_id}-{len(parts)}", "VersionId": "version-001"}

    def head_object(
        self,
        *,
        bucket_name: str,
        object_key: str,
    ) -> dict[str, Any]:
        return dict(self.metadata.get((bucket_name, object_key), {}))

    def get_object_bytes(
        self,
        *,
        bucket_name: str,
        object_key: str,
    ) -> bytes:
        return self.objects[(bucket_name, object_key)]

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


class _FakeDeepEvalEngine(EvaluationEngineProtocol):
    @property
    def descriptor(self) -> EvalEngineDescriptor:
        return EvalEngineDescriptor(
            engine_id="deepeval",
            display_name="DeepEval",
            provider="Confident AI / OSS",
            availability_status="available",
            execution_modes=["sync", "async"],
            supported_eval_types=[
                EvalType.RAG,
                EvalType.AGENTIC,
                EvalType.MULTI_TURN,
                EvalType.CUSTOM,
            ],
            supported_metric_prefixes=["rag", "agent", "dialog", "quality", "safety", "custom"],
            default_profiles=["rag_default"],
        )

    async def run(self, request: EvalSyncRequest) -> EvalRunResult:
        sample_total = len(request.input.test_cases) or 1
        return EvalRunResult(
            name=request.name,
            eval_type=request.eval_type,
            engine_id="deepeval",
            profile_key=request.profile_key,
            status="succeeded",
            source_summary={
                "input_type": request.input.type,
                "test_case_count": len(request.input.test_cases),
            },
            target_summary={"target_type": request.target.type if request.target else None},
            summary=EvalScoreCard(
                overall_passed=True,
                composite_score=0.93,
                metric_count=len(request.metrics),
                passed_metric_count=len(request.metrics),
                failed_metric_count=0,
                summary_by_namespace={"rag": 0.93},
            ),
            metrics=[
                EvalMetricResult(
                    metric_key=metric.metric_key,
                    display_name=metric.metric_key,
                    status="passed",
                    score=0.93,
                    threshold=metric.threshold,
                    engine_id="deepeval",
                )
                for metric in request.metrics
            ],
            samples=EvalSampleCounters(total=sample_total, passed=sample_total, failed=0),
            started_at=utc_now(),
            completed_at=utc_now(),
        )


class _FakeDeepEvalSynthEngine(SynthesisEngineProtocol):
    @property
    def descriptor(self) -> SynthesisEngineDescriptor:
        return SynthesisEngineDescriptor(
            engine_id="deepeval",
            display_name="DeepEval Synthesizer",
            provider="Confident AI / OSS",
            availability_status="available",
            supported_synthesis_types=[
                SynthesisType.RAG_GOLDENS,
                SynthesisType.QA_PAIRS,
                SynthesisType.CONVERSATION_GOLDENS,
                SynthesisType.AGENT_TRAJECTORIES,
                SynthesisType.CUSTOM,
            ],
            supported_source_types=["documents", "object", "objects", "dataset", "inline_records"],
            output_formats=["json", "jsonl"],
            default_profiles=["rag_goldens_default"],
        )

    async def run(self, request: SynthesisSyncRequest) -> SynthesisRunResult:
        sample_count = request.config.sample_count or 4
        quality_gates = [
            SynthesisQualityResult(
                metric_key=gate.metric_key,
                status="passed",
                threshold=gate.threshold,
                score=0.92,
            )
            for gate in request.config.quality_gates
        ]
        return SynthesisRunResult(
            name=request.name,
            synthesis_type=request.synthesis_type,
            engine_id="deepeval",
            profile_key=request.profile_key,
            status="succeeded",
            source_summary={"source_type": request.source.type},
            summary=SynthesisSummary(
                requested_sample_count=sample_count,
                output_sample_count=sample_count,
                quality_score=0.92,
                privacy_score=0.98,
                notes=["synthetic preview generated by test double"],
            ),
            quality_gates=quality_gates,
            outputs=[
                StoredArtifactRef(
                    object_id="obj_preview_eval_dataset",
                    label="preview",
                    content_type="application/json",
                    format=request.output.output_format or "json",
                    description="Synthetic preview artifact.",
                )
            ],
            output_dataset_id="ds_synth_preview",
            started_at=utc_now(),
            completed_at=utc_now(),
        )


def _build_evaluation_service() -> EvaluationService:
    registry = EvaluationEngineRegistry()
    registry.register(_FakeDeepEvalEngine())
    return EvaluationService(
        registry=registry,
        metric_catalog=default_eval_metric_catalog(),
        default_profile_ref="rag_default",
    )


def _build_synthesis_service() -> SynthesisService:
    registry = SynthesisEngineRegistry()
    registry.register(_FakeDeepEvalSynthEngine())
    return SynthesisService(registry=registry, default_profile_ref="rag_goldens_default")


@contextmanager
def _build_client(
    monkeypatch: pytest.MonkeyPatch,
    db_path: Path,
) -> Iterator[TestClient]:
    monkeypatch.setenv("CORTEX_DB_DSN", _async_sqlite_url(db_path))
    monkeypatch.setenv("CORTEX_AUTH_MODE", "dev")
    monkeypatch.setenv("CORTEX_ENV", "local")
    monkeypatch.setenv("CORTEX_OTEL_ENABLED", "false")
    monkeypatch.setenv("CORTEX_COGNEE_ENABLED", "false")
    monkeypatch.setenv("CORTEX_CRAWL4AI_SKIP_PROBE", "1")
    load_settings.cache_clear()
    app = create_app()
    with TestClient(app) as client:
        runtime_app = cast(FastAPI, client.app)
        runtime_app.state.evaluation_service = _build_evaluation_service()
        runtime_app.state.evaluation_job_service = EvaluationJobControlService()
        runtime_app.state.synthesis_service = _build_synthesis_service()
        runtime_app.state.synthesis_job_service = SynthesisJobControlService()
        yield client
    load_settings.cache_clear()


async def _run_evaluation_worker_once(db_path: Path) -> str:
    engine = create_database_engine(_async_sqlite_url(db_path))
    session_factory = create_session_factory(engine)
    try:
        worker = EvaluationWorker(
            session_factory=session_factory,
            evaluation_service=_build_evaluation_service(),
            storage_service=StorageService(
                load_settings().s3,
                object_store=_FakeObjectStoreClient(),
            ),
            config=EvaluationWorkerConfig(worker_id="eval-worker", lease_seconds=30),
        )
        result = await worker.run_once()
        return result.status
    finally:
        await engine.dispose()


async def _run_synthesis_worker_once(db_path: Path) -> str:
    engine = create_database_engine(_async_sqlite_url(db_path))
    session_factory = create_session_factory(engine)
    try:
        worker = SynthesisWorker(
            session_factory=session_factory,
            synthesis_service=_build_synthesis_service(),
            storage_service=StorageService(
                load_settings().s3,
                object_store=_FakeObjectStoreClient(),
            ),
            config=SynthesisWorkerConfig(worker_id="synth-worker", lease_seconds=30),
        )
        result = await worker.run_once()
        return result.status
    finally:
        await engine.dispose()


async def _seed_eval_dataset(db_path: Path, *, tenant_id: str, dataset_id: str) -> None:
    engine = create_database_engine(_async_sqlite_url(db_path))
    session_factory = create_session_factory(engine)
    try:
        async with CortexUnitOfWork(session_factory) as uow:
            await uow.datasets.add(
                DatasetRecord(
                    dataset_id=dataset_id,
                    tenant_id=tenant_id,
                    dataset_key="docs-rag-eval",
                    display_name="Docs RAG Eval",
                    access_level=AccessLevel.TENANT_PRIVATE,
                    created_by="alice",
                )
            )
            await uow.dataset_items.add(
                DatasetItemRecord(
                    dataset_id=dataset_id,
                    item_type="eval_case",
                    item_id="case-001",
                    source_stage="golden",
                    metadata={
                        "question": "What does Cortex provide?",
                        "answer": (
                            "Cortex provides parse, storage, knowledge, eval, "
                            "and synthesis APIs."
                        ),
                        "expected": "A unified AI data and evaluation API plane.",
                        "contexts": [
                            "Cortex includes parse, storage, knowledge, evaluation, and synthesis."
                        ],
                    },
                )
            )
    finally:
        await engine.dispose()


def test_evaluation_api_lists_catalog_and_runs_sync_eval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = _case_db_path("api-evaluation-sync")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_eval",
            actor_id="alice",
            scopes=["eval:read", "eval:write"],
        )
    }

    with _build_client(monkeypatch, db_path) as client:
        engines_response = client.get("/v1/eval/engines", headers=headers)
        metrics_response = client.get(
            "/v1/eval/metrics",
            headers=headers,
            params={"evalType": "rag", "engineId": "deepeval"},
        )
        sync_response = client.post(
            "/v1/eval/sync",
            headers=headers,
            json={
                "name": "docs-rag-eval",
                "eval_type": "rag",
                "engine_id": "auto",
                "input": {
                    "type": "dataset",
                    "dataset_id": "ds_docs_eval",
                    "field_mapping": {
                        "user_input": "question",
                        "actual_output": "answer",
                        "retrieval_contexts": "contexts",
                    },
                },
                "target": {
                    "type": "api",
                    "endpoint_url": "https://example.com/query",
                },
                "metrics": [
                    {"metric_key": "rag.faithfulness", "threshold": 0.8},
                    {"metric_key": "rag.answer_relevance", "threshold": 0.7},
                ],
            },
        )

    assert engines_response.status_code == 200
    assert [engine["engine_id"] for engine in engines_response.json()["engines"]] == ["deepeval"]
    assert metrics_response.status_code == 200
    assert metrics_response.json()["metrics"][0]["metric_key"].startswith("rag.")
    assert sync_response.status_code == 200
    assert sync_response.json()["engine_id"] == "deepeval"
    assert sync_response.json()["status"] == "succeeded"
    assert sync_response.json()["summary"]["overall_passed"] is True


def test_evaluation_job_submit_worker_and_result(monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = _case_db_path("api-evaluation-async")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_eval_jobs",
            actor_id="alice",
            scopes=["eval:read", "eval:write", "jobs:read"],
        ),
        "Idempotency-Key": "eval-job-001",
    }
    asyncio.run(
        _seed_eval_dataset(
            db_path,
            tenant_id="tenant_eval_jobs",
            dataset_id="ds_agent_eval",
        )
    )

    with _build_client(monkeypatch, db_path) as client:
        accepted_response = client.post(
            "/v1/eval/jobs",
            headers=headers,
            json={
                "name": "agent-eval",
                "eval_type": "agentic",
                "engine_id": "auto",
                "input": {"type": "dataset", "dataset_id": "ds_agent_eval"},
                "metrics": [
                    {"metric_key": "agent.task_completion", "threshold": 0.8},
                    {"metric_key": "agent.tool_correctness", "threshold": 0.8},
                ],
            },
        )
        duplicate_response = client.post(
            "/v1/eval/jobs",
            headers=headers,
            json={
                "name": "agent-eval",
                "eval_type": "agentic",
                "engine_id": "auto",
                "input": {"type": "dataset", "dataset_id": "ds_agent_eval"},
                "metrics": [
                    {"metric_key": "agent.task_completion", "threshold": 0.8},
                    {"metric_key": "agent.tool_correctness", "threshold": 0.8},
                ],
            },
        )
        job_id = accepted_response.json()["job_id"]
        pending_result = client.get(f"/v1/eval/jobs/{job_id}/result", headers=headers)
        worker_status = asyncio.run(_run_evaluation_worker_once(db_path))
        completed_result = client.get(f"/v1/eval/jobs/{job_id}/result", headers=headers)
        events_response = client.get(f"/v1/jobs/{job_id}/events", headers=headers)

    assert accepted_response.status_code == 202
    assert duplicate_response.status_code == 202
    assert duplicate_response.json()["job_id"] == job_id
    assert pending_result.status_code == 409
    assert worker_status == "succeeded"
    assert completed_result.status_code == 200
    assert completed_result.json()["eval_run_id"].startswith("erun_")
    assert completed_result.json()["engine_id"] == "deepeval"
    assert completed_result.json()["source_summary"] == {
        "input_type": "inline_test_cases",
        "test_case_count": 1,
    }
    assert completed_result.json()["artifacts"][0]["label"] == "evaluation_report"
    assert completed_result.json()["artifacts"][0]["object_id"].startswith("obj_")
    assert [event["event_type"] for event in events_response.json()] == [
        "evaluation.job.queued",
        "evaluation.job.started",
        "evaluation.job.succeeded",
    ]


def test_synthesis_api_lists_catalog_and_runs_sync_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = _case_db_path("api-synthesis-sync")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_synth",
            actor_id="alice",
            scopes=["synthesis:read", "synthesis:write"],
        )
    }

    with _build_client(monkeypatch, db_path) as client:
        engines_response = client.get("/v1/synthesis/engines", headers=headers)
        sync_response = client.post(
            "/v1/synthesis/sync",
            headers=headers,
            json={
                "name": "rag-golden-generation",
                "synthesis_type": "rag_goldens",
                "engine_id": "auto",
                "source": {
                    "type": "documents",
                    "documents": [
                        "Cortex supports parse, storage, knowledge, evaluation, and synthesis."
                    ],
                },
                "config": {
                    "sample_count": 5,
                    "quality_gates": [
                        {"metric_key": "quality.correctness", "threshold": 0.8}
                    ],
                },
                "output": {"output_format": "json"},
            },
        )

    assert engines_response.status_code == 200
    assert [engine["engine_id"] for engine in engines_response.json()["engines"]] == ["deepeval"]
    assert sync_response.status_code == 200
    assert sync_response.json()["engine_id"] == "deepeval"
    assert sync_response.json()["summary"]["output_sample_count"] == 5
    assert sync_response.json()["outputs"][0]["object_id"] == "obj_preview_eval_dataset"


def test_synthesis_job_submit_worker_and_result(monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = _case_db_path("api-synthesis-async")
    db_migrate_main(["upgrade", "head", "--db-url", _sync_sqlite_url(db_path)])
    headers = {
        "Authorization": _dev_bearer_token(
            tenant_id="tenant_synth_jobs",
            actor_id="alice",
            scopes=["synthesis:read", "synthesis:write", "jobs:read"],
        ),
        "Idempotency-Key": "synth-job-001",
    }

    with _build_client(monkeypatch, db_path) as client:
        accepted_response = client.post(
            "/v1/synthesis/jobs",
            headers=headers,
            json={
                "name": "qa-synthesis",
                "synthesis_type": "qa_pairs",
                "engine_id": "auto",
                "source": {
                    "type": "inline_records",
                    "inline_records": [
                        {
                            "document": "Cortex uses pluggable engines for parsing and evaluation."
                        }
                    ],
                },
                "config": {
                    "sample_count": 3,
                    "quality_gates": [
                        {"metric_key": "quality.correctness", "threshold": 0.8}
                    ],
                },
                "output": {"output_format": "jsonl"},
            },
        )
        duplicate_response = client.post(
            "/v1/synthesis/jobs",
            headers=headers,
            json={
                "name": "qa-synthesis",
                "synthesis_type": "qa_pairs",
                "engine_id": "auto",
                "source": {
                    "type": "inline_records",
                    "inline_records": [
                        {
                            "document": "Cortex uses pluggable engines for parsing and evaluation."
                        }
                    ],
                },
                "config": {
                    "sample_count": 3,
                    "quality_gates": [
                        {"metric_key": "quality.correctness", "threshold": 0.8}
                    ],
                },
                "output": {"output_format": "jsonl"},
            },
        )
        job_id = accepted_response.json()["job_id"]
        pending_result = client.get(f"/v1/synthesis/jobs/{job_id}/result", headers=headers)
        worker_status = asyncio.run(_run_synthesis_worker_once(db_path))
        completed_result = client.get(f"/v1/synthesis/jobs/{job_id}/result", headers=headers)
        events_response = client.get(f"/v1/jobs/{job_id}/events", headers=headers)

    assert accepted_response.status_code == 202
    assert duplicate_response.status_code == 202
    assert duplicate_response.json()["job_id"] == job_id
    assert pending_result.status_code == 409
    assert worker_status == "succeeded"
    assert completed_result.status_code == 200
    assert completed_result.json()["synthesis_run_id"].startswith("srun_")
    assert completed_result.json()["output_dataset_id"] == "ds_synth_preview"
    assert any(
        output["label"] == "synthesis_output"
        and output["object_id"].startswith("obj_")
        for output in completed_result.json()["outputs"]
    )
    assert [event["event_type"] for event in events_response.json()] == [
        "synthesis.job.queued",
        "synthesis.job.started",
        "synthesis.job.succeeded",
    ]
