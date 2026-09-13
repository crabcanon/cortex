"""Unit coverage for evaluation and synthesis runtime adapters."""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import tomllib
import types
from pathlib import Path
from typing import Any, cast

import pytest
from cortex_common import ConfigError, CortexError, OpenAICompatibleConfig
from cortex_contracts import (
    EvalInput,
    EvalMetricRequest,
    EvalRunResult,
    EvalScoreCard,
    EvalSyncRequest,
    EvalTarget,
    EvalTestCase,
    EvalType,
    ParseEngineStatus,
    SynthesisConfig,
    SynthesisSource,
    SynthesisSyncRequest,
    SynthesisType,
)
from cortex_evaluation.adapters import (
    DeepEvalEvaluationEngine,
    EvalScopeEvaluationEngine,
    EvalScopeSelfHostedSdkEvaluationEngine,
    OpenAICompatibleDeepEvalModel,
    _build_deepeval_judge_model,
    _build_evalscope_payload,
    _default_metric_requests,
    _normalize_evalscope_result,
)
from cortex_evaluation.adapters.utils.deepeval_helper import deepeval_metric_manifest
from cortex_evaluation.adapters.utils.evalscope_cleaner import EvalScopePerfResult
from cortex_evaluation.artifacts import EvaluationStorageCaller, persist_evaluation_report
from cortex_evaluation.jobs import _redact_error_message
from cortex_evaluation.registry import EvaluationEngineRegistry
from cortex_evaluation.service import EvaluationService
from cortex_parse.adapters.docling import DoclingParseEngine
from cortex_synthesis.adapters import (
    DeepEvalSynthesisEngine,
    OpenAICompatibleDeepEvalSynthesisModel,
    SDVSynthesisEngine,
    _coerce_deepeval_schema,
)
from pydantic import BaseModel


class _FakeMetric:
    def __init__(self, threshold: float | None = None, **kwargs) -> None:
        self.threshold = threshold
        self.kwargs = kwargs
        self.score = None
        self.reason = None
        self.success = False

    def measure(self, test_case) -> None:
        del test_case
        self.score = 0.92
        self.reason = "ok"
        self.success = self.threshold is None or self.score >= self.threshold


class _FakeLLMTestCase:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


class _FakeConversationalTestCase:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


class _FakeTurn:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


class _FakeLLMTestCaseParams:
    INPUT = "INPUT"
    ACTUAL_OUTPUT = "ACTUAL_OUTPUT"
    EXPECTED_OUTPUT = "EXPECTED_OUTPUT"
    RETRIEVAL_CONTEXT = "RETRIEVAL_CONTEXT"
    RETRIEVAL_CONTEXTS = "RETRIEVAL_CONTEXTS"


class _FakeTurnParams:
    CONTENT = "CONTENT"


class _FakeDataFrame:
    def __init__(self, rows):
        self._rows = list(rows)
        self.columns = list(self._rows[0].keys()) if self._rows else []

    def __len__(self) -> int:
        return len(self._rows)

    def head(self, limit: int):
        return _FakeDataFrame(self._rows[:limit])

    def to_dict(self, orient: str = "records"):
        assert orient == "records"
        return list(self._rows)


class _FakeMetadata:
    @staticmethod
    def detect_from_dataframe(*, data, table_name: str):
        return {"kind": "single", "rows": len(data), "table_name": table_name}

    @staticmethod
    def detect_from_dataframes(*, data):
        return {"kind": "multi", "tables": sorted(data)}


class _FakeGaussianCopulaSynthesizer:
    def __init__(self, metadata) -> None:
        self.metadata = metadata
        self._fit_rows = None

    def fit(self, data) -> None:
        self._fit_rows = len(data)

    def sample(self, *, num_rows: int):
        return _FakeDataFrame([{"row_id": index, "kind": "synthetic"} for index in range(num_rows)])


class _FakeHMASynthesizer:
    def __init__(self, metadata) -> None:
        self.metadata = metadata

    def fit(self, data) -> None:
        self.data = data

    def sample(self, *, scale: int):
        return {
            "orders": _FakeDataFrame([{"order_id": index} for index in range(scale)]),
            "items": _FakeDataFrame([{"item_id": index} for index in range(scale)]),
        }


class _FakeGolden:
    def __init__(self, **kwargs) -> None:
        self.input = kwargs.get("input")
        self.expected_output = kwargs.get("expected_output")
        self.context = kwargs.get("context")
        self.expected_outcome = kwargs.get("expected_outcome")


class _FakeSynthesizer:
    instances: list[Any] = []

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.__class__.instances.append(self)

    def generate_goldens_from_contexts(
        self,
        *,
        contexts,
        include_expected_output: bool,
        max_goldens_per_context=None,
    ):
        assert isinstance(max_goldens_per_context, int)
        return [
            _FakeGolden(
                input=f"question-{index}",
                expected_output="answer" if include_expected_output else None,
                context=context,
            )
            for index, context in enumerate(contexts * max_goldens_per_context, start=1)
        ]

    def generate_conversational_goldens_from_contexts(
        self,
        *,
        contexts,
        include_expected_outcome: bool,
        max_goldens_per_context=None,
    ):
        assert isinstance(max_goldens_per_context, int)
        return [
            _FakeGolden(
                input=f"conversation-{index}",
                expected_outcome="resolved" if include_expected_outcome else None,
                context=context,
            )
            for index, context in enumerate(contexts * max_goldens_per_context, start=1)
        ]


class _FakeDeepEvalBaseLLM:
    pass


def _install_fake_deepeval(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeSynthesizer.instances = []
    metrics_module = types.ModuleType("deepeval.metrics")
    for name in [
        "FaithfulnessMetric",
        "AnswerRelevancyMetric",
        "ContextualRecallMetric",
        "ContextualPrecisionMetric",
        "ContextualRelevancyMetric",
        "HallucinationMetric",
        "TaskCompletionMetric",
        "ToolCorrectnessMetric",
        "ConversationCompletenessMetric",
        "ConversationRelevancyMetric",
        "ToxicityMetric",
        "BiasMetric",
        "JsonCorrectnessMetric",
        "GEval",
        "ConversationalGEval",
    ]:
        setattr(metrics_module, name, _FakeMetric)

    test_case_module = types.ModuleType("deepeval.test_case")
    test_case_module.__dict__["LLMTestCase"] = _FakeLLMTestCase
    test_case_module.__dict__["ConversationalTestCase"] = _FakeConversationalTestCase
    test_case_module.__dict__["Turn"] = _FakeTurn
    test_case_module.__dict__["LLMTestCaseParams"] = _FakeLLMTestCaseParams
    test_case_module.__dict__["TurnParams"] = _FakeTurnParams

    synthesizer_module = types.ModuleType("deepeval.synthesizer")
    synthesizer_module.__dict__["Synthesizer"] = _FakeSynthesizer

    models_module = types.ModuleType("deepeval.models")
    models_module.__dict__["DeepEvalBaseLLM"] = _FakeDeepEvalBaseLLM

    monkeypatch.setitem(sys.modules, "deepeval", types.ModuleType("deepeval"))
    monkeypatch.setitem(sys.modules, "deepeval.metrics", metrics_module)
    monkeypatch.setitem(sys.modules, "deepeval.test_case", test_case_module)
    monkeypatch.setitem(sys.modules, "deepeval.synthesizer", synthesizer_module)
    monkeypatch.setitem(sys.modules, "deepeval.models", models_module)


def _install_fake_sdv(monkeypatch: pytest.MonkeyPatch) -> None:
    pandas_module = types.ModuleType("pandas")
    pandas_module.__dict__["DataFrame"] = _FakeDataFrame

    metadata_module = types.ModuleType("sdv.metadata")
    metadata_module.__dict__["Metadata"] = _FakeMetadata

    single_table_module = types.ModuleType("sdv.single_table")
    single_table_module.__dict__["GaussianCopulaSynthesizer"] = _FakeGaussianCopulaSynthesizer

    multi_table_module = types.ModuleType("sdv.multi_table")
    multi_table_module.__dict__["HMASynthesizer"] = _FakeHMASynthesizer

    monkeypatch.setitem(sys.modules, "pandas", pandas_module)
    monkeypatch.setitem(sys.modules, "sdv", types.ModuleType("sdv"))
    monkeypatch.setitem(sys.modules, "sdv.metadata", metadata_module)
    monkeypatch.setitem(sys.modules, "sdv.single_table", single_table_module)
    monkeypatch.setitem(sys.modules, "sdv.multi_table", multi_table_module)


def _install_fake_openai(monkeypatch: pytest.MonkeyPatch) -> type:
    openai_module = types.ModuleType("openai")

    class _FakeCompletions:
        def __init__(self, owner) -> None:
            self._owner = owner

        def create(self, **kwargs):
            self._owner.requests.append(kwargs)
            return types.SimpleNamespace(
                choices=[
                    types.SimpleNamespace(message=types.SimpleNamespace(content='{"score": 1}'))
                ]
            )

    class _FakeAsyncCompletions:
        def __init__(self, owner) -> None:
            self._owner = owner

        async def create(self, **kwargs):
            self._owner.requests.append(kwargs)
            self._owner.loops.append(asyncio.get_running_loop())
            return types.SimpleNamespace(
                choices=[
                    types.SimpleNamespace(message=types.SimpleNamespace(content='{"score": 1}'))
                ]
            )

    class _FakeChat:
        def __init__(self, owner, completions_class) -> None:
            self.completions = completions_class(owner)

    class _FakeOpenAI:
        instances: list[Any] = []
        requests: list[dict[str, Any]] = []
        closed = 0

        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs
            self.requests = self.__class__.requests
            self.chat = _FakeChat(self, _FakeCompletions)
            self.__class__.instances.append(self)

        def close(self) -> None:
            self.__class__.closed += 1

    class _FakeAsyncOpenAI:
        instances: list[Any] = []
        requests: list[dict[str, Any]] = []
        loops: list[Any] = []
        closed = 0

        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs
            self.requests = self.__class__.requests
            self.loops = self.__class__.loops
            self.chat = _FakeChat(self, _FakeAsyncCompletions)
            self.__class__.instances.append(self)

        async def close(self) -> None:
            self.__class__.closed += 1

    openai_module.__dict__["OpenAI"] = _FakeOpenAI
    openai_module.__dict__["AsyncOpenAI"] = _FakeAsyncOpenAI
    monkeypatch.setitem(sys.modules, "openai", openai_module)
    return _FakeAsyncOpenAI


def test_deepeval_engine_runs_inline_test_cases(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_deepeval(monkeypatch)
    engine = DeepEvalEvaluationEngine(available=True)
    request = EvalSyncRequest(
        name="rag-inline",
        eval_type=EvalType.RAG,
        input=EvalInput(
            type="inline_test_cases",
            test_cases=[
                EvalTestCase(
                    user_input="What is Cortex?",
                    actual_output="A platform.",
                    expected_output="A platform.",
                    retrieval_contexts=["Cortex is a platform."],
                )
            ],
        ),
        metrics=[
            EvalMetricRequest(metric_key="rag.faithfulness", threshold=0.8),
            EvalMetricRequest(metric_key="quality.correctness", threshold=0.8),
        ],
    )

    result = asyncio.run(engine.run(request))

    assert result.engine_id == "deepeval"
    assert result.status == "succeeded"
    assert len(result.metrics) == 2
    assert result.metrics[0].score == pytest.approx(0.92)
    assert result.summary.composite_score == pytest.approx(0.92)


def test_deepeval_engine_can_be_routable_without_local_sdk() -> None:
    engine = DeepEvalEvaluationEngine(available=True, local_available=False)
    request = EvalSyncRequest(
        name="rag-inline",
        eval_type=EvalType.RAG,
        input=EvalInput(
            type="inline_test_cases",
            test_cases=[EvalTestCase(user_input="q", actual_output="a")],
        ),
    )

    with pytest.raises(CortexError) as exc_info:
        asyncio.run(engine.run(request))

    assert engine.descriptor.availability_status == "degraded"
    assert exc_info.value.code == "deepeval_runtime_not_available_in_process"


def test_evalscope_self_hosted_engine_can_be_routable_without_local_sdk() -> None:
    engine = EvalScopeSelfHostedSdkEvaluationEngine(
        host="127.0.0.1",
        port=9000,
        timeout_seconds=1,
        headers={},
        debug=False,
        startup_timeout_seconds=1,
        available=True,
        local_available=False,
    )
    request = EvalSyncRequest(
        name="perf",
        eval_type=EvalType.PERF,
        input=EvalInput(type="builtin_dataset", builtin_dataset_key="openqa"),
    )

    with pytest.raises(CortexError) as exc_info:
        asyncio.run(engine.run(request))

    assert engine.descriptor.availability_status == "degraded"
    assert exc_info.value.code == "evalscope_sdk_runtime_not_available_in_process"


def test_evaluation_service_routes_only_to_engines_supporting_eval_type() -> None:
    registry = EvaluationEngineRegistry()
    registry.register(
        EvalScopeEvaluationEngine(base_url="http://evalscope", timeout_seconds=1, headers={})
    )
    service = EvaluationService(registry=registry)
    request = EvalSyncRequest(
        name="agent-regression",
        eval_type=EvalType.AGENTIC,
        input=EvalInput(
            type="inline_test_cases",
            test_cases=[EvalTestCase(user_input="q", actual_output="a")],
        ),
        engine_id="auto",
        metrics=[EvalMetricRequest(metric_key="agent.task_completion", threshold=0.8)],
    )

    with pytest.raises(CortexError) as auto_error:
        service.resolve_request(request)
    with pytest.raises(CortexError) as explicit_error:
        service.resolve_request(request.model_copy(update={"engine_id": "evalscope"}))

    assert auto_error.value.code == "eval_engine_not_available"
    assert auto_error.value.status_code == 503
    assert "`agentic`" in auto_error.value.detail
    assert explicit_error.value.code == "eval_engine_unsupported_type"
    assert explicit_error.value.status_code == 422
    assert "does not support `agentic`" in explicit_error.value.detail


def test_evalscope_runtime_extra_declares_service_server_dependency() -> None:
    pyproject = Path(__file__).resolve().parents[2] / "packages" / "evaluation" / "pyproject.toml"
    optional_dependencies = tomllib.loads(pyproject.read_text())["project"]["optional-dependencies"]

    assert "evalscope[service]>=1.6,<2" in optional_dependencies["evalscope"]
    assert "fastapi>=0.115,<1" in optional_dependencies["evalscope"]
    assert "sse-starlette>=2.1,<3" in optional_dependencies["evalscope"]
    assert "uvicorn>=0.35,<0.36" in optional_dependencies["evalscope"]
    assert "fastapi>=0.115,<1" in optional_dependencies["runtime"]
    assert "sse-starlette>=2.1,<3" in optional_dependencies["runtime"]
    assert "uvicorn>=0.35,<0.36" in optional_dependencies["runtime"]


def test_evalscope_engine_calls_blocking_invoke_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    posts: list[tuple[str, dict[str, Any]]] = []
    clients: list[Any] = []

    class _FakeAsyncClient:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs
            clients.append(self)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> None:
            del args

        async def post(self, endpoint: str, json: dict[str, Any]):
            posts.append((endpoint, json))
            payload = (
                {"metrics": {"Req Throughput (req/s)": 1.0}}
                if endpoint == "/api/v1/perf/invoke"
                else {"metrics": {"quality.correctness": 0.9}}
            )
            return types.SimpleNamespace(
                status_code=200,
                text="{}",
                json=lambda: payload,
            )

    monkeypatch.setattr(
        "cortex_evaluation.adapters.evalscope_engine.httpx.AsyncClient",
        _FakeAsyncClient,
    )
    engine = EvalScopeEvaluationEngine(base_url="http://evalscope", timeout_seconds=1, headers={})

    asyncio.run(
        engine.run(
            EvalSyncRequest(
                name="perf",
                eval_type=EvalType.PERF,
                input=EvalInput(type="builtin_dataset", builtin_dataset_key="openqa"),
                engine_options={"evalscope_task_id": "job_perf"},
            )
        )
    )
    asyncio.run(
        engine.run(
            EvalSyncRequest(
                name="rag",
                eval_type=EvalType.RAG,
                input=EvalInput(type="builtin_dataset", builtin_dataset_key="openqa"),
                engine_options={"evalscope_task_id": "job_rag"},
            )
        )
    )

    assert posts[0][0] == "/api/v1/perf/invoke"
    assert posts[1][0] == "/api/v1/eval/invoke"
    assert clients[0].kwargs["headers"]["EvalScope-Task-Id"] == "job_perf"
    assert clients[1].kwargs["headers"]["EvalScope-Task-Id"] == "job_rag"
    assert "evalscope_task_id" not in posts[0][1]
    assert "evalscope_task_id" not in posts[1][1]


def test_evalscope_perf_payload_forwards_openai_compatible_target_api_key() -> None:
    request = EvalSyncRequest(
        name="perf",
        eval_type=EvalType.PERF,
        engine_id="evalscope",
        input=EvalInput(type="builtin_dataset", builtin_dataset_key="openqa"),
        engine_options={
            "evalscope_task_id": "job_perf",
            "cortex_job_id": "job_perf",
            "model_args": {"temperature": 0.1},
        },
        target=EvalTarget(
            type="api",
            protocol="openai_compatible",
            endpoint_url="https://llm.example/v1/chat/completions",
            api_key="sk-test-key",
            model_ref="qwen-max",
        ),
    )

    payload = _build_evalscope_payload(request)

    assert payload["api"] == "openai"
    assert payload["url"] == "https://llm.example/v1/chat/completions"
    assert payload["api_key"] == "sk-test-key"
    assert payload["headers"]["Authorization"] == "Bearer sk-test-key"
    assert payload["model"] == "qwen-max"
    assert payload["model_args"] == {"temperature": 0.1}
    assert "evalscope_task_id" not in payload
    assert "cortex_job_id" not in payload


def test_evalscope_openqa_rejects_overstrict_min_prompt_length() -> None:
    request = EvalSyncRequest(
        name="perf",
        eval_type=EvalType.PERF,
        engine_id="evalscope",
        input=EvalInput(type="builtin_dataset", builtin_dataset_key="openqa"),
        engine_options={
            "parallel": [1],
            "number": [2],
            "min_prompt_length": 1024,
            "max_prompt_length": 2048,
        },
        target=EvalTarget(
            type="api",
            protocol="openai_compatible",
            endpoint_url="https://openrouter.ai/api/v1/chat/completions",
            api_key="sk-or-v1-test-key",
            model_ref="gpt-4o-mini",
        ),
    )

    with pytest.raises(CortexError) as exc_info:
        _build_evalscope_payload(request)

    assert exc_info.value.code == "evalscope_dataset_filter_too_strict"
    assert exc_info.value.status_code == 422
    assert "min_prompt_length=1024" in exc_info.value.detail


def test_evaluation_error_redaction_handles_openrouter_json_api_keys() -> None:
    key = "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"
    message = f'{{"api_key": "{key}", "headers": {{"Authorization": "Bearer {key}"}}}}'

    redacted = _redact_error_message(message)

    assert "sk-or-v1-bc365" not in redacted
    assert redacted.count("<redacted>") == 2


def test_evalscope_perf_defaults_cover_official_stress_metrics() -> None:
    metric_keys = [metric.metric_key for metric in _default_metric_requests(EvalType.PERF)]

    assert "perf.test_duration_seconds" in metric_keys
    assert "perf.request_throughput" in metric_keys
    assert "perf.avg_latency_seconds" in metric_keys
    assert "perf.ttft_ms" in metric_keys
    assert "perf.tpot_ms" in metric_keys
    assert "perf.itl_ms" in metric_keys
    assert "perf.avg_input_tokens" in metric_keys
    assert "perf.avg_output_tokens" in metric_keys
    assert "perf.output_throughput_tokens_per_second" in metric_keys
    assert "perf.total_throughput_tokens_per_second" in metric_keys
    assert "perf.p99.latency_seconds" in metric_keys
    assert "perf.p99.total_throughput_tokens_per_second" in metric_keys


def test_evalscope_perf_result_normalizes_general_latency_token_and_percentile_tables() -> None:
    request = EvalSyncRequest(
        name="perf",
        eval_type=EvalType.PERF,
        engine_id="evalscope",
        input=EvalInput(type="builtin_dataset", builtin_dataset_key="openqa"),
    )
    payload = {
        "General": {
            "Test Duration (s)": 3.1,
            "Concurrency": 2,
            "Request Rate (req/s)": 4.0,
            "Total / Success / Failed": "20 / 19 / 1",
            "Req Throughput (req/s)": 6.2,
        },
        "Latency": {
            "Avg Latency (s)": 0.42,
            "TTFT (ms)": 110,
            "TPOT (ms)": 20,
            "ITL (ms)": 14,
        },
        "Tokens": {
            "Avg Input Tokens": 128,
            "Avg Output Tokens": 256,
            "Output Throughput (tok/s)": 512,
            "Total Throughput (tok/s)": 700,
        },
        "Percentiles": [
            {
                "Percentile": 99,
                "Latency (s)": 1.4,
                "TTFT (ms)": 200,
                "ITL (ms)": 30,
                "TPOT (ms)": 25,
                "Input tokens": 180,
                "Output tokens": 280,
                "Output Throughput (tok/s)": 450,
                "Total Throughput (tok/s)": 610,
            }
        ],
    }

    result = _normalize_evalscope_result(request, payload, started_at=None)
    metrics = {metric.metric_key: metric for metric in result.metrics}

    assert metrics["perf.test_duration_seconds"].score == pytest.approx(3.1)
    assert metrics["perf.qps"].score == pytest.approx(6.2)
    assert metrics["perf.ttft"].score == pytest.approx(0.11)
    assert metrics["perf.avg_input_tokens"].score == pytest.approx(128)
    assert metrics["perf.p99.latency_seconds"].score == pytest.approx(1.4)
    assert metrics["perf.p99.total_throughput_tokens_per_second"].score == pytest.approx(610)
    assert result.samples is not None
    assert result.samples.total == 20
    assert result.samples.passed == 19
    assert result.samples.failed == 1


def test_evalscope_perf_result_pydantic_pipeline_normalizes_metric_aliases() -> None:
    result = EvalScopePerfResult.model_validate(
        {
            "metrics": {
                "Req Throughput (req/s)": "7.5 req/s",
                "Total / Success / Failed": "10 / 9 / 1",
            },
            "Percentiles": [{"P": "90", "Latency (s)": "1.25"}],
        }
    )

    assert result.metrics["perf.request_throughput"] == pytest.approx(7.5)
    assert result.metrics["perf.qps"] == pytest.approx(7.5)
    assert result.metrics["perf.p90.latency_seconds"] == pytest.approx(1.25)
    assert result.samples.total == 10
    assert result.samples.passed == 9
    assert result.samples.failed == 1


def test_evalscope_perf_result_omits_missing_metric_placeholders() -> None:
    request = EvalSyncRequest(
        name="perf",
        eval_type=EvalType.PERF,
        engine_id="evalscope",
        input=EvalInput(type="builtin_dataset", builtin_dataset_key="openqa"),
    )

    result = _normalize_evalscope_result(request, {"task_id": "job_perf"}, started_at=None)

    assert result.metrics == []
    assert result.summary.metric_count == 0
    assert result.summary.overall_passed is True


def test_evalscope_native_output_directory_is_uploaded_and_cleaned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        output_root = Path(temp_dir) / "outputs"
        artifact_dir = output_root / "job_perf" / "perf"
        nested_dir = artifact_dir / "nested"
        nested_dir.mkdir(parents=True)
        (artifact_dir / "summary.html").write_text("<html>report</html>", encoding="utf-8")
        (nested_dir / "metrics.json").write_text('{"ok": true}', encoding="utf-8")
        monkeypatch.setenv("CORTEX_EVALSCOPE_OUTPUT_ROOT", str(output_root))

        class _FakeStorage:
            def __init__(self) -> None:
                self.artifact_uploads: list[dict[str, Any]] = []

            async def upload_artifact_file(self, **kwargs):
                self.artifact_uploads.append(kwargs)
                relative_path = kwargs["relative_path"]
                return types.SimpleNamespace(
                    object_id=f"obj_artifact_{len(self.artifact_uploads)}",
                    bucket="cortex-test",
                    object_key=f"{kwargs['object_key_prefix']}/{relative_path}",
                    content_type=kwargs["content_type"],
                )

            async def upload_small_file(self, **kwargs):
                del kwargs
                return types.SimpleNamespace(
                    object_id="obj_report",
                    bucket="cortex-test",
                    object_key="tenant/evaluation/job_perf/report.json",
                    content_type="application/json",
                )

        request = EvalSyncRequest(
            name="perf",
            eval_type=EvalType.PERF,
            engine_id="evalscope",
            input=EvalInput(type="builtin_dataset", builtin_dataset_key="openqa"),
            engine_options={"evalscope_task_id": "job_perf"},
        )
        result = EvalRunResult(
            name="perf",
            eval_type=EvalType.PERF,
            engine_id="evalscope",
            status="succeeded",
            job_id="job_perf",
            eval_run_id="erun_perf",
            summary=EvalScoreCard(overall_passed=True),
            metrics=[],
        )
        storage = _FakeStorage()

        persisted = asyncio.run(
            persist_evaluation_report(
                uow=cast(Any, object()),
                storage_service=storage,
                caller=EvaluationStorageCaller(
                    tenant_id="tenant_eval",
                    subject="alice",
                    actor_id="alice",
                ),
                request=request,
                result=result,
            )
        )

        assert [upload["relative_path"] for upload in storage.artifact_uploads] == [
            "nested/metrics.json",
            "summary.html",
        ]
        assert all(
            upload["object_key_prefix"] == "evaluation/job_perf/evalscope/perf"
            for upload in storage.artifact_uploads
        )
        assert not artifact_dir.exists()
        labels = [artifact.label for artifact in persisted.artifacts]
        assert labels.count("evalscope_artifact") == 2
        assert "evaluation_report" in labels


def test_deepeval_engine_applies_default_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_deepeval(monkeypatch)
    engine = DeepEvalEvaluationEngine(available=True)
    request = EvalSyncRequest(
        name="rag-defaults",
        eval_type=EvalType.RAG,
        input=EvalInput(
            type="inline_test_cases",
            test_cases=[
                EvalTestCase(
                    user_input="What is Cortex?",
                    actual_output="A platform.",
                    expected_output="A platform.",
                    retrieval_contexts=["Cortex is a platform."],
                )
            ],
        ),
    )

    result = asyncio.run(engine.run(request))

    assert len(result.metrics) == 4
    assert all(metric.engine_id == "deepeval" for metric in result.metrics)


def test_deepeval_engine_applies_openai_compatible_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_deepeval(monkeypatch)
    for key in ("OPENAI_API_URL", "OPENAI_BASE_URL", "OPENAI_API_BASE", "LITELLM_API_BASE"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    engine = DeepEvalEvaluationEngine(
        available=True,
        provider_config=OpenAICompatibleConfig(
            api_url="https://llm.example/v1",
            api_key="provider-key",
        ),
    )
    request = EvalSyncRequest(
        name="rag-openai-compatible",
        eval_type=EvalType.RAG,
        input=EvalInput(
            type="inline_test_cases",
            test_cases=[EvalTestCase(user_input="q", actual_output="a")],
        ),
        metrics=[EvalMetricRequest(metric_key="quality.correctness", threshold=0.8)],
    )

    asyncio.run(engine.run(request))

    assert os.environ["OPENAI_API_URL"] == "https://llm.example/v1"
    assert os.environ["OPENAI_BASE_URL"] == "https://llm.example/v1"
    assert os.environ["OPENAI_API_BASE"] == "https://llm.example/v1"
    assert os.environ["LITELLM_API_BASE"] == "https://llm.example/v1"
    assert os.environ["OPENAI_API_KEY"] == "provider-key"


def test_deepeval_openai_compatible_judge_does_not_reuse_async_clients_across_loops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_deepeval(monkeypatch)
    fake_async_openai = _install_fake_openai(monkeypatch)
    judge = _build_deepeval_judge_model(
        model="openrouter/auto",
        provider_config=OpenAICompatibleConfig(
            api_url="https://openrouter.ai/api/v1",
            api_key="provider-key",
        ),
        options={"timeout_seconds": 5, "max_tokens": 64},
    )

    first = asyncio.run(judge.a_generate("judge prompt one"))
    second = asyncio.run(judge.a_generate("judge prompt two"))

    assert first == '{"score": 1}'
    assert second == '{"score": 1}'
    assert len(fake_async_openai.instances) == 2
    assert fake_async_openai.closed == 2
    assert fake_async_openai.loops[0] is not fake_async_openai.loops[1]


def test_deepeval_judge_model_is_static_top_level_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_deepeval(monkeypatch)
    _install_fake_openai(monkeypatch)

    first = _build_deepeval_judge_model(
        model="openrouter/auto",
        provider_config=OpenAICompatibleConfig(
            api_url="https://openrouter.ai/api/v1",
            api_key="provider-key",
        ),
        options={},
    )
    second = _build_deepeval_judge_model(
        model="openrouter/auto",
        provider_config=OpenAICompatibleConfig(
            api_url="https://openrouter.ai/api/v1",
            api_key="provider-key",
        ),
        options={},
    )

    assert isinstance(first, OpenAICompatibleDeepEvalModel)
    assert first.__class__ is second.__class__


def test_deepeval_metric_manifest_is_loaded_outside_engine_logic() -> None:
    manifest = deepeval_metric_manifest()

    assert manifest.direct_metrics["rag.faithfulness"] == "FaithfulnessMetric"
    assert "quality.correctness" in manifest.custom_criteria
    assert "dialog.conversation_relevancy" in manifest.conversational_metrics


def test_sdv_engine_generates_single_table_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_sdv(monkeypatch)
    engine = SDVSynthesisEngine(available=True)
    request = SynthesisSyncRequest(
        name="single-table",
        synthesis_type=SynthesisType.STRUCTURED_SINGLE_TABLE,
        source=SynthesisSource(
            type="inline_records",
            inline_records=[
                {"customer_id": "c1", "tier": "gold"},
                {"customer_id": "c2", "tier": "silver"},
            ],
        ),
        config=SynthesisConfig(sample_count=3),
    )

    result = asyncio.run(engine.run(request))

    assert result.engine_id == "sdv"
    assert result.summary.output_sample_count == 3
    assert result.source_summary["preview_rows"][0]["kind"] == "synthetic"


def test_sdv_engine_can_be_routable_without_local_sdk() -> None:
    engine = SDVSynthesisEngine(available=True, local_available=False)
    request = SynthesisSyncRequest(
        name="single-table",
        synthesis_type=SynthesisType.STRUCTURED_SINGLE_TABLE,
        source=SynthesisSource(type="inline_records", inline_records=[{"id": 1}]),
    )

    with pytest.raises(CortexError) as exc_info:
        asyncio.run(engine.run(request))

    assert engine.descriptor.availability_status == "degraded"
    assert exc_info.value.code == "sdv_runtime_not_available_in_process"


def test_deepeval_synthesis_engine_generates_context_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_deepeval(monkeypatch)
    engine = DeepEvalSynthesisEngine(available=True)
    request = SynthesisSyncRequest(
        name="rag-goldens",
        synthesis_type=SynthesisType.RAG_GOLDENS,
        source=SynthesisSource(
            type="documents",
            documents=["Cortex is a vendor-neutral AI platform."],
        ),
        config=SynthesisConfig(sample_count=1, include_expected_output=True),
    )

    result = asyncio.run(engine.run(request))

    assert result.engine_id == "deepeval"
    assert result.summary.output_sample_count == 1
    assert result.source_summary["preview_rows"][0]["input"] == "question-1"


def test_deepeval_synthesis_engine_defaults_goldens_per_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_deepeval(monkeypatch)
    engine = DeepEvalSynthesisEngine(available=True)
    request = SynthesisSyncRequest(
        name="rag-goldens-default",
        synthesis_type=SynthesisType.RAG_GOLDENS,
        source=SynthesisSource(
            type="documents",
            documents=["Cortex keeps synthesis requests concise."],
        ),
    )

    result = asyncio.run(engine.run(request))

    assert result.engine_id == "deepeval"
    assert result.summary.output_sample_count == 1
    assert result.source_summary["preview_rows"][0]["input"] == "question-1"


def test_deepeval_synthesis_uses_openai_compatible_model_wrapper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_deepeval(monkeypatch)
    _install_fake_openai(monkeypatch)
    engine = DeepEvalSynthesisEngine(
        available=True,
        model="openrouter/auto",
        provider_config=OpenAICompatibleConfig(
            api_url="https://openrouter.ai/api/v1",
            api_key="provider-key",
        ),
    )
    request = SynthesisSyncRequest(
        name="rag-goldens-openai-compatible",
        synthesis_type=SynthesisType.RAG_GOLDENS,
        source=SynthesisSource(
            type="documents",
            documents=["Cortex can synthesize RAG goldens."],
        ),
        config=SynthesisConfig(sample_count=1, include_expected_output=True),
    )

    result = asyncio.run(engine.run(request))

    synthesizer_model = _FakeSynthesizer.instances[-1].kwargs["model"]
    assert isinstance(synthesizer_model, OpenAICompatibleDeepEvalSynthesisModel)
    assert synthesizer_model.get_model_name() == "openai-compatible:openrouter/auto"
    assert result.summary.output_sample_count == 1


def test_deepeval_synthesis_limits_multi_document_output_to_sample_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_deepeval(monkeypatch)
    engine = DeepEvalSynthesisEngine(available=True)
    request = SynthesisSyncRequest(
        name="rag-goldens-limited",
        synthesis_type=SynthesisType.RAG_GOLDENS,
        source=SynthesisSource(
            type="documents",
            documents=[
                "Cortex Parse converts sources to Markdown.",
                "Cortex Knowledge builds graph-backed memory.",
            ],
        ),
        config=SynthesisConfig(sample_count=3),
    )

    result = asyncio.run(engine.run(request))

    assert result.summary.output_sample_count == 3
    assert len(result.source_summary["preview_rows"]) == 3
    assert [row["input"] for row in result.source_summary["preview_rows"]] == [
        "question-1",
        "question-2",
        "question-3",
    ]


def test_deepeval_conversation_synthesis_keeps_sample_count_a_hard_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_deepeval(monkeypatch)
    engine = DeepEvalSynthesisEngine(available=True)
    request = SynthesisSyncRequest(
        name="conversation-goldens-limited",
        synthesis_type=SynthesisType.CONVERSATION_GOLDENS,
        source=SynthesisSource(
            type="documents",
            documents=[
                "Support agents should ask for the object_id before parsing a private file."
            ],
        ),
        config=SynthesisConfig(
            sample_count=3,
            max_contexts_per_case=100,
            include_expected_output=True,
        ),
    )

    result = asyncio.run(engine.run(request))

    assert result.summary.output_sample_count == 3
    assert len(result.source_summary["preview_rows"]) == 3
    assert [row["input"] for row in result.source_summary["preview_rows"]] == [
        "conversation-1",
        "conversation-2",
        "conversation-3",
    ]


def test_deepeval_schema_fallback_coerces_plain_text_conversation_scenarios() -> None:
    class _Scenario(BaseModel):
        scenario: str

    class _ScenarioList(BaseModel):
        data: list[_Scenario]

    result = _coerce_deepeval_schema(
        "A support agent asks a customer for the object_id before parsing a private file.",
        _ScenarioList,
    )

    assert result.data[0].scenario.startswith("A support agent asks")


def test_deepeval_schema_parse_failure_is_actionable() -> None:
    class _StrictModel(BaseModel):
        count: int

    with pytest.raises(CortexError) as exc_info:
        _coerce_deepeval_schema("not-json", _StrictModel)

    assert exc_info.value.code == "deepeval_synth_schema_parse_failed"
    assert "StrictModel" in exc_info.value.detail


def test_deepeval_synthesis_cost_none_errors_are_actionable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_deepeval(monkeypatch)

    class _CostFailingSynthesizer:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def generate_goldens_from_contexts(self, **kwargs):
            del kwargs
            raise TypeError("unsupported operand type(s) for +=: 'int' and 'NoneType'")

    cast(Any, sys.modules["deepeval.synthesizer"]).Synthesizer = _CostFailingSynthesizer
    engine = DeepEvalSynthesisEngine(available=True, model="gpt-4o-mini")
    request = SynthesisSyncRequest(
        name="rag-goldens-cost-failure",
        synthesis_type=SynthesisType.RAG_GOLDENS,
        source=SynthesisSource(type="documents", documents=["doc"]),
    )

    with pytest.raises(CortexError) as exc_info:
        asyncio.run(engine.run(request))

    assert exc_info.value.code == "deepeval_synth_cost_tracking_failed"
    assert exc_info.value.status_code == 502
    assert "OpenAI-compatible provider base URL" in exc_info.value.detail


def test_deepeval_synthesis_engine_can_be_routable_without_local_sdk() -> None:
    engine = DeepEvalSynthesisEngine(available=True, local_available=False)
    request = SynthesisSyncRequest(
        name="rag-goldens",
        synthesis_type=SynthesisType.RAG_GOLDENS,
        source=SynthesisSource(type="documents", documents=["doc"]),
    )

    with pytest.raises(CortexError) as exc_info:
        asyncio.run(engine.run(request))

    assert engine.descriptor.availability_status == "degraded"
    assert exc_info.value.code == "deepeval_synth_runtime_not_available_in_process"


def test_docling_engine_is_catalog_active_when_sdk_is_worker_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "cortex_parse.adapters.docling._docling_available",
        lambda: False,
    )
    engine = DoclingParseEngine({"enabled": True})

    assert engine.descriptor.status is ParseEngineStatus.ACTIVE
    with pytest.raises(ConfigError) as exc_info:
        asyncio.run(
            engine.execute(
                cast(
                    Any,
                    type(
                        "Context",
                        (),
                        {
                            "source": type(
                                "Source",
                                (),
                                {"uri": "demo.pdf", "url": None},
                            )()
                        },
                    )(),
                )
            )
        )
    assert "cortex-parse-worker-docling" in str(exc_info.value)
