"""Synthesis orchestration service."""

from __future__ import annotations

import time

from cortex_common import CortexError, utc_now
from cortex_contracts import (
    SynthesisEngineList,
    SynthesisRunResult,
    SynthesisSyncRequest,
    SynthesisType,
)
from cortex_db import CortexUnitOfWork
from cortex_domain import SynthesisEngineRecord
from cortex_observability import MetricsFacade
from opentelemetry import trace

from .models import (
    ResolvedSynthesisRequest,
    SynthesisEngineProtocol,
    SynthesisRequestT,
)
from .registry import SynthesisEngineRegistry


class SynthesisService:
    def __init__(
        self,
        *,
        registry: SynthesisEngineRegistry,
        default_profile_ref: str = "auto_default",
    ) -> None:
        self._registry = registry
        self._default_profile_ref = default_profile_ref
        self._tracer = trace.get_tracer("cortex.synthesis")
        self._metrics = MetricsFacade("cortex.synthesis")

    def list_engines(self) -> SynthesisEngineList:
        return SynthesisEngineList(
            generated_at=utc_now(),
            engines=[engine.descriptor for engine in self._registry.list_all()],
        )

    def resolve_request(
        self,
        request: SynthesisRequestT,
    ) -> ResolvedSynthesisRequest[SynthesisRequestT]:
        engine = self._select_engine(request)
        resolved = request.model_copy(
            update={
                "engine_id": engine.descriptor.engine_id,
                "profile_key": request.profile_key or self._default_profile_ref,
            }
        )
        return ResolvedSynthesisRequest(request=resolved, engine_id=engine.descriptor.engine_id)

    async def run(self, request: SynthesisSyncRequest) -> SynthesisRunResult:
        started = time.perf_counter()
        with self._tracer.start_as_current_span("cortex.synthesis.run") as span:
            resolved = self.resolve_request(request)
            engine = self._registry.get(resolved.engine_id)
            if engine is None:
                raise CortexError(
                    code="synthesis_engine_missing",
                    detail=f"Synthesis engine `{resolved.engine_id}` is not registered.",
                    status_code=404,
                )
            attributes = {
                "cortex.synthesis.type": request.synthesis_type.value,
                "cortex.synthesis.engine_id": resolved.engine_id,
                "cortex.synthesis.profile_key": resolved.request.profile_key or "",
                "cortex.synthesis.source_type": request.source.type,
                "cortex.synthesis.output_format": request.output.output_format or "",
                "cortex.synthesis.requested_sample_count": request.config.sample_count or 0,
            }
            span.set_attributes(attributes)
            labels = {
                "cortex.synthesis.type": request.synthesis_type.value,
                "cortex.synthesis.engine_id": resolved.engine_id,
            }
            try:
                result = await engine.run(resolved.request)
            except Exception as exc:
                span.record_exception(exc)
                span.set_attribute("cortex.synthesis.status", "failed")
                self._metrics.counter(
                    "cortex.synthesis.runs",
                    description="Synthesis run attempts.",
                ).add(1, {**labels, "cortex.synthesis.status": "failed"})
                raise
            if result.profile_key is None:
                result.profile_key = resolved.request.profile_key
            if result.engine_id != resolved.engine_id:
                result.engine_id = resolved.engine_id
            span.set_attribute("cortex.synthesis.status", result.status)
            span.set_attribute(
                "cortex.synthesis.output_sample_count",
                result.summary.output_sample_count or 0,
            )
            duration_ms = (time.perf_counter() - started) * 1000
            metric_labels = {**labels, "cortex.synthesis.status": result.status}
            self._metrics.counter(
                "cortex.synthesis.runs",
                description="Synthesis run attempts.",
            ).add(1, metric_labels)
            self._metrics.histogram(
                "cortex.synthesis.run.duration",
                unit="ms",
                description="Synthesis run duration.",
            ).record(duration_ms, metric_labels)
            return result

    async def sync_catalog(self, uow: CortexUnitOfWork) -> None:
        for descriptor in self.list_engines().engines:
            await uow.synthesis_engines.upsert(
                SynthesisEngineRecord(
                    engine_id=descriptor.engine_id,
                    engine_key=descriptor.engine_id,
                    display_name=descriptor.display_name,
                    engine_kind=descriptor.provider or "synthesis",
                    capability_flags=[
                        value.value for value in descriptor.supported_synthesis_types
                    ],
                    supported_source_types=list(descriptor.supported_source_types),
                    output_formats=list(descriptor.output_formats),
                    runtime_config={"notes": descriptor.notes} if descriptor.notes else {},
                    status=_status_to_db(descriptor.availability_status),
                )
            )

    def _select_engine(self, request: SynthesisSyncRequest) -> SynthesisEngineProtocol:
        if request.engine_id != "auto":
            engine = self._registry.get(request.engine_id)
            if engine is None:
                raise CortexError(
                    code="synthesis_engine_not_available",
                    detail=f"Synthesis engine `{request.engine_id}` is not currently available.",
                    status_code=404,
                )
            if engine.descriptor.availability_status == "disabled":
                raise CortexError(
                    code="synthesis_engine_not_available",
                    detail=f"Synthesis engine `{request.engine_id}` is not currently available.",
                    status_code=503,
                )
            return engine
        preference = (
            ["sdv"]
            if request.synthesis_type
            in {
                SynthesisType.STRUCTURED_SINGLE_TABLE,
                SynthesisType.STRUCTURED_RELATIONAL,
            }
            else ["deepeval", "sdv"]
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
            code="synthesis_engine_not_available",
            detail="No synthesis engines are currently available.",
            status_code=503,
        )


def _status_to_db(availability_status: str) -> str:
    return {
        "available": "active",
        "degraded": "active",
        "disabled": "disabled",
    }.get(availability_status, "active")
