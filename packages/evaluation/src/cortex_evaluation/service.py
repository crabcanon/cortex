"""Evaluation orchestration service."""

from __future__ import annotations

import time

from cortex_common import CortexError, utc_now
from cortex_contracts import (
    EvalEngineList,
    EvalMetricCatalog,
    EvalMetricDefinition,
    EvalRunResult,
    EvalSyncRequest,
    EvalType,
)
from cortex_db import CortexUnitOfWork
from cortex_domain import EvalEngineRecord, EvalMetricDefinitionRecord
from cortex_domain import EvalType as DomainEvalType
from cortex_observability import MetricsFacade
from opentelemetry import trace

from .catalog import default_eval_metric_catalog
from .models import EvalRequestT, EvaluationEngineProtocol, ResolvedEvalRequest
from .registry import EvaluationEngineRegistry


class EvaluationService:
    def __init__(
        self,
        *,
        registry: EvaluationEngineRegistry,
        metric_catalog: EvalMetricCatalog | None = None,
        default_profile_ref: str = "auto_default",
    ) -> None:
        self._registry = registry
        self._metric_catalog = metric_catalog or default_eval_metric_catalog()
        self._default_profile_ref = default_profile_ref
        self._tracer = trace.get_tracer("cortex.evaluation")
        self._metrics = MetricsFacade("cortex.evaluation")

    def list_engines(self) -> EvalEngineList:
        return EvalEngineList(
            generated_at=utc_now(),
            engines=[engine.descriptor for engine in self._registry.list_all()],
        )

    def list_metrics(
        self,
        *,
        eval_type: EvalType | None = None,
        engine_id: str | None = None,
    ) -> EvalMetricCatalog:
        metrics = list(self._metric_catalog.metrics)
        if eval_type is not None:
            metrics = [metric for metric in metrics if eval_type in metric.eval_types]
        if engine_id:
            metrics = [
                metric
                for metric in metrics
                if any(binding.engine_id == engine_id for binding in metric.engine_bindings)
            ]
        return EvalMetricCatalog(generated_at=utc_now(), metrics=metrics)

    def resolve_request(self, request: EvalRequestT) -> ResolvedEvalRequest[EvalRequestT]:
        engine = self._select_engine(request)
        resolved = request.model_copy(
            update={
                "engine_id": engine.descriptor.engine_id,
                "profile_key": request.profile_key or self._default_profile_ref,
            }
        )
        return ResolvedEvalRequest(request=resolved, engine_id=engine.descriptor.engine_id)

    async def run(self, request: EvalSyncRequest) -> EvalRunResult:
        started = time.perf_counter()
        with self._tracer.start_as_current_span("cortex.eval.run") as span:
            resolved = self.resolve_request(request)
            engine = self._registry.get(resolved.engine_id)
            if engine is None:
                raise CortexError(
                    code="eval_engine_missing",
                    detail=f"Evaluation engine `{resolved.engine_id}` is not registered.",
                    status_code=404,
                )
            attributes = {
                "cortex.eval.type": request.eval_type.value,
                "cortex.eval.engine_id": resolved.engine_id,
                "cortex.eval.profile_key": resolved.request.profile_key or "",
                "cortex.eval.input_type": request.input.type,
                "cortex.eval.metric_count": len(request.metrics),
                "cortex.eval.target_type": request.target.type if request.target else "",
            }
            span.set_attributes(attributes)
            labels = {
                "cortex.eval.type": request.eval_type.value,
                "cortex.eval.engine_id": resolved.engine_id,
            }
            try:
                result = await engine.run(resolved.request)
            except Exception as exc:
                span.record_exception(exc)
                span.set_attribute("cortex.eval.status", "failed")
                self._metrics.counter(
                    "cortex.eval.runs",
                    description="Evaluation run attempts.",
                ).add(1, {**labels, "cortex.eval.status": "failed"})
                raise
            if result.engine_id != resolved.engine_id:
                result.engine_id = resolved.engine_id
            if result.profile_key is None:
                result.profile_key = resolved.request.profile_key
            span.set_attribute("cortex.eval.status", result.status)
            span.set_attribute("cortex.eval.overall_passed", result.summary.overall_passed)
            duration_ms = (time.perf_counter() - started) * 1000
            metric_labels = {**labels, "cortex.eval.status": result.status}
            self._metrics.counter(
                "cortex.eval.runs",
                description="Evaluation run attempts.",
            ).add(1, metric_labels)
            self._metrics.histogram(
                "cortex.eval.run.duration",
                unit="ms",
                description="Evaluation run duration.",
            ).record(duration_ms, metric_labels)
            return result

    async def sync_catalog(self, uow: CortexUnitOfWork) -> None:
        for descriptor in self.list_engines().engines:
            await uow.eval_engines.upsert(
                EvalEngineRecord(
                    engine_id=descriptor.engine_id,
                    engine_key=descriptor.engine_id,
                    display_name=descriptor.display_name,
                    engine_kind=descriptor.provider or "evaluation",
                    capability_flags=[value.value for value in descriptor.supported_eval_types],
                    metric_prefixes=list(descriptor.supported_metric_prefixes),
                    supported_modes=list(descriptor.execution_modes),
                    runtime_config={"notes": descriptor.notes} if descriptor.notes else {},
                    status=_status_to_db(descriptor.availability_status),
                )
            )
        for metric in self._metric_catalog.metrics:
            await uow.eval_metric_definitions.upsert(_metric_record(metric))

    def _select_engine(self, request: EvalSyncRequest) -> EvaluationEngineProtocol:
        if request.engine_id != "auto":
            engine = self._registry.get(request.engine_id)
            if engine is None:
                raise CortexError(
                    code="eval_engine_not_available",
                    detail=f"Evaluation engine `{request.engine_id}` is not currently available.",
                    status_code=404,
                )
            if engine.descriptor.availability_status == "disabled":
                raise CortexError(
                    code="eval_engine_not_available",
                    detail=f"Evaluation engine `{request.engine_id}` is not currently available.",
                    status_code=503,
                )
            return engine
        preference = (
            ["evalscope"] if request.eval_type is EvalType.PERF else ["deepeval", "evalscope"]
        )
        available = {
            engine.descriptor.engine_id: engine for engine in self._registry.list_available()
        }
        for engine_id in preference:
            engine = available.get(engine_id)
            if engine is not None:
                return engine
        if available:
            return next(iter(available.values()))
        raise CortexError(
            code="eval_engine_not_available",
            detail="No evaluation engines are currently available.",
            status_code=503,
        )


def _metric_record(metric: EvalMetricDefinition) -> EvalMetricDefinitionRecord:
    return EvalMetricDefinitionRecord(
        metric_key=metric.metric_key,
        display_name=metric.display_name,
        category=metric.category or "custom",
        description=metric.description,
        unit=metric.unit,
        score_direction=metric.score_direction,
        eval_types=_to_domain_eval_types(metric.eval_types),
        engine_bindings=[binding.model_dump(mode="json") for binding in metric.engine_bindings],
        threshold_hint=metric.threshold_hint,
    )


def _status_to_db(availability_status: str) -> str:
    return {
        "available": "active",
        "degraded": "active",
        "disabled": "disabled",
    }.get(availability_status, "active")


def _to_domain_eval_types(eval_types: list[EvalType]) -> list[DomainEvalType]:
    return [DomainEvalType(value.value) for value in eval_types]
