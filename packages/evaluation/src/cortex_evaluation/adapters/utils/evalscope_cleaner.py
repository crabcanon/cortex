"""EvalScope result normalization.

EvalScope stress-test reports can arrive as nested dicts, section tables, or
list rows depending on the service version. This module turns those variants
into a small typed pipeline before the engine builds Cortex result objects.
"""

from __future__ import annotations

import re
from typing import Any

from cortex_common import utc_now
from cortex_contracts import (
    EvalMetricResult,
    EvalRunResult,
    EvalSampleCounters,
    EvalScoreCard,
    EvalSyncRequest,
    EvalType,
)
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import (
    _default_metric_requests,
    _metric_status,
    _namespace_scores,
    _perf_metric_unit,
)

_EVALSCOPE_METRIC_ALIASES = {
    "testdurations": "perf.test_duration_seconds",
    "testdurationsec": "perf.test_duration_seconds",
    "testdurationseconds": "perf.test_duration_seconds",
    "concurrency": "perf.concurrency",
    "requestratereqs": "perf.request_rate",
    "requestratereqsec": "perf.request_rate",
    "requestrate": "perf.request_rate",
    "reqthroughputreqs": "perf.request_throughput",
    "reqthroughputreqsec": "perf.request_throughput",
    "reqthroughput": "perf.request_throughput",
    "requestthroughput": "perf.request_throughput",
    "totalrequests": "perf.total_requests",
    "successrequests": "perf.success_requests",
    "failedrequests": "perf.failed_requests",
    "total": "perf.total_requests",
    "success": "perf.success_requests",
    "failed": "perf.failed_requests",
    "avglatencys": "perf.avg_latency_seconds",
    "avglatencysec": "perf.avg_latency_seconds",
    "avglatencyseconds": "perf.avg_latency_seconds",
    "averagelatency": "perf.avg_latency_seconds",
    "ttftms": "perf.ttft_ms",
    "tpotms": "perf.tpot_ms",
    "itlms": "perf.itl_ms",
    "avginputtokens": "perf.avg_input_tokens",
    "avgoutputtokens": "perf.avg_output_tokens",
    "outputthroughputtoks": "perf.output_throughput_tokens_per_second",
    "outputthroughputtoksec": "perf.output_throughput_tokens_per_second",
    "outputthroughputtokenspersecond": "perf.output_throughput_tokens_per_second",
    "totalthroughputtoks": "perf.total_throughput_tokens_per_second",
    "totalthroughputtoksec": "perf.total_throughput_tokens_per_second",
    "totalthroughputtokenspersecond": "perf.total_throughput_tokens_per_second",
    "qps": "perf.qps",
}

_PERCENTILE_LABEL_ALIASES = {
    "latencys": "latency_seconds",
    "latencysec": "latency_seconds",
    "latencyseconds": "latency_seconds",
    "latency": "latency_seconds",
    "ttftms": "ttft_ms",
    "ttft": "ttft_ms",
    "itlms": "itl_ms",
    "itl": "itl_ms",
    "tpotms": "tpot_ms",
    "tpot": "tpot_ms",
    "inputtokens": "input_tokens",
    "outputtokens": "output_tokens",
    "outputthroughputtoks": "output_throughput_tokens_per_second",
    "outputthroughputtoksec": "output_throughput_tokens_per_second",
    "outputthroughputtokenspersecond": "output_throughput_tokens_per_second",
    "totalthroughputtoks": "total_throughput_tokens_per_second",
    "totalthroughputtoksec": "total_throughput_tokens_per_second",
    "totalthroughputtokenspersecond": "total_throughput_tokens_per_second",
}


class EvalScopePerfMetricCleaner:
    """Collect normalized Cortex perf metric keys from variant EvalScope payloads."""

    def collect(self, payload: dict[str, Any]) -> dict[str, float]:
        values: dict[str, float] = {}
        raw_metrics = self._extract_metrics(payload)
        if isinstance(raw_metrics, dict):
            self._collect(raw_metrics, values)
        self._collect(payload, values)
        self._apply_aliases(values)
        return values

    def _extract_metrics(self, data: dict[str, Any]) -> Any:
        raw_metrics = data.get("metrics")
        if isinstance(raw_metrics, dict):
            return raw_metrics
        result = data.get("result")
        if isinstance(result, dict) and isinstance(result.get("metrics"), dict):
            return result["metrics"]
        results = data.get("results")
        if isinstance(results, dict):
            merged: dict[str, Any] = {}
            for value in results.values():
                if isinstance(value, dict) and isinstance(value.get("metrics"), dict):
                    merged.update(value["metrics"])
            if merged:
                return merged
        return raw_metrics

    def _collect(self, value: Any, output: dict[str, float]) -> None:
        if isinstance(value, dict):
            percentile = _percentile_from_row(value)
            if percentile is not None:
                self._collect_percentile_row(percentile, value, output)
                return
            for raw_key, raw_value in value.items():
                key = str(raw_key)
                self._collect_total_success_failed(key, raw_value, output)
                metric_key = _metric_key_from_label(key)
                numeric_value = _coerce_float_like(raw_value)
                if metric_key is not None and numeric_value is not None:
                    output[metric_key] = numeric_value
                    continue
                percentile_key = _percentile_from_label(key)
                if percentile_key is not None:
                    self._collect_percentile_value(percentile_key, raw_value, output)
                    continue
                percentile_suffix = _percentile_metric_suffix(key)
                if percentile_suffix is not None and isinstance(raw_value, dict):
                    if self._collect_nested_percentiles(
                        raw_value, percentile_suffix, output
                    ):
                        continue
                self._collect(raw_value, output)
            return
        if isinstance(value, list):
            for item in value:
                self._collect(item, output)

    def _collect_total_success_failed(
        self,
        label: str,
        value: Any,
        output: dict[str, float],
    ) -> None:
        normalized = _normalize_label(label)
        if "totalsuccessfailed" not in normalized:
            return
        if isinstance(value, dict):
            for key, metric_key in (
                ("total", "perf.total_requests"),
                ("success", "perf.success_requests"),
                ("failed", "perf.failed_requests"),
            ):
                number = _coerce_float_like(value.get(key) or value.get(key.title()))
                if number is not None:
                    output[metric_key] = number
            return
        if isinstance(value, list | tuple) and len(value) >= 3:
            numbers = [_coerce_float_like(item) for item in value[:3]]
        elif isinstance(value, str):
            numbers = [
                _coerce_float_like(item)
                for item in re.split(r"\s*/\s*|\s*,\s*", value)
            ]
        else:
            numbers = []
        if len(numbers) >= 3 and all(number is not None for number in numbers[:3]):
            # numbers[:3] is guaranteed to be float by the all() check, but pyright
            # can't infer it over a list slice.
            output["perf.total_requests"] = float(numbers[0]) # type: ignore[arg-type]
            output["perf.success_requests"] = float(numbers[1]) # type: ignore[arg-type]
            output["perf.failed_requests"] = float(numbers[2]) # type: ignore[arg-type]

    def _collect_percentile_row(
        self,
        percentile: int,
        row: dict[str, Any],
        output: dict[str, float],
    ) -> None:
        for raw_key, raw_value in row.items():
            if _is_percentile_column(str(raw_key)):
                continue
            suffix = _percentile_metric_suffix(str(raw_key))
            numeric_value = _coerce_float_like(raw_value)
            if suffix is not None and numeric_value is not None:
                output[f"perf.p{percentile}.{suffix}"] = numeric_value

    def _collect_percentile_value(
        self,
        percentile: int,
        value: Any,
        output: dict[str, float],
    ) -> None:
        if isinstance(value, dict):
            self._collect_percentile_row(percentile, value, output)
            return
        numeric_value = _coerce_float_like(value)
        if numeric_value is not None:
            output[f"perf.p{percentile}.latency_seconds"] = numeric_value

    def _collect_nested_percentiles(
        self,
        values: dict[str, Any],
        suffix: str,
        output: dict[str, float],
    ) -> bool:
        collected = False
        for nested_key, nested_value in values.items():
            nested_percentile = _percentile_from_label(str(nested_key))
            nested_numeric = _coerce_float_like(nested_value)
            if nested_percentile is not None and nested_numeric is not None:
                output[f"perf.p{nested_percentile}.{suffix}"] = nested_numeric
                collected = True
        return collected

    def _apply_aliases(self, values: dict[str, float]) -> None:
        if "perf.request_throughput" in values:
            values.setdefault("perf.qps", values["perf.request_throughput"])
        if "perf.output_throughput_tokens_per_second" in values:
            values.setdefault(
                "perf.output_tokens_per_second",
                values["perf.output_throughput_tokens_per_second"],
            )
        if "perf.ttft_ms" in values:
            values.setdefault("perf.ttft", values["perf.ttft_ms"] / 1000.0)
        for percentile in (50, 90, 99):
            latency_key = f"perf.p{percentile}.latency_seconds"
            if latency_key in values:
                values.setdefault(f"perf.p{percentile}_latency", values[latency_key])


class EvalScopePerfResult(BaseModel):
    """Typed normalized view over an EvalScope performance payload."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    metrics: dict[str, float] = Field(default_factory=dict)
    samples: EvalSampleCounters = Field(default_factory=EvalSampleCounters)
    raw: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_payload(cls, value: Any) -> dict[str, Any]:
        data = value if isinstance(value, dict) else {"raw": value}
        cleaner = EvalScopePerfMetricCleaner()
        metrics = cleaner.collect(data)
        return {
            "metrics": metrics,
            "samples": EvalSampleCounters(
                total=_coerce_int(metrics.get("perf.total_requests")),
                passed=_coerce_int(metrics.get("perf.success_requests")),
                failed=_coerce_int(metrics.get("perf.failed_requests")),
            ),
            "raw": data,
        }


def normalize_evalscope_result(
    request: EvalSyncRequest,
    payload: Any,
    started_at,
) -> EvalRunResult:
    data = payload if isinstance(payload, dict) else {"raw": payload}
    metric_requests = request.metrics or _default_metric_requests(request.eval_type)
    metric_thresholds = {metric.metric_key: metric.threshold for metric in metric_requests}
    normalized = EvalScopePerfResult.model_validate(data)
    raw_metrics = normalized.metrics
    metrics: list[EvalMetricResult] = []
    if request.eval_type is EvalType.PERF:
        for metric_request in metric_requests:
            score = raw_metrics.get(metric_request.metric_key)
            threshold = metric_thresholds.get(metric_request.metric_key)
            if isinstance(score, int | float):
                metrics.append(
                    EvalMetricResult(
                        metric_key=metric_request.metric_key,
                        status=_metric_status(
                            score=float(score),
                            threshold=threshold,
                            metric_key=metric_request.metric_key,
                        ),
                        display_name=metric_request.metric_key,
                        score=float(score),
                        threshold=threshold,
                        unit=_perf_metric_unit(metric_request.metric_key),
                        engine_id="evalscope",
                        native_metric_key=metric_request.metric_key,
                    )
                )
    else:
        for metric_key, value in raw_metrics.items():
            score = _coerce_float_like(value)
            if score is None:
                continue
            threshold = metric_thresholds.get(str(metric_key))
            metrics.append(
                EvalMetricResult(
                    metric_key=str(metric_key),
                    status=_metric_status(
                        score=score,
                        threshold=threshold,
                        metric_key=str(metric_key),
                    ),
                    score=score,
                    threshold=threshold,
                    engine_id="evalscope",
                )
            )
    if not metrics and request.eval_type is not EvalType.PERF:
        for metric in metric_requests:
            metrics.append(
                EvalMetricResult(
                    metric_key=metric.metric_key,
                    status="info",
                    threshold=metric.threshold,
                    engine_id="evalscope",
                    details={"reason": "No normalized EvalScope metrics were present."},
                )
            )
    passed_metric_count = sum(1 for metric in metrics if metric.status == "passed")
    failed_metric_count = sum(1 for metric in metrics if metric.status == "failed")
    return EvalRunResult(
        name=request.name,
        eval_type=request.eval_type,
        engine_id="evalscope",
        profile_key=request.profile_key,
        status="succeeded" if failed_metric_count == 0 else "partial",
        source_summary={"input_type": request.input.type},
        target_summary={
            "target_type": request.target.type if request.target else None,
            "protocol": request.target.protocol if request.target else None,
            "model_ref": request.target.model_ref if request.target else None,
            "has_api_key": bool(request.target and request.target.api_key),
        },
        summary=EvalScoreCard(
            overall_passed=failed_metric_count == 0,
            metric_count=len(metrics),
            passed_metric_count=passed_metric_count,
            failed_metric_count=failed_metric_count,
            summary_by_namespace=_namespace_scores(metrics),
        ),
        metrics=metrics,
        samples=normalized.samples,
        started_at=started_at,
        completed_at=utc_now(),
    )


def _extract_evalscope_metric_values(data: dict[str, Any]) -> dict[str, float]:
    return EvalScopePerfResult.model_validate(data).metrics


def _normalize_label(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", label.lower())


def _metric_key_from_label(label: str) -> str | None:
    if label.startswith("perf."):
        return label
    return _EVALSCOPE_METRIC_ALIASES.get(_normalize_label(label))


def _percentile_metric_suffix(label: str) -> str | None:
    return _PERCENTILE_LABEL_ALIASES.get(_normalize_label(label))


def _percentile_from_row(row: dict[str, Any]) -> int | None:
    for key in ("percentile", "Percentile", "P", "p", "quantile", "Quantile"):
        if key in row:
            return _percentile_from_label(str(row[key]))
    return None


def _percentile_from_label(label: str) -> int | None:
    stripped = str(label).strip().lower().lstrip("p")
    try:
        value = int(float(stripped))
    except ValueError:
        return None
    return value if value in {1, 5, 10, 25, 50, 66, 75, 80, 90, 95, 98, 99} else None


def _is_percentile_column(label: str) -> bool:
    return _normalize_label(label) in {"percentile", "p", "quantile"}


def _coerce_float_like(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
        if match:
            return float(match.group(0))
    return None


def _coerce_int(value: Any) -> int | None:
    number = _coerce_float_like(value)
    return int(number) if number is not None else None


_normalize_evalscope_result = normalize_evalscope_result
