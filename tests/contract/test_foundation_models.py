"""Phase B contract tests for shared foundation modules."""

import logging
from datetime import UTC, datetime

import pytest
from cortex_common import PaginationWindow, ValidationError, json_dumps, json_loads, load_settings
from cortex_common.idempotency import normalize_idempotency_key
from cortex_common.ids import new_prefixed_id
from cortex_contracts import JobAccepted, JobStatus, JobType, PaginationEnvelope, ProblemDetails
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
        submitted_at="2026-04-12T13:00:00Z",
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
