"""Built-in evaluation metric catalog."""

from __future__ import annotations

from cortex_common import utc_now
from cortex_contracts import (
    EngineMetricBinding,
    EvalMetricCatalog,
    EvalMetricDefinition,
    EvalType,
)

_PERF_PERCENTILES = (1, 5, 10, 25, 50, 66, 75, 80, 90, 95, 98, 99)

_PERF_GENERAL_METRICS: tuple[tuple[str, str, str, str], ...] = (
    ("perf.test_duration_seconds", "Test Duration", "seconds", "lower_is_better"),
    ("perf.concurrency", "Concurrency", "count", "higher_is_better"),
    ("perf.request_rate", "Request Rate", "requests_per_second", "higher_is_better"),
    ("perf.total_requests", "Total Requests", "count", "higher_is_better"),
    ("perf.success_requests", "Success Requests", "count", "higher_is_better"),
    ("perf.failed_requests", "Failed Requests", "count", "lower_is_better"),
    ("perf.request_throughput", "Request Throughput", "requests_per_second", "higher_is_better"),
)

_PERF_LATENCY_METRICS: tuple[tuple[str, str, str, str], ...] = (
    ("perf.avg_latency_seconds", "Average Latency", "seconds", "lower_is_better"),
    ("perf.ttft_ms", "Time To First Token", "milliseconds", "lower_is_better"),
    ("perf.tpot_ms", "Time Per Output Token", "milliseconds", "lower_is_better"),
    ("perf.itl_ms", "Inter-token Latency", "milliseconds", "lower_is_better"),
)

_PERF_TOKEN_METRICS: tuple[tuple[str, str, str, str], ...] = (
    ("perf.avg_input_tokens", "Average Input Tokens", "tokens", "lower_is_better"),
    ("perf.avg_output_tokens", "Average Output Tokens", "tokens", "higher_is_better"),
    (
        "perf.output_throughput_tokens_per_second",
        "Output Throughput",
        "tokens_per_second",
        "higher_is_better",
    ),
    (
        "perf.total_throughput_tokens_per_second",
        "Total Throughput",
        "tokens_per_second",
        "higher_is_better",
    ),
)

_PERF_COMPAT_METRICS: tuple[tuple[str, str, str, str], ...] = (
    ("perf.qps", "QPS", "requests_per_second", "higher_is_better"),
    ("perf.p50_latency", "P50 Latency", "seconds", "lower_is_better"),
    ("perf.p90_latency", "P90 Latency", "seconds", "lower_is_better"),
    ("perf.p99_latency", "P99 Latency", "seconds", "lower_is_better"),
    ("perf.ttft", "Time To First Token", "seconds", "lower_is_better"),
    (
        "perf.output_tokens_per_second",
        "Output Tokens Per Second",
        "tokens_per_second",
        "higher_is_better",
    ),
)

_PERF_PERCENTILE_METRIC_SPECS: tuple[tuple[str, str, str, str], ...] = (
    ("latency_seconds", "Latency", "seconds", "lower_is_better"),
    ("ttft_ms", "TTFT", "milliseconds", "lower_is_better"),
    ("itl_ms", "ITL", "milliseconds", "lower_is_better"),
    ("tpot_ms", "TPOT", "milliseconds", "lower_is_better"),
    ("input_tokens", "Input Tokens", "tokens", "lower_is_better"),
    ("output_tokens", "Output Tokens", "tokens", "higher_is_better"),
    (
        "output_throughput_tokens_per_second",
        "Output Throughput",
        "tokens_per_second",
        "higher_is_better",
    ),
    (
        "total_throughput_tokens_per_second",
        "Total Throughput",
        "tokens_per_second",
        "higher_is_better",
    ),
)


def default_perf_metric_keys() -> list[str]:
    return [metric.metric_key for metric in _perf_metric_catalog_entries()]


def perf_metric_direction(metric_key: str) -> str:
    for metric in _perf_metric_catalog_entries():
        if metric.metric_key == metric_key:
            return metric.score_direction
    return "higher_is_better"


def default_eval_metric_catalog() -> EvalMetricCatalog:
    metrics = [
        *_perf_metric_catalog_entries(),
        _metric(
            "rag.faithfulness",
            "Faithfulness",
            "rag",
            [EvalType.RAG],
            ["deepeval"],
            "higher_is_better",
        ),
        _metric(
            "rag.answer_relevance",
            "Answer Relevance",
            "rag",
            [EvalType.RAG],
            ["deepeval"],
            "higher_is_better",
        ),
        _metric(
            "rag.contextual_recall",
            "Contextual Recall",
            "rag",
            [EvalType.RAG],
            ["deepeval"],
            "higher_is_better",
        ),
        _metric(
            "rag.contextual_precision",
            "Contextual Precision",
            "rag",
            [EvalType.RAG],
            ["deepeval"],
            "higher_is_better",
        ),
        _metric(
            "rag.contextual_relevance",
            "Contextual Relevance",
            "rag",
            [EvalType.RAG],
            ["deepeval"],
            "higher_is_better",
        ),
        _metric(
            "rag.hallucination",
            "Hallucination",
            "rag",
            [EvalType.RAG],
            ["deepeval"],
            "lower_is_better",
        ),
        _metric(
            "agent.task_completion",
            "Task Completion",
            "agent",
            [EvalType.AGENTIC],
            ["deepeval"],
            "higher_is_better",
        ),
        _metric(
            "agent.tool_correctness",
            "Tool Correctness",
            "agent",
            [EvalType.AGENTIC],
            ["deepeval"],
            "higher_is_better",
        ),
        _metric(
            "agent.goal_success",
            "Goal Success",
            "agent",
            [EvalType.AGENTIC],
            ["deepeval"],
            "higher_is_better",
        ),
        _metric(
            "agent.step_efficiency",
            "Step Efficiency",
            "agent",
            [EvalType.AGENTIC],
            ["deepeval"],
            "higher_is_better",
        ),
        _metric(
            "agent.path_validity",
            "Path Validity",
            "agent",
            [EvalType.AGENTIC],
            ["deepeval"],
            "higher_is_better",
        ),
        _metric(
            "agent.reasoning_quality",
            "Reasoning Quality",
            "agent",
            [EvalType.AGENTIC],
            ["deepeval"],
            "higher_is_better",
        ),
        _metric(
            "dialog.conversation_completeness",
            "Conversation Completeness",
            "dialog",
            [EvalType.MULTI_TURN],
            ["deepeval"],
            "higher_is_better",
        ),
        _metric(
            "dialog.conversation_relevancy",
            "Conversation Relevancy",
            "dialog",
            [EvalType.MULTI_TURN],
            ["deepeval"],
            "higher_is_better",
        ),
        _metric(
            "dialog.turn_relevancy",
            "Turn Relevancy",
            "dialog",
            [EvalType.MULTI_TURN],
            ["deepeval"],
            "higher_is_better",
        ),
        _metric(
            "dialog.intent_drift",
            "Intent Drift",
            "dialog",
            [EvalType.MULTI_TURN],
            ["deepeval"],
            "lower_is_better",
        ),
        _metric(
            "safety.toxicity",
            "Toxicity",
            "safety",
            [EvalType.CUSTOM, EvalType.MULTI_TURN],
            ["deepeval"],
            "lower_is_better",
        ),
        _metric(
            "safety.bias", "Bias", "safety", [EvalType.CUSTOM], ["deepeval"], "lower_is_better"
        ),
        _metric(
            "safety.pii_leakage",
            "PII Leakage",
            "safety",
            [EvalType.CUSTOM, EvalType.RAG],
            ["deepeval"],
            "lower_is_better",
        ),
        _metric(
            "safety.prompt_leakage",
            "Prompt Leakage",
            "safety",
            [EvalType.CUSTOM, EvalType.AGENTIC],
            ["deepeval"],
            "lower_is_better",
        ),
        _metric(
            "safety.misinformation",
            "Misinformation",
            "safety",
            [EvalType.CUSTOM, EvalType.RAG],
            ["deepeval"],
            "lower_is_better",
        ),
        _metric(
            "safety.harm", "Harm", "safety", [EvalType.CUSTOM], ["deepeval"], "lower_is_better"
        ),
        _metric(
            "quality.correctness",
            "Correctness",
            "quality",
            [EvalType.CUSTOM, EvalType.RAG],
            ["deepeval"],
            "higher_is_better",
        ),
        _metric(
            "quality.completeness",
            "Completeness",
            "quality",
            [EvalType.CUSTOM, EvalType.RAG],
            ["deepeval"],
            "higher_is_better",
        ),
        _metric(
            "quality.relevance",
            "Relevance",
            "quality",
            [EvalType.CUSTOM, EvalType.RAG],
            ["deepeval"],
            "higher_is_better",
        ),
        _metric(
            "quality.coherence",
            "Coherence",
            "quality",
            [EvalType.CUSTOM, EvalType.MULTI_TURN],
            ["deepeval"],
            "higher_is_better",
        ),
        _metric(
            "quality.fluency",
            "Fluency",
            "quality",
            [EvalType.CUSTOM, EvalType.MULTI_TURN],
            ["deepeval"],
            "higher_is_better",
        ),
        _metric(
            "quality.consistency",
            "Consistency",
            "quality",
            [EvalType.CUSTOM, EvalType.MULTI_TURN],
            ["deepeval"],
            "higher_is_better",
        ),
        _metric(
            "custom.g_eval", "G-Eval", "custom", [EvalType.CUSTOM], ["deepeval"], "higher_is_better"
        ),
        _metric(
            "custom.answer_match",
            "Answer Match",
            "custom",
            [EvalType.CUSTOM],
            ["deepeval"],
            "higher_is_better",
        ),
        _metric(
            "custom.json_correctness",
            "JSON Correctness",
            "custom",
            [EvalType.CUSTOM],
            ["deepeval"],
            "higher_is_better",
        ),
        _metric(
            "custom.schema_compliance",
            "Schema Compliance",
            "custom",
            [EvalType.CUSTOM],
            ["deepeval"],
            "higher_is_better",
        ),
    ]
    return EvalMetricCatalog(generated_at=utc_now(), metrics=metrics)


def _perf_metric_catalog_entries() -> list[EvalMetricDefinition]:
    metrics: list[EvalMetricDefinition] = []
    for metric_key, display_name, unit, direction in (
        *_PERF_GENERAL_METRICS,
        *_PERF_LATENCY_METRICS,
        *_PERF_TOKEN_METRICS,
        *_PERF_COMPAT_METRICS,
    ):
        metrics.append(
            _metric(
                metric_key,
                display_name,
                "perf",
                [EvalType.PERF],
                ["evalscope"],
                direction,
                unit,
            )
        )
    for percentile in _PERF_PERCENTILES:
        percentile_key = f"p{percentile}"
        for suffix, display_name, unit, direction in _PERF_PERCENTILE_METRIC_SPECS:
            metrics.append(
                _metric(
                    f"perf.{percentile_key}.{suffix}",
                    f"P{percentile} {display_name}",
                    "perf",
                    [EvalType.PERF],
                    ["evalscope"],
                    direction,
                    unit,
                )
            )
    return metrics


def _metric(
    metric_key: str,
    display_name: str,
    category: str,
    eval_types: list[EvalType],
    engine_ids: list[str],
    score_direction: str,
    unit: str | None = "score",
) -> EvalMetricDefinition:
    return EvalMetricDefinition(
        metric_key=metric_key,
        display_name=display_name,
        category=category,
        eval_types=eval_types,
        unit=unit,
        score_direction=score_direction,
        threshold_hint=0.8 if score_direction == "higher_is_better" else None,
        engine_bindings=[EngineMetricBinding(engine_id=engine_id) for engine_id in engine_ids],
    )
