"""Built-in synthesis engine adapters."""

from __future__ import annotations

import asyncio
import importlib
import inspect
import json
from typing import Any

from cortex_common import (
    CortexError,
    OpenAICompatibleConfig,
    apply_openai_compatible_environment,
    utc_now,
)
from cortex_contracts import (
    StoredArtifactRef,
    SynthesisEngineDescriptor,
    SynthesisQualityResult,
    SynthesisRunResult,
    SynthesisSummary,
    SynthesisSyncRequest,
    SynthesisType,
)


class DisabledSynthesisEngine:
    def __init__(self, descriptor: SynthesisEngineDescriptor, reason: str) -> None:
        self._descriptor = descriptor.model_copy(update={"notes": reason})

    @property
    def descriptor(self) -> SynthesisEngineDescriptor:
        return self._descriptor

    async def run(self, request: SynthesisSyncRequest) -> SynthesisRunResult:
        del request
        raise CortexError(
            code="synthesis_engine_unavailable",
            detail=f"Synthesis engine `{self.descriptor.engine_id}` is not available.",
            status_code=503,
        )


class SDVSynthesisEngine:
    def __init__(
        self,
        *,
        available: bool,
        local_available: bool | None = None,
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
                "SDV is enabled and routable to runtime workers, but the SDK is not installed in "
                "this process; synchronous execution is unavailable here."
            )
            if status == "degraded"
            else "Enable SDV in runtime config and install the optional dependency."
        )
        self._options = dict(options or {})
        self._descriptor = SynthesisEngineDescriptor(
            engine_id="sdv",
            display_name="SDV",
            provider="DataCebo / OSS",
            availability_status=status,
            supported_synthesis_types=[
                SynthesisType.STRUCTURED_SINGLE_TABLE,
                SynthesisType.STRUCTURED_RELATIONAL,
            ],
            supported_source_types=["dataset", "relational_metadata", "inline_records"],
            output_formats=["csv", "jsonl", "parquet"],
            default_profiles=["structured_default"],
            notes=notes,
        )

    @property
    def descriptor(self) -> SynthesisEngineDescriptor:
        return self._descriptor

    async def run(self, request: SynthesisSyncRequest) -> SynthesisRunResult:
        if self.descriptor.availability_status == "disabled":
            raise CortexError(
                code="sdv_runtime_not_available",
                detail=(
                    "SDV is disabled for this deployment. Enable the runtime engine and install "
                    "the optional dependency before using `engine_id=sdv`."
                ),
                status_code=503,
            )
        if not self._local_available:
            raise CortexError(
                code="sdv_runtime_not_available_in_process",
                detail=(
                    "SDV is enabled for async routing, but the SDK is not installed in the "
                    "current API process. Use `/v1/synthesis/jobs` with a "
                    "`cortex-synthesis-worker-runtime` worker, or install "
                    "`cortex-synthesis[runtime]` in this process for `/v1/synthesis/sync`."
                ),
                status_code=503,
            )
        started_at = utc_now()
        if request.synthesis_type is SynthesisType.STRUCTURED_SINGLE_TABLE:
            payload = await asyncio.to_thread(self._run_single_table, request)
        elif request.synthesis_type is SynthesisType.STRUCTURED_RELATIONAL:
            payload = await asyncio.to_thread(self._run_relational, request)
        else:
            raise CortexError(
                code="sdv_synthesis_type_not_supported",
                detail=(
                    "SDV currently supports `structured_single_table` and "
                    "`structured_relational` only."
                ),
                status_code=400,
            )
        completed_at = utc_now()
        output_count = int(payload["output_count"])
        return SynthesisRunResult(
            name=request.name,
            synthesis_type=request.synthesis_type,
            engine_id="sdv",
            profile_key=request.profile_key,
            status="succeeded",
            source_summary=payload["source_summary"],
            summary=SynthesisSummary(
                requested_sample_count=request.config.sample_count,
                output_sample_count=output_count,
                quality_score=1.0,
                notes=payload["notes"],
            ),
            quality_gates=_evaluate_quality_gates(request, output_count=output_count),
            outputs=[
                StoredArtifactRef(
                    object_id="inline_preview",
                    label="preview",
                    content_type="application/json",
                    format=request.output.output_format or "json",
                    description="Inline preview emitted from SDV synthesis runtime.",
                )
            ],
            started_at=started_at,
            completed_at=completed_at,
        )

    def _run_single_table(self, request: SynthesisSyncRequest) -> dict[str, Any]:
        records = list(request.source.inline_records)
        if not records:
            raise CortexError(
                code="sdv_input_not_supported",
                detail="SDV single-table synthesis currently requires `source.inline_records`.",
                status_code=501,
            )
        pandas_module = importlib.import_module("pandas")
        metadata_module = importlib.import_module("sdv.metadata")
        single_table_module = importlib.import_module("sdv.single_table")
        dataframe = pandas_module.DataFrame(records)
        metadata_class = metadata_module.Metadata
        metadata = metadata_class.detect_from_dataframe(
            data=dataframe,
            table_name=request.source.options.get("table_name", "table"),
        )
        synthesizer_class = single_table_module.GaussianCopulaSynthesizer
        synthesizer = synthesizer_class(metadata)
        synthesizer.fit(dataframe)
        sample_size = request.config.sample_count or len(records)
        synthetic = synthesizer.sample(num_rows=sample_size)
        preview_rows = synthetic.head(min(sample_size, 10)).to_dict(orient="records")
        return {
            "output_count": len(synthetic),
            "notes": ["Generated with SDV GaussianCopulaSynthesizer."],
            "source_summary": {
                "source_type": request.source.type,
                "preview_rows": preview_rows,
                "column_names": list(getattr(synthetic, "columns", [])),
            },
        }

    def _run_relational(self, request: SynthesisSyncRequest) -> dict[str, Any]:
        tables_payload = request.source.options.get("tables")
        if not isinstance(tables_payload, dict) or not tables_payload:
            raise CortexError(
                code="sdv_relational_input_not_supported",
                detail=(
                    "SDV relational synthesis currently expects `source.options.tables` to be a "
                    "mapping of table name to rows."
                ),
                status_code=501,
            )
        pandas_module = importlib.import_module("pandas")
        metadata_module = importlib.import_module("sdv.metadata")
        multi_table_module = importlib.import_module("sdv.multi_table")
        dataframes = {
            str(table_name): pandas_module.DataFrame(rows)
            for table_name, rows in tables_payload.items()
        }
        metadata_class = metadata_module.Metadata
        metadata = metadata_class.detect_from_dataframes(data=dataframes)
        synthesizer_class = multi_table_module.HMASynthesizer
        synthesizer = synthesizer_class(metadata)
        synthesizer.fit(dataframes)
        synthetic = synthesizer.sample(scale=request.config.sample_count or 1)
        preview_tables = {
            table_name: table.head(5).to_dict(orient="records")
            for table_name, table in synthetic.items()
        }
        first_table = next(iter(synthetic.values()))
        return {
            "output_count": len(first_table),
            "notes": ["Generated with SDV HMASynthesizer."],
            "source_summary": {
                "source_type": request.source.type,
                "preview_tables": preview_tables,
                "table_names": list(synthetic),
            },
        }


class DeepEvalSynthesisEngine:
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
                "DeepEval Synthesizer is enabled and routable to runtime workers, but the SDK is "
                "not installed in this process; synchronous execution is unavailable here."
            )
            if status == "degraded"
            else (
                "Enable DeepEval Synthesizer in runtime config and install the optional "
                "dependency."
            )
        )
        self._model = model
        self._provider_config = provider_config or OpenAICompatibleConfig()
        self._options = dict(options or {})
        self._descriptor = SynthesisEngineDescriptor(
            engine_id="deepeval",
            display_name="DeepEval Synthesizer",
            provider="Confident AI / OSS",
            availability_status=status,
            supported_synthesis_types=[
                SynthesisType.RAG_GOLDENS,
                SynthesisType.QA_PAIRS,
                SynthesisType.CONVERSATION_GOLDENS,
                SynthesisType.AGENT_TRAJECTORIES,
                SynthesisType.CUSTOM,
            ],
            supported_source_types=["documents", "object", "objects", "dataset", "inline_records"],
            output_formats=["json", "jsonl"],
            default_profiles=["rag_goldens_default", "conversation_default"],
            notes=notes,
        )

    @property
    def descriptor(self) -> SynthesisEngineDescriptor:
        return self._descriptor

    async def run(self, request: SynthesisSyncRequest) -> SynthesisRunResult:
        if self.descriptor.availability_status == "disabled":
            raise CortexError(
                code="deepeval_synth_runtime_not_available",
                detail=(
                    "DeepEval Synthesizer is disabled for this deployment. Enable the runtime "
                    "engine and install the optional dependency before using `engine_id=deepeval`."
                ),
                status_code=503,
            )
        if not self._local_available:
            raise CortexError(
                code="deepeval_synth_runtime_not_available_in_process",
                detail=(
                    "DeepEval Synthesizer is enabled for async routing, but the SDK is not "
                    "installed in the current API process. Use `/v1/synthesis/jobs` with a "
                    "`cortex-synthesis-worker-runtime` worker, or install "
                    "`cortex-synthesis[runtime]` in this process for `/v1/synthesis/sync`."
                ),
                status_code=503,
            )

        started_at = utc_now()
        payload = await asyncio.to_thread(self._generate_goldens, request)
        completed_at = utc_now()
        output_count = int(payload["output_count"])
        return SynthesisRunResult(
            name=request.name,
            synthesis_type=request.synthesis_type,
            engine_id="deepeval",
            profile_key=request.profile_key,
            status="succeeded",
            source_summary=payload["source_summary"],
            summary=SynthesisSummary(
                requested_sample_count=request.config.sample_count,
                output_sample_count=output_count,
                quality_score=1.0,
                notes=payload["notes"],
            ),
            quality_gates=_evaluate_quality_gates(request, output_count=output_count),
            outputs=[
                StoredArtifactRef(
                    object_id="inline_preview",
                    label="preview",
                    content_type="application/json",
                    format=request.output.output_format or "json",
                    description="Inline preview emitted from DeepEval synthesis runtime.",
                )
            ],
            started_at=started_at,
            completed_at=completed_at,
        )

    def _generate_goldens(self, request: SynthesisSyncRequest) -> dict[str, Any]:
        apply_openai_compatible_environment(self._provider_config)
        synthesizer_module = importlib.import_module("deepeval.synthesizer")
        synthesizer_class = synthesizer_module.Synthesizer
        synthesizer = _construct_supported(
            synthesizer_class,
            {
                "async_mode": self._options.get("async_mode", True),
                "model": self._model,
                "max_concurrent": self._options.get("max_concurrent"),
                "cost_tracking": self._options.get("cost_tracking"),
            },
        )

        if request.synthesis_type is SynthesisType.CONVERSATION_GOLDENS:
            preview_rows = self._generate_conversational_goldens(synthesizer, request)
        else:
            preview_rows = self._generate_single_turn_goldens(synthesizer, request)

        return {
            "output_count": len(preview_rows),
            "notes": ["Generated with DeepEval Synthesizer."],
            "source_summary": {
                "source_type": request.source.type,
                "preview_rows": preview_rows,
            },
        }

    def _generate_single_turn_goldens(
        self,
        synthesizer: Any,
        request: SynthesisSyncRequest,
    ) -> list[dict[str, Any]]:
        include_expected_output = bool(request.config.include_expected_output)
        max_goldens_per_context = _max_goldens_per_context(request)
        if request.source.documents:
            contexts = [[text] for text in request.source.documents]
            method = getattr(synthesizer, "generate_goldens_from_contexts", None)
            if method is None:
                raise CortexError(
                    code="deepeval_synth_method_missing",
                    detail="DeepEval Synthesizer does not expose `generate_goldens_from_contexts`.",
                    status_code=500,
                )
            goldens = method(
                contexts=contexts,
                include_expected_output=include_expected_output,
                max_goldens_per_context=max_goldens_per_context,
            )
            return [_coerce_preview_row(golden) for golden in goldens]

        if request.source.inline_records:
            contexts = _extract_contexts_from_inline_records(request)
            method = getattr(synthesizer, "generate_goldens_from_contexts", None)
            if method is None:
                raise CortexError(
                    code="deepeval_synth_method_missing",
                    detail="DeepEval Synthesizer does not expose `generate_goldens_from_contexts`.",
                    status_code=500,
                )
            goldens = method(
                contexts=contexts,
                include_expected_output=include_expected_output,
                max_goldens_per_context=max_goldens_per_context,
            )
            return [_coerce_preview_row(golden) for golden in goldens]

        raise CortexError(
            code="deepeval_synth_input_not_supported",
            detail=(
                "DeepEval synthesis currently supports `source.documents` or context-like "
                "`source.inline_records`."
            ),
            status_code=501,
        )

    def _generate_conversational_goldens(
        self,
        synthesizer: Any,
        request: SynthesisSyncRequest,
    ) -> list[dict[str, Any]]:
        include_expected_outcome = bool(request.config.include_expected_output)
        method = getattr(synthesizer, "generate_conversational_goldens_from_contexts", None)
        if method is None:
            raise CortexError(
                code="deepeval_synth_method_missing",
                detail=(
                    "DeepEval Synthesizer does not expose "
                    "`generate_conversational_goldens_from_contexts`."
                ),
                status_code=500,
            )
        contexts = (
            [[text] for text in request.source.documents]
            if request.source.documents
            else _extract_contexts_from_inline_records(request)
        )
        goldens = method(
            contexts=contexts,
            include_expected_outcome=include_expected_outcome,
            max_goldens_per_context=_max_goldens_per_context(request),
        )
        return [_coerce_preview_row(golden) for golden in goldens]


def _max_goldens_per_context(request: SynthesisSyncRequest) -> int:
    return max(1, request.config.max_contexts_per_case or request.config.sample_count or 1)


def _extract_contexts_from_inline_records(request: SynthesisSyncRequest) -> list[list[str]]:
    field_mapping = dict(request.source.field_mapping)
    context_field = field_mapping.get("context") or field_mapping.get("document") or "context"
    contexts: list[list[str]] = []
    for record in request.source.inline_records:
        if context_field in record and isinstance(record[context_field], str):
            contexts.append([record[context_field]])
            continue
        rendered = json.dumps(record, ensure_ascii=False)
        contexts.append([rendered])
    if not contexts:
        raise CortexError(
            code="deepeval_synth_input_not_supported",
            detail="No usable contexts were found in `source.inline_records`.",
            status_code=400,
        )
    return contexts


def _coerce_preview_row(golden: Any) -> dict[str, Any]:
    if hasattr(golden, "model_dump"):
        payload = golden.model_dump(mode="json")
        if isinstance(payload, dict):
            return payload
    if isinstance(golden, dict):
        return {str(key): value for key, value in golden.items()}
    if hasattr(golden, "__dict__"):
        return {
            str(key): value
            for key, value in vars(golden).items()
            if not key.startswith("_")
        }
    return {"value": str(golden)}


def _evaluate_quality_gates(
    request: SynthesisSyncRequest,
    *,
    output_count: int,
) -> list[SynthesisQualityResult]:
    results: list[SynthesisQualityResult] = []
    for gate in request.config.quality_gates:
        if gate.metric_key == "quality.row_count_match" and request.config.sample_count:
            score = 1.0 if output_count == request.config.sample_count else 0.0
            threshold = gate.threshold if gate.threshold is not None else 1.0
            results.append(
                SynthesisQualityResult(
                    metric_key=gate.metric_key,
                    status="passed" if score >= threshold else "failed",
                    threshold=threshold,
                    score=score,
                    details={"requested": request.config.sample_count, "actual": output_count},
                )
            )
            continue
        results.append(
            SynthesisQualityResult(
                metric_key=gate.metric_key,
                status="info",
                threshold=gate.threshold,
                details={"reason": "Quality gate is not yet implemented by this adapter."},
            )
        )
    return results


def _construct_supported(factory: Any, payload: dict[str, Any]) -> Any:
    signature = inspect.signature(factory)
    supported = {
        key: value
        for key, value in payload.items()
        if key in signature.parameters and value is not None
    }
    return factory(**supported)
