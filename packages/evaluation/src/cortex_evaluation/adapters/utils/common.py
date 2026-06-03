"""Shared helpers for evaluation adapters."""

from __future__ import annotations

from typing import Any

from cortex_contracts import EvalMetricRequest, EvalMetricResult, EvalType

from ...catalog import default_perf_metric_keys, perf_metric_direction


def default_metric_requests(eval_type: EvalType) -> list[EvalMetricRequest]:
    if eval_type is EvalType.PERF:
        keys = default_perf_metric_keys()
    elif eval_type is EvalType.RAG:
        keys = [
            "rag.faithfulness",
            "rag.answer_relevance",
            "rag.contextual_precision",
            "rag.contextual_recall",
        ]
    elif eval_type is EvalType.AGENTIC:
        keys = ["agent.task_completion", "agent.tool_correctness", "agent.goal_success"]
    elif eval_type is EvalType.MULTI_TURN:
        keys = ["dialog.conversation_relevancy", "dialog.conversation_completeness"]
    else:
        keys = ["quality.correctness", "quality.relevance", "custom.g_eval"]
    return [EvalMetricRequest(metric_key=key) for key in keys]


def metric_status(*, score: float, threshold: float | None, metric_key: str) -> str:
    if threshold is None:
        return "info"
    if perf_metric_direction(metric_key) == "lower_is_better":
        return "passed" if score <= threshold else "failed"
    return "passed" if score >= threshold else "failed"


def namespace_scores(metrics: list[EvalMetricResult]) -> dict[str, float]:
    grouped: dict[str, list[float]] = {}
    for metric in metrics:
        if metric.score is None:
            continue
        namespace = metric.metric_key.split(".", maxsplit=1)[0]
        grouped.setdefault(namespace, []).append(metric.score)
    return {
        namespace: sum(scores) / len(scores)
        for namespace, scores in grouped.items()
        if scores
    }


def perf_metric_unit(metric_key: str) -> str | None:
    if metric_key.endswith("_seconds") or metric_key.endswith("_latency"):
        return "seconds"
    if metric_key.endswith("_ms"):
        return "milliseconds"
    if "tokens_per_second" in metric_key or metric_key.endswith("_tokens_per_second"):
        return "tokens_per_second"
    if metric_key.endswith("_tokens"):
        return "tokens"
    if metric_key in {"perf.qps", "perf.request_rate", "perf.request_throughput"}:
        return "requests_per_second"
    if metric_key.endswith("_requests") or metric_key == "perf.concurrency":
        return "count"
    return None


def coerce_float(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


_default_metric_requests = default_metric_requests
_metric_status = metric_status
_namespace_scores = namespace_scores
_perf_metric_unit = perf_metric_unit
_coerce_float = coerce_float
