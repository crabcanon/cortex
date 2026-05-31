"""Unit coverage for evaluation and synthesis runtime adapters."""

from __future__ import annotations

import asyncio
import os
import sys
import types
from typing import Any, cast

import pytest
from cortex_common import ConfigError, CortexError, OpenAICompatibleConfig
from cortex_contracts import (
    EvalInput,
    EvalMetricRequest,
    EvalSyncRequest,
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
    EvalScopeSelfHostedSdkEvaluationEngine,
    _build_deepeval_judge_model,
)
from cortex_parse.adapters.docling import DoclingParseEngine
from cortex_synthesis.adapters import DeepEvalSynthesisEngine, SDVSynthesisEngine


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
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

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
