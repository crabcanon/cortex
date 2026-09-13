"""Built-in synthesis engine adapters."""

from __future__ import annotations

import asyncio
import importlib
import inspect
import json
from typing import Any, get_args, get_origin
from urllib.parse import urlparse

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

try:  # pragma: no cover - depends on optional runtime extra
    from deepeval.models import (  # type: ignore[reportMissingImports]
        DeepEvalBaseLLM as _DeepEvalBaseLLM,
    )
except Exception:  # pragma: no cover - light API image does not install DeepEval
    _DeepEvalBaseLLM = object


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


class OpenAICompatibleDeepEvalSynthesisModel(_DeepEvalBaseLLM):  # type: ignore[misc, valid-type]
    """DeepEval Synthesizer model backed by an OpenAI-compatible chat endpoint."""

    def __init__(
        self,
        *,
        model: str,
        provider_config: OpenAICompatibleConfig,
        options: dict[str, Any],
        openai_client_class: type[Any],
        async_openai_client_class: type[Any],
    ) -> None:
        self._model_name = model
        self._base_url = (provider_config.api_url or "").rstrip("/")
        self._api_key = provider_config.api_key
        self._temperature = float(options.get("temperature", 0))
        self._max_tokens = int(options.get("max_tokens", 4096))
        self._timeout = float(options.get("timeout_seconds", 180))
        self._extra_body = options.get("extra_body")
        self._json_mode = options.get("json_mode", True) is not False
        self._response_format = options.get("response_format")
        self._openai_client_class = openai_client_class
        self._async_openai_client_class = async_openai_client_class

    def load_model(self) -> Any:
        return self._new_sync_client()

    def generate(self, prompt: str, schema: Any | None = None, **_: Any) -> Any:
        client = self._new_sync_client()
        try:
            completion = client.chat.completions.create(
                **self._completion_payload(prompt, schema=schema)
            )
        except Exception as exc:
            raise _provider_connection_error(
                exc,
                model=self._model_name,
                base_url=self._base_url,
            ) from exc
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()
        return _coerce_deepeval_schema(_completion_text(completion), schema)

    async def a_generate(self, prompt: str, schema: Any | None = None, **_: Any) -> Any:
        client = self._new_async_client()
        try:
            completion = await client.chat.completions.create(
                **self._completion_payload(prompt, schema=schema)
            )
        except Exception as exc:
            raise _provider_connection_error(
                exc,
                model=self._model_name,
                base_url=self._base_url,
            ) from exc
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                result = close()
                if inspect.isawaitable(result):
                    await result
        return _coerce_deepeval_schema(_completion_text(completion), schema)

    def get_model_name(self) -> str:
        return f"openai-compatible:{self._model_name}"

    def _new_sync_client(self) -> Any:
        return self._openai_client_class(
            base_url=self._base_url,
            api_key=self._api_key,
            timeout=self._timeout,
        )

    def _new_async_client(self) -> Any:
        return self._async_openai_client_class(
            base_url=self._base_url,
            api_key=self._api_key,
            timeout=self._timeout,
        )

    def _completion_payload(self, prompt: str, *, schema: Any | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You generate high-quality synthetic evaluation data. Follow the "
                        "requested schema exactly and return only valid JSON when a schema is "
                        "provided."
                    ),
                },
                {"role": "user", "content": _prompt_with_schema(prompt, schema)},
            ],
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        if schema is not None and self._json_mode:
            payload["response_format"] = (
                dict(self._response_format)
                if isinstance(self._response_format, dict)
                else {"type": "json_object"}
            )
        if isinstance(self._extra_body, dict):
            payload["extra_body"] = dict(self._extra_body)
        return payload


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
                "Enable DeepEval Synthesizer in runtime config and install the optional dependency."
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
        model = _build_deepeval_synthesis_model(
            model=self._model,
            provider_config=self._provider_config,
            options=self._options,
        )
        synthesizer = _construct_supported(
            synthesizer_class,
            {
                "async_mode": self._options.get("async_mode", True),
                "model": model,
                "max_concurrent": self._options.get("max_concurrent"),
                "cost_tracking": bool(self._options.get("cost_tracking", False)),
            },
        )

        try:
            if request.synthesis_type is SynthesisType.CONVERSATION_GOLDENS:
                preview_rows = self._generate_conversational_goldens(synthesizer, request)
            else:
                preview_rows = self._generate_single_turn_goldens(synthesizer, request)
        except TypeError as exc:
            if _is_deepeval_cost_none_error(exc):
                raise CortexError(
                    code="deepeval_synth_cost_tracking_failed",
                    detail=(
                        "DeepEval Synthesizer failed while aggregating native-model cost "
                        "metadata. Configure the synthesis engine with an OpenAI-compatible "
                        "provider base URL and API key so Cortex can use its custom model "
                        "adapter, or set `use_native_deepeval_model=false` in engine options."
                    ),
                    status_code=502,
                ) from exc
            raise

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
        requested_sample_count = _requested_sample_count(request)
        if request.source.documents:
            contexts = [[text] for text in request.source.documents]
            method = getattr(synthesizer, "generate_goldens_from_contexts", None)
            if method is None:
                raise CortexError(
                    code="deepeval_synth_method_missing",
                    detail="DeepEval Synthesizer does not expose `generate_goldens_from_contexts`.",
                    status_code=500,
                )
            goldens = _call_supported(
                method,
                {
                    "contexts": contexts,
                    "include_expected_output": include_expected_output,
                    "max_goldens_per_context": max_goldens_per_context,
                    "max_goldens": requested_sample_count,
                    "num_goldens": requested_sample_count,
                    "goldens_per_context": max_goldens_per_context,
                },
            )
            return _limit_preview_rows(
                [_coerce_preview_row(golden) for golden in goldens],
                request,
            )

        if request.source.inline_records:
            contexts = _extract_contexts_from_inline_records(request)
            method = getattr(synthesizer, "generate_goldens_from_contexts", None)
            if method is None:
                raise CortexError(
                    code="deepeval_synth_method_missing",
                    detail="DeepEval Synthesizer does not expose `generate_goldens_from_contexts`.",
                    status_code=500,
                )
            goldens = _call_supported(
                method,
                {
                    "contexts": contexts,
                    "include_expected_output": include_expected_output,
                    "max_goldens_per_context": max_goldens_per_context,
                    "max_goldens": requested_sample_count,
                    "num_goldens": requested_sample_count,
                    "goldens_per_context": max_goldens_per_context,
                },
            )
            return _limit_preview_rows(
                [_coerce_preview_row(golden) for golden in goldens],
                request,
            )

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
        max_goldens_per_context = _max_goldens_per_context(request)
        requested_sample_count = _requested_sample_count(request)
        goldens = _call_supported(
            method,
            {
                "contexts": contexts,
                "include_expected_outcome": include_expected_outcome,
                "max_goldens_per_context": max_goldens_per_context,
                "max_goldens": requested_sample_count,
                "num_goldens": requested_sample_count,
                "goldens_per_context": max_goldens_per_context,
            },
        )
        return _limit_preview_rows(
            [_coerce_preview_row(golden) for golden in goldens],
            request,
        )


def _max_goldens_per_context(request: SynthesisSyncRequest) -> int:
    requested = _requested_sample_count(request)
    context_count = max(1, _source_context_count(request))
    return max(1, (requested + context_count - 1) // context_count)


def _requested_sample_count(request: SynthesisSyncRequest) -> int:
    return max(1, request.config.sample_count or 1)


def _source_context_count(request: SynthesisSyncRequest) -> int:
    if request.source.documents:
        return len(request.source.documents)
    if request.source.inline_records:
        return len(request.source.inline_records)
    return 1


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
        return {str(key): value for key, value in vars(golden).items() if not key.startswith("_")}
    return {"value": str(golden)}


def _limit_preview_rows(
    rows: list[dict[str, Any]],
    request: SynthesisSyncRequest,
) -> list[dict[str, Any]]:
    if request.config.sample_count is None:
        return rows
    return rows[: _requested_sample_count(request)]


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
    has_var_kwargs = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )
    supported = {
        key: value
        for key, value in payload.items()
        if value is not None and (has_var_kwargs or key in signature.parameters)
    }
    return factory(**supported)


def _call_supported(method: Any, payload: dict[str, Any]) -> Any:
    signature = inspect.signature(method)
    has_var_kwargs = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )
    supported = {
        key: value
        for key, value in payload.items()
        if value is not None and (has_var_kwargs or key in signature.parameters)
    }
    return method(**supported)


def _build_deepeval_synthesis_model(
    *,
    model: str | None,
    provider_config: OpenAICompatibleConfig,
    options: dict[str, Any],
) -> Any:
    if not model or not provider_config.api_url or not provider_config.api_key:
        return model
    if options.get("use_native_deepeval_model") is True:
        return model
    try:
        openai_module = importlib.import_module("openai")
    except Exception:
        return model
    openai_client = getattr(openai_module, "OpenAI", None)
    async_openai_client = getattr(openai_module, "AsyncOpenAI", None)
    if openai_client is None or async_openai_client is None:
        return model
    return OpenAICompatibleDeepEvalSynthesisModel(
        model=model,
        provider_config=provider_config,
        options=dict(options),
        openai_client_class=openai_client,
        async_openai_client_class=async_openai_client,
    )


def _is_deepeval_cost_none_error(exc: TypeError) -> bool:
    message = str(exc)
    return "NoneType" in message and ("+=" in message or "*=" in message)


def _prompt_with_schema(prompt: str, schema: Any | None) -> str:
    if schema is None:
        return prompt
    return (
        f"{prompt}\n\n"
        "Return only valid JSON that matches this schema. Do not include Markdown fences.\n"
        f"{_schema_description(schema)}"
    )


def _schema_description(schema: Any) -> str:
    try:
        if hasattr(schema, "model_json_schema"):
            return json.dumps(schema.model_json_schema(), ensure_ascii=False)
        if hasattr(schema, "schema"):
            return json.dumps(schema.schema(), ensure_ascii=False)
    except Exception:
        return str(schema)
    return str(schema)


def _completion_text(completion: Any) -> str:
    choices = getattr(completion, "choices", None)
    if not choices:
        return ""
    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", None)
    return content if isinstance(content, str) else ""


def _coerce_deepeval_schema(content: str, schema: Any | None) -> Any:
    if schema is None:
        return content
    payload = _extract_json_payload(content)
    parse_errors: list[str] = []
    try:
        if hasattr(schema, "model_validate_json"):
            return schema.model_validate_json(payload)
        if hasattr(schema, "parse_raw"):
            return schema.parse_raw(payload)
        if hasattr(schema, "model_validate"):
            return schema.model_validate(json.loads(payload))
    except Exception as exc:
        parse_errors.append(f"{type(exc).__name__}: {_one_line(str(exc), max_chars=240)}")
    fallback = _coerce_deepeval_schema_fallback(payload, content, schema)
    if fallback is not None:
        return fallback
    raise CortexError(
        code="deepeval_synth_schema_parse_failed",
        detail=(
            f"OpenAI-compatible synthesis model returned content that could not be parsed as "
            f"`{_schema_name(schema)}`. errors={parse_errors or ['unknown']} "
            f"content_excerpt={_one_line(content, max_chars=300)}"
        ),
        status_code=502,
    )


def _coerce_deepeval_schema_fallback(
    payload: str,
    content: str,
    schema: Any,
) -> Any | None:
    schema_fields = _model_fields(schema)
    if "data" in schema_fields:
        item_type = _list_item_type(_field_annotation(schema_fields["data"]))
        item_fields = _model_fields(item_type)
        text_field = _preferred_text_field(item_fields, ("scenario", "input", "response"))
        if item_type is None or text_field is None:
            return None
        texts = _extract_schema_text_items(payload, content, preferred_key=text_field)
        if not texts:
            return None
        items = [_construct_model(item_type, {text_field: text}) for text in texts]
        return _construct_model(schema, {"data": items})

    text_field = _preferred_text_field(schema_fields, ("response", "scenario", "input"))
    if text_field is None:
        return None
    text = _first_schema_text_item(payload, content, preferred_key=text_field)
    if not text:
        return None
    return _construct_model(schema, {text_field: text})


def _extract_schema_text_items(
    payload: str,
    content: str,
    *,
    preferred_key: str,
) -> list[str]:
    parsed = _load_jsonish(payload)
    values = _texts_from_jsonish(parsed, preferred_key=preferred_key) if parsed is not None else []
    if values:
        return values
    return _texts_from_plain_content(content)


def _first_schema_text_item(
    payload: str,
    content: str,
    *,
    preferred_key: str,
) -> str | None:
    values = _extract_schema_text_items(payload, content, preferred_key=preferred_key)
    return values[0] if values else None


def _load_jsonish(value: str) -> Any | None:
    try:
        return json.loads(value)
    except Exception:
        return None


def _texts_from_jsonish(value: Any, *, preferred_key: str) -> list[str]:
    if isinstance(value, dict):
        if isinstance(value.get("data"), list):
            return _texts_from_jsonish(value["data"], preferred_key=preferred_key)
        if preferred_key in value:
            return [_clean_text_item(value[preferred_key])]
        for item in value.values():
            if isinstance(item, str) and item.strip():
                return [_clean_text_item(item)]
        return []
    if isinstance(value, list):
        texts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                item_texts = _texts_from_jsonish(item, preferred_key=preferred_key)
                if item_texts:
                    texts.extend(item_texts)
            elif isinstance(item, str) and item.strip():
                texts.append(_clean_text_item(item))
        return [text for text in texts if text]
    if isinstance(value, str) and value.strip():
        return [_clean_text_item(value)]
    return []


def _texts_from_plain_content(content: str) -> list[str]:
    stripped = _strip_markdown_fence(content)
    lines = [_clean_text_item(line) for line in stripped.splitlines() if _clean_text_item(line)]
    if lines:
        return lines
    cleaned = _clean_text_item(stripped)
    return [cleaned] if cleaned else []


def _strip_markdown_fence(content: str) -> str:
    text = content.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _clean_text_item(value: Any) -> str:
    text = str(value).strip()
    for prefix in ("- ", "* ", "• "):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
    if len(text) > 2 and text[0].isdigit():
        stripped = text.lstrip("0123456789").lstrip(".): ")
        text = stripped or text
    return text.strip().strip('"').strip("'").strip()


def _model_fields(model: Any) -> dict[str, Any]:
    fields = getattr(model, "model_fields", None) or getattr(model, "__fields__", None)
    return fields if isinstance(fields, dict) else {}


def _field_annotation(field: Any) -> Any:
    return getattr(field, "annotation", None) or getattr(field, "outer_type_", None)


def _list_item_type(annotation: Any) -> Any | None:
    origin = get_origin(annotation)
    if origin in {list, tuple}:
        args = get_args(annotation)
        return args[0] if args else None
    return None


def _preferred_text_field(fields: dict[str, Any], candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        if candidate in fields:
            return candidate
    for name, field in fields.items():
        annotation = _field_annotation(field)
        if annotation is str:
            return name
    return None


def _construct_model(model: Any, payload: dict[str, Any]) -> Any:
    if hasattr(model, "model_validate"):
        return model.model_validate(payload)
    return model(**payload)


def _schema_name(schema: Any) -> str:
    return getattr(schema, "__name__", str(schema))


def _extract_json_payload(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    object_start = text.find("{")
    object_end = text.rfind("}")
    array_start = text.find("[")
    array_end = text.rfind("]")
    if object_start >= 0 and object_end > object_start:
        return text[object_start : object_end + 1]
    if array_start >= 0 and array_end > array_start:
        return text[array_start : array_end + 1]
    return text


def _provider_connection_error(exc: Exception, *, model: str, base_url: str) -> CortexError:
    parsed = urlparse(base_url)
    endpoint = base_url.rstrip("/") if parsed.netloc else base_url
    details = [
        f"OpenAI-compatible synthesis call failed for model `{model}` at `{endpoint}`.",
        f"exception={type(exc).__name__}",
    ]
    cause = exc.__cause__ or exc.__context__
    if cause is not None:
        details.append(f"cause={type(cause).__name__}: {_one_line(str(cause))}")
    message = _one_line(str(exc))
    if message:
        details.append(f"message={message}")
    details.append(
        "Check container DNS/proxy/firewall access to the provider endpoint and verify the "
        "configured synthesis base URL, API key, and model ID are present inside the synthesis "
        "worker container."
    )
    return CortexError(
        code="deepeval_synth_provider_connection_failed",
        detail=" ".join(details),
        status_code=502,
    )


def _one_line(value: str, *, max_chars: int = 500) -> str:
    return value.replace("\r", " ").replace("\n", " ")[:max_chars]
