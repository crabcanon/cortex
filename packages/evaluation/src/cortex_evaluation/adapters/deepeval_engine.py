"""DeepEval evaluation engine."""

from __future__ import annotations

import asyncio
import importlib
from typing import Any

from cortex_common import (
    CortexError,
    OpenAICompatibleConfig,
    apply_openai_compatible_environment,
    utc_now,
)
from cortex_contracts import (
    EvalEngineDescriptor,
    EvalMetricRequest,
    EvalMetricResult,
    EvalRunResult,
    EvalSampleCounters,
    EvalScoreCard,
    EvalSyncRequest,
    EvalTestCase,
    EvalType,
)

from .utils.common import _coerce_float, _default_metric_requests, _namespace_scores
from .utils.deepeval_helper import (
    _build_deepeval_case,
    _build_deepeval_judge_model,
    _build_deepeval_metric,
    _select_test_cases,
    deepeval_metric_manifest,
)


class DeepEvalEvaluationEngine:
    def __init__(
        self,
        *,
        available: bool,
        local_available: bool | None = None,
        model: str | None = None,
        provider_config: OpenAICompatibleConfig | None = None,
        options: dict[str, Any] | None = None,
    ) -> None:
        self._local_available = available if local_available is None else local_available
        status = (
            "available"
            if available and self._local_available
            else "degraded"
            if available
            else "disabled"
        )
        notes = (
            None
            if status == "available"
            else (
                "DeepEval is enabled and routable to runtime workers, but the SDK is not "
                "installed in this process; synchronous execution is unavailable here."
            )
            if status == "degraded"
            else "Enable DeepEval in runtime config and install the optional dependency."
        )
        self._model = model
        self._provider_config = provider_config or OpenAICompatibleConfig()
        self._options = dict(options or {})
        self._descriptor = EvalEngineDescriptor(
            engine_id="deepeval",
            display_name="DeepEval",
            provider="Confident AI / OSS",
            availability_status=status,
            execution_modes=["sync", "async"],
            supported_eval_types=[
                EvalType.RAG,
                EvalType.AGENTIC,
                EvalType.MULTI_TURN,
                EvalType.CUSTOM,
            ],
            supported_metric_prefixes=["rag", "agent", "dialog", "quality", "safety", "custom"],
            default_profiles=["rag_default", "agent_default", "dialog_default"],
            notes=notes,
        )

    @property
    def descriptor(self) -> EvalEngineDescriptor:
        return self._descriptor

    async def run(self, request: EvalSyncRequest) -> EvalRunResult:
        if self.descriptor.availability_status == "disabled":
            raise CortexError(
                code="deepeval_runtime_not_available",
                detail=(
                    "DeepEval is disabled for this deployment. Enable the runtime engine and "
                    "install the optional dependency before using `engine_id=deepeval`."
                ),
                status_code=503,
            )
        if not self._local_available:
            raise CortexError(
                code="deepeval_runtime_not_available_in_process",
                detail=(
                    "DeepEval is enabled for async routing, but the SDK is not installed in the "
                    "current API process. Use `/v1/eval/jobs` with a "
                    "`cortex-evaluation-worker-runtime` worker, or install "
                    "`cortex-evaluation[runtime]` in this process for `/v1/eval/sync`."
                ),
                status_code=503,
            )
        if not request.input.test_cases:
            raise CortexError(
                code="deepeval_input_not_supported",
                detail=(
                    "DeepEval requires hydrated inline `input.test_cases` for execution. "
                    "Use inline cases directly, or submit dataset/object-backed jobs through "
                    "the Evaluation Worker so Cortex can expand them before engine execution."
                ),
                status_code=501,
            )

        apply_openai_compatible_environment(self._provider_config)
        metrics_module = importlib.import_module("deepeval.metrics")
        test_case_module = importlib.import_module("deepeval.test_case")
        judge_model = _build_deepeval_judge_model(
            model=self._model,
            provider_config=self._provider_config,
            options=self._options,
        )
        metric_requests = request.metrics or _default_metric_requests(request.eval_type)
        started_at = utc_now()
        metric_results = await asyncio.gather(
            *[
                self._evaluate_metric(
                    request=request,
                    metric_request=metric_request,
                    metrics_module=metrics_module,
                    test_case_module=test_case_module,
                    judge_model=judge_model,
                )
                for metric_request in metric_requests
            ]
        )

        scored_metrics = [metric.score for metric in metric_results if metric.score is not None]
        composite_score = sum(scored_metrics) / len(scored_metrics) if scored_metrics else None
        passed_metric_count = sum(1 for metric in metric_results if metric.status == "passed")
        failed_metric_count = sum(1 for metric in metric_results if metric.status == "failed")
        return EvalRunResult(
            name=request.name,
            eval_type=request.eval_type,
            engine_id="deepeval",
            profile_key=request.profile_key,
            status="succeeded" if failed_metric_count == 0 else "partial",
            source_summary={
                "input_type": request.input.type,
                "test_case_count": len(request.input.test_cases),
            },
            target_summary={"target_type": request.target.type if request.target else None},
            summary=EvalScoreCard(
                overall_passed=failed_metric_count == 0,
                composite_score=composite_score,
                metric_count=len(metric_results),
                passed_metric_count=passed_metric_count,
                failed_metric_count=failed_metric_count,
                summary_by_namespace=_namespace_scores(metric_results),
            ),
            metrics=metric_results,
            samples=EvalSampleCounters(
                total=len(request.input.test_cases),
                passed=passed_metric_count,
                failed=failed_metric_count,
                skipped=sum(1 for metric in metric_results if metric.status in {"warn", "info"}),
            ),
            started_at=started_at,
            completed_at=utc_now(),
        )

    async def _evaluate_metric(
        self,
        *,
        request: EvalSyncRequest,
        metric_request: EvalMetricRequest,
        metrics_module: Any,
        test_case_module: Any,
        judge_model: Any,
    ) -> EvalMetricResult:
        applicable_cases = _select_test_cases(metric_request.metric_key, request.input.test_cases)
        if not applicable_cases:
            return EvalMetricResult(
                metric_key=metric_request.metric_key,
                display_name=metric_request.metric_key,
                status="warn",
                threshold=metric_request.threshold,
                engine_id="deepeval",
                details={"reason": "No compatible test cases were provided for this metric."},
            )

        case_results = await asyncio.gather(
            *[
                asyncio.to_thread(
                    self._measure_case,
                    metric_request,
                    case,
                    metrics_module,
                    test_case_module,
                    judge_model,
                )
                for case in applicable_cases
            ]
        )
        numeric_scores = [
            float(case_result["score"])
            for case_result in case_results
            if isinstance(case_result.get("score"), int | float)
        ]
        mean_score = sum(numeric_scores) / len(numeric_scores) if numeric_scores else None
        threshold = metric_request.threshold
        if mean_score is None:
            status_value = "info"
        elif threshold is None or mean_score >= threshold:
            status_value = "passed"
        else:
            status_value = "failed"
        manifest = deepeval_metric_manifest()
        return EvalMetricResult(
            metric_key=metric_request.metric_key,
            display_name=metric_request.metric_key,
            status=status_value,
            score=mean_score,
            threshold=threshold,
            unit="score",
            engine_id="deepeval",
            native_metric_key=manifest.direct_metrics.get(metric_request.metric_key),
            sample_size=len(case_results),
            details={
                "case_results": case_results,
                "engine_options": dict(self._options),
            },
        )

    def _measure_case(
        self,
        metric_request: EvalMetricRequest,
        case: EvalTestCase,
        metrics_module: Any,
        test_case_module: Any,
        judge_model: Any,
    ) -> dict[str, Any]:
        deepeval_case = _build_deepeval_case(metric_request.metric_key, case, test_case_module)
        metric = _build_deepeval_metric(
            metric_request=metric_request,
            metrics_module=metrics_module,
            test_case_module=test_case_module,
            model=judge_model,
            options=self._options,
        )
        metric.measure(deepeval_case)
        return {
            "score": _coerce_float(getattr(metric, "score", None)),
            "reason": getattr(metric, "reason", None),
            "passed": bool(getattr(metric, "success", False)),
        }
