"""Phase B contract tests for shared foundation modules."""

import logging
from datetime import UTC, datetime

import pytest
from cortex_common import PaginationWindow, ValidationError, json_dumps, json_loads, load_settings
from cortex_common.idempotency import normalize_idempotency_key
from cortex_common.ids import new_prefixed_id
from cortex_contracts import (
    AccessLevel as ContractAccessLevel,
)
from cortex_contracts import (
    AccessPolicy as ContractAccessPolicy,
)
from cortex_contracts import (
    AddJobRequest,
    AuditFields,
    Citation,
    CognifyJobRequest,
    DatasetCounters,
    DatasetRetentionClass,
    FallbackMode,
    GraphPath,
    JobAccepted,
    JobStatus,
    JobType,
    KnowledgeDataset,
    KnowledgeDatasetCreateRequest,
    KnowledgeDatasetStatus,
    KnowledgeInput,
    KnowledgeInputType,
    MemifyJobRequest,
    MemifyPipeline,
    PaginationEnvelope,
    ParseAttemptStatus,
    ParseBatchJobAccepted,
    ParseBatchResult,
    ParsedDocument,
    ParseDiagnostics,
    ParseEngineAttempt,
    ParseEngineDeploymentMode,
    ParseEngineDescriptor,
    ParseEngineStatus,
    ParseInputKind,
    ParseJobSubmitRequest,
    ParseResult,
    ParserProfile,
    ParseSource,
    ParseSubmitRequest,
    ParseSyncRequest,
    ParseTimingSummary,
    ProblemDetails,
    SearchHit,
    SearchHitType,
    SearchRequest,
    SearchResponse,
    StorageObject,
    StorageObjectStatus,
    StorageUploadCreateRequest,
    UploadMode,
)
from cortex_domain import (
    AccessLevel,
    DatasetRecord,
    DecisionEffect,
    JobRecord,
)
from cortex_domain import (
    JobStatus as DomainJobStatus,
)
from cortex_domain import (
    JobType as DomainJobType,
)
from cortex_observability import MetricsFacade, configure_telemetry, get_trace_context
from cortex_observability.logging import install_logging_correlation


def test_settings_load_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_HOST", "0.0.0.0")
    monkeypatch.setenv("CORTEX_DB_DSN", "sqlite+aiosqlite:///./test.db")
    load_settings.cache_clear()

    settings = load_settings()

    assert settings.app.host == "0.0.0.0"
    assert settings.database.dsn == "sqlite+aiosqlite:///./test.db"
    load_settings.cache_clear()


def test_id_helpers_and_json_helpers() -> None:
    generated = new_prefixed_id("Parse Job")
    hashed = normalize_idempotency_key("x" * 128)
    payload = {"b": 2, "a": 1}

    assert generated.startswith("parse_job_")
    assert len(hashed) == 64
    assert json_dumps(payload) == '{"a":1,"b":2}'
    assert json_loads('{"ok":true}') == {"ok": True}


def test_empty_idempotency_key_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        normalize_idempotency_key("   ")


def test_pagination_and_contract_models() -> None:
    window = PaginationWindow.from_params(offset=-10, limit=999)
    accepted = JobAccepted(
        job_id="job_123",
        job_type=JobType.PARSE,
        status=JobStatus.QUEUED,
        submitted_at=datetime(2026, 4, 12, 13, 0, tzinfo=UTC),
        poll_url="/v1/jobs/job_123",
    )
    envelope = PaginationEnvelope[JobAccepted](items=[accepted], offset=0, limit=50, total=1)
    problem = ProblemDetails(
        title="Forbidden",
        status=403,
        required_permissions=["storage.objects.read"],
    )

    assert window.offset == 0
    assert window.limit == 500
    assert envelope.total == 1
    assert problem.required_permissions == ["storage.objects.read"]


def test_domain_records_capture_access_and_job_metadata() -> None:
    dataset = DatasetRecord(
        dataset_id="dst_123",
        tenant_id="tenant_1",
        dataset_key="finance",
        display_name="Finance",
        access_level=AccessLevel.RESTRICTED,
        metadata={"tier": "gold"},
    )
    job = JobRecord(
        job_id="job_123",
        tenant_id="tenant_1",
        job_type=DomainJobType.KNOWLEDGE_ADD,
        status=DomainJobStatus.RUNNING,
        operation_name="dataset.add",
        submitted_at=datetime.now(UTC),
    )

    assert dataset.access_level is AccessLevel.RESTRICTED
    assert dataset.metadata["tier"] == "gold"
    assert job.operation_name == "dataset.add"


def test_telemetry_bootstrap_trace_context_and_metric_reuse() -> None:
    runtime = configure_telemetry(
        "cortex-tests",
        load_settings().telemetry.model_copy(update={"enabled": False}),
    )
    tracer = runtime.tracer_provider.get_tracer("tests.foundation")
    metrics_facade = MetricsFacade("tests.foundation")

    counter = metrics_facade.counter("requests_total")
    histogram = metrics_facade.histogram("latency_ms")

    with tracer.start_as_current_span("foundation-span"):
        trace_context = get_trace_context()
        logger = install_logging_correlation(logging.getLogger("cortex.tests.foundation"))
        record = logger.makeRecord(
            logger.name,
            logging.INFO,
            __file__,
            1,
            "hello",
            args=(),
            exc_info=None,
        )
        for logging_filter in logger.filters:
            logging_filter.filter(record)

    assert trace_context["trace_id"] is not None
    assert trace_context["span_id"] is not None
    assert record.__dict__["trace_id"] == trace_context["trace_id"]
    assert metrics_facade.counter("requests_total") is counter
    assert metrics_facade.histogram("latency_ms") is histogram


def test_decision_effect_enum_stability() -> None:
    assert DecisionEffect.ALLOW == "allow"


def test_storage_contract_models_capture_upload_and_object_metadata() -> None:
    create_request = StorageUploadCreateRequest(
        filename="sample.pdf",
        content_type="application/pdf",
        size_bytes=1024,
        metadata={"source": "user"},
        tags=["finance"],
        upload_mode=UploadMode.SINGLE_PART,
        access_policy=ContractAccessPolicy(access_level=ContractAccessLevel.RESTRICTED),
    )
    storage_object = StorageObject(
        object_id="obj_123",
        filename="sample.pdf",
        content_type="application/pdf",
        size_bytes=1024,
        status=StorageObjectStatus.AVAILABLE,
        metadata={"source": "user"},
        tags=["finance"],
        access_policy=ContractAccessPolicy(access_level=ContractAccessLevel.RESTRICTED),
        audit=AuditFields(
            created_at=datetime(2026, 4, 13, 10, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 13, 10, 0, tzinfo=UTC),
        ),
    )

    assert create_request.access_policy is not None
    assert create_request.access_policy.access_level is ContractAccessLevel.RESTRICTED
    assert storage_object.status is StorageObjectStatus.AVAILABLE
    assert storage_object.tags == ["finance"]


def test_knowledge_contract_models_capture_dataset_metadata() -> None:
    create_request = KnowledgeDatasetCreateRequest(
        dataset_key="finance_docs",
        display_name="Finance Docs",
        tags=["finance"],
        retention_class=DatasetRetentionClass.DURABLE,
        access_policy=ContractAccessPolicy(access_level=ContractAccessLevel.TENANT_SHARED),
    )
    dataset = KnowledgeDataset(
        dataset_id="dataset_123",
        dataset_key="finance_docs",
        display_name="Finance Docs",
        status=KnowledgeDatasetStatus.ACTIVE,
        tags=["finance"],
        retention_class=DatasetRetentionClass.DURABLE,
        counters=DatasetCounters(documents=3, chunks=8),
        access_policy=ContractAccessPolicy(access_level=ContractAccessLevel.TENANT_SHARED),
        audit=AuditFields(
            created_at=datetime(2026, 4, 14, 21, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 14, 21, 0, tzinfo=UTC),
        ),
    )

    assert create_request.retention_class is DatasetRetentionClass.DURABLE
    assert dataset.status is KnowledgeDatasetStatus.ACTIVE
    assert dataset.counters.documents == 3


def test_knowledge_job_and_search_contract_models_capture_request_shapes() -> None:
    add_request = AddJobRequest(
        dataset_key="finance_docs",
        inputs=[
            KnowledgeInput(input_type=KnowledgeInputType.OBJECT_ID, object_id="obj_123"),
            KnowledgeInput(input_type=KnowledgeInputType.TEXT, text="A short inline note."),
        ],
    )
    cognify_request = CognifyJobRequest(dataset_id="dataset_123")
    memify_request = MemifyJobRequest(
        dataset_id="dataset_123",
        pipeline=MemifyPipeline.TRIPLET_EMBEDDINGS,
    )
    search_request = SearchRequest(
        query_text="what changed",
        dataset_ids=["dataset_123"],
        include_graph_paths=True,
    )
    search_response = SearchResponse(
        request_id="sreq_123",
        search_type=search_request.search_type,
        dataset_scope=["dataset_123"],
        answer="One answer",
        context_items=[
            SearchHit(
                rank=1,
                hit_type=SearchHitType.CHUNK,
                score=0.99,
                source_id="chunk_1",
                citation=Citation(document_id="doc_123", chunk_id="chunk_1"),
            )
        ],
        graph_paths=[GraphPath(nodes=[{"id": "n1"}], edges=[{"source": "n1", "target": "n2"}])],
        created_at=datetime(2026, 4, 14, 22, 0, tzinfo=UTC),
        latency_ms=12,
    )

    assert add_request.inputs[0].object_id == "obj_123"
    assert cognify_request.graph_prompt_profile == "default"
    assert memify_request.pipeline == "triplet_embeddings"
    assert search_request.dataset_ids == ["dataset_123"]
    assert search_response.context_items[0].citation is not None
    assert search_response.context_items[0].citation.chunk_id == "chunk_1"
    assert search_response.graph_paths[0].nodes[0]["id"] == "n1"


def test_parse_contract_models_capture_request_and_result_shapes() -> None:
    public_request = ParseSubmitRequest(
        sources=["https://example.com/docs"],
        engine_id="auto",
    )
    public_job_request = ParseJobSubmitRequest(
        sources=["cortex://objects/obj_123"],
        engine_id="auto",
        scene="document_ai",
    )
    request = ParseSyncRequest(
        source=ParseSource(
            input_kind=ParseInputKind.URL,
            url="https://example.com/docs",
        )
    )
    engine = ParseEngineDescriptor(
        engine_key="crawl4ai",
        display_name="Crawl4AI",
        engine_family="web_interactive",
        deployment_mode=ParseEngineDeploymentMode.LOCAL,
        status=ParseEngineStatus.ACTIVE,
        supported_source_types=["url"],
        capabilities=["interactive_web"],
    )
    profile = ParserProfile(
        profile_ref="auto_default",
        display_name="Auto Default",
        preferred_engine_key="crawl4ai",
    )
    result = ParseResult(
        job_id="job_123",
        document=ParsedDocument(
            document_id="doc_123",
            source_type=ParseInputKind.URL,
            source_format="text/html",
            markdown="# Example",
            audit=AuditFields(
                created_at=datetime(2026, 4, 14, 9, 0, tzinfo=UTC),
                updated_at=datetime(2026, 4, 14, 9, 0, tzinfo=UTC),
            ),
        ),
        diagnostics=ParseDiagnostics(
            selected_engine_key="crawl4ai",
            fallback_used=True,
            engine_attempts=[
                ParseEngineAttempt(
                    attempt_no=1,
                    engine_key="jina_reader",
                    status=ParseAttemptStatus.FAILED,
                ),
                ParseEngineAttempt(
                    attempt_no=2,
                    engine_key="crawl4ai",
                    status=ParseAttemptStatus.SUCCEEDED,
                ),
            ],
            timings_ms=ParseTimingSummary(total=120),
        ),
    )
    batch_result = ParseBatchResult(
        requested_sources=["https://example.com/docs"],
        engine_id="auto",
        results=[result],
    )
    accepted = JobAccepted(
        job_id="job_456",
        job_type=JobType.PARSE,
        status=JobStatus.QUEUED,
        submitted_at=datetime(2026, 4, 14, 9, 0, tzinfo=UTC),
        poll_url="/v1/jobs/job_456",
    )
    batch_accepted = ParseBatchJobAccepted(
        requested_sources=["https://example.com/docs"],
        engine_id="auto",
        jobs=[accepted],
    )

    assert public_request.engine_id == "auto"
    assert public_request.sources == ["https://example.com/docs"]
    assert public_job_request.sources == ["cortex://objects/obj_123"]
    assert request.source.input_kind is ParseInputKind.URL
    assert engine.deployment_mode is ParseEngineDeploymentMode.LOCAL
    assert profile.profile_ref == "auto_default"
    assert result.diagnostics.engine_attempts[0].status is ParseAttemptStatus.FAILED
    assert result.diagnostics.fallback_used is True
    assert batch_result.results[0].job_id == "job_123"
    assert batch_accepted.jobs[0].job_id == "job_456"
    assert FallbackMode.ORDERED == "ordered"
