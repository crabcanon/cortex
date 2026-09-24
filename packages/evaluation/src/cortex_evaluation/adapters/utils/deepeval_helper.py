"""DeepEval case, metric, and judge-model helpers."""

from __future__ import annotations

import importlib
import inspect
import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

from cortex_common import CortexError, OpenAICompatibleConfig
from cortex_contracts import EvalMetricRequest, EvalTestCase

from ..manifests.metrics import (
    CONVERSATIONAL_METRICS,
    CUSTOM_CRITERIA,
    DEFAULT_CUSTOM_CRITERIA,
    DIRECT_DEEPEVAL_METRICS,
)

try:  # pragma: no cover - depends on optional runtime extra
    from deepeval.models import DeepEvalBaseLLM as _DeepEvalBaseLLM  # type: ignore
except Exception:  # pragma: no cover - light API image does not install DeepEval
    _DeepEvalBaseLLM = object


@dataclass(frozen=True)
class DeepEvalMetricManifest:
    direct_metrics: dict[str, str]
    custom_criteria: dict[str, str]
    conversational_metrics: frozenset[str]
    default_custom_criteria: str


@lru_cache(maxsize=1)
def deepeval_metric_manifest() -> DeepEvalMetricManifest:
    return DeepEvalMetricManifest(
        direct_metrics=dict(DIRECT_DEEPEVAL_METRICS),
        custom_criteria=dict(CUSTOM_CRITERIA),
        conversational_metrics=frozenset(CONVERSATIONAL_METRICS),
        default_custom_criteria=DEFAULT_CUSTOM_CRITERIA,
    )


class OpenAICompatibleDeepEvalModel(_DeepEvalBaseLLM):  # type: ignore[misc, valid-type]
    """DeepEval judge model backed by an OpenAI-compatible chat endpoint."""

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
        self._timeout = float(options.get("timeout_seconds", 120))
        self._extra_body = options.get("extra_body")
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
        content = _completion_text(completion)
        return _coerce_deepeval_schema(content, schema)

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
        content = _completion_text(completion)
        return _coerce_deepeval_schema(content, schema)

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
                        "You are a strict evaluation judge. Follow the user prompt exactly. "
                        "When a JSON schema is provided, return only valid JSON."
                    ),
                },
                {"role": "user", "content": _prompt_with_schema(prompt, schema)},
            ],
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        if isinstance(self._extra_body, dict):
            payload["extra_body"] = dict(self._extra_body)
        return payload


class VersionedConstructorAdapter:
    """Cache constructor signatures for an imported third-party version."""

    def __init__(self, factory: Any) -> None:
        self._factory = factory
        self._signature = inspect.signature(factory)

    def construct(self, payload: dict[str, Any]) -> Any:
        supported = {
            key: value
            for key, value in payload.items()
            if key in self._signature.parameters and value is not None
        }
        try:
            return self._factory(**supported)
        except TypeError:
            fallback = {
                key: value
                for key, value in supported.items()
                if key not in {"include_reason", "async_mode", "verbose_mode", "model"}
            }
            return self._factory(**fallback)


@lru_cache(maxsize=256)
def _constructor_adapter(factory: Any) -> VersionedConstructorAdapter:
    return VersionedConstructorAdapter(factory)


def build_deepeval_judge_model(
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
        importlib.import_module("deepeval.models")
        openai_module = importlib.import_module("openai")
    except Exception:
        return model

    openai_client = getattr(openai_module, "OpenAI", None)
    async_openai_client = getattr(openai_module, "AsyncOpenAI", None)
    if openai_client is None or async_openai_client is None:
        return model
    return OpenAICompatibleDeepEvalModel(
        model=model,
        provider_config=provider_config,
        options=dict(options),
        openai_client_class=openai_client,
        async_openai_client_class=async_openai_client,
    )


def select_test_cases(metric_key: str, test_cases: list[EvalTestCase]) -> list[EvalTestCase]:
    if metric_key in deepeval_metric_manifest().conversational_metrics:
        return [case for case in test_cases if case.conversation_turns]
    return test_cases


def build_deepeval_case(
    metric_key: str,
    case: EvalTestCase,
    test_case_module: Any,
) -> Any:
    if metric_key in deepeval_metric_manifest().conversational_metrics:
        turn_class = getattr(test_case_module, "Turn", None)
        turns = [
            (
                construct_supported(turn_class, {"role": turn.role, "content": turn.content})
                if turn_class is not None
                else {"role": turn.role, "content": turn.content}
            )
            for turn in case.conversation_turns
        ]
        conversational_class = getattr(test_case_module, "ConversationalTestCase", None)
        if conversational_class is None:
            raise CortexError(
                code="deepeval_case_type_missing",
                detail="DeepEval conversational test case support is unavailable.",
                status_code=500,
            )
        return construct_supported(
            conversational_class,
            {"turns": turns, "metadata": case.metadata},
        )

    llm_test_case = getattr(test_case_module, "LLMTestCase", None)
    if llm_test_case is None:
        raise CortexError(
            code="deepeval_case_type_missing",
            detail="DeepEval single-turn test case support is unavailable.",
            status_code=500,
        )
    candidate_payloads = [
        {
            "input": case.user_input,
            "actual_output": case.actual_output,
            "expected_output": case.expected_output,
            "retrieval_context": case.retrieval_contexts,
            "metadata": case.metadata,
        },
        {
            "input": case.user_input,
            "actual_output": case.actual_output,
            "expected_output": case.expected_output,
            "retrieval_contexts": case.retrieval_contexts,
            "metadata": case.metadata,
        },
        {
            "input": case.user_input,
            "actual_output": case.actual_output,
            "expected_output": case.expected_output,
            "context": case.retrieval_contexts,
            "metadata": case.metadata,
        },
    ]
    last_error: Exception | None = None
    for payload in candidate_payloads:
        try:
            return construct_supported(llm_test_case, payload)
        except Exception as exc:  # pragma: no cover - defensive fallback
            last_error = exc
    raise CortexError(
        code="deepeval_case_construction_failed",
        detail=f"Failed to construct DeepEval test case: {last_error}",
        status_code=500,
    )


def build_deepeval_metric(
    *,
    metric_request: EvalMetricRequest,
    metrics_module: Any,
    test_case_module: Any,
    model: str | None,
    options: dict[str, Any],
) -> Any:
    manifest = deepeval_metric_manifest()
    direct_class_name = manifest.direct_metrics.get(metric_request.metric_key)
    metric_class = getattr(metrics_module, direct_class_name, None) if direct_class_name else None
    common_kwargs = {
        "threshold": metric_request.threshold,
        "model": model,
        "include_reason": True,
        "async_mode": options.get("async_mode"),
        "verbose_mode": options.get("verbose_mode"),
        **metric_request.params,
    }
    if metric_class is not None:
        return construct_supported(metric_class, common_kwargs)

    criteria = metric_request.params.get("criteria") or manifest.custom_criteria.get(
        metric_request.metric_key,
        manifest.default_custom_criteria,
    )
    if metric_request.metric_key in manifest.conversational_metrics:
        conversational_metric = getattr(metrics_module, "ConversationalGEval", None)
        if conversational_metric is None:
            raise CortexError(
                code="deepeval_metric_missing",
                detail="DeepEval ConversationalGEval is unavailable for conversational metrics.",
                status_code=500,
            )
        turn_params = getattr(test_case_module, "TurnParams", None)
        evaluation_params = []
        if turn_params is not None:
            evaluation_params = [_enum_member(turn_params, "CONTENT")]
        return construct_supported(
            conversational_metric,
            {
                **common_kwargs,
                "name": metric_request.metric_key,
                "criteria": criteria,
                "evaluation_params": [value for value in evaluation_params if value is not None],
            },
        )

    g_eval_class = getattr(metrics_module, "GEval", None)
    if g_eval_class is None:
        raise CortexError(
            code="deepeval_metric_missing",
            detail="DeepEval GEval is unavailable for custom evaluation metrics.",
            status_code=500,
        )
    llm_params = getattr(test_case_module, "LLMTestCaseParams", None)
    evaluation_params = [
        _enum_member(llm_params, "INPUT"),
        _enum_member(llm_params, "ACTUAL_OUTPUT"),
        _enum_member(llm_params, "EXPECTED_OUTPUT"),
        _enum_member(llm_params, "RETRIEVAL_CONTEXT"),
        _enum_member(llm_params, "RETRIEVAL_CONTEXTS"),
    ]
    return construct_supported(
        g_eval_class,
        {
            **common_kwargs,
            "name": metric_request.metric_key,
            "criteria": criteria,
            "evaluation_params": [value for value in evaluation_params if value is not None],
        },
    )


def construct_supported(factory: Any, payload: dict[str, Any]) -> Any:
    return _constructor_adapter(factory).construct(payload)


def _prompt_with_schema(prompt: str, schema: Any | None) -> str:
    if schema is None:
        return prompt
    return (
        f"{prompt}\n\n"
        "Return only valid JSON that matches this schema. Do not include Markdown fences.\n"
        f"{_schema_description(schema)}"
    )


def _provider_connection_error(exc: Exception, *, model: str, base_url: str) -> CortexError:
    parsed = urlparse(base_url)
    endpoint = base_url.rstrip("/") if parsed.netloc else base_url
    details = [
        f"OpenAI-compatible judge call failed for model `{model}` at `{endpoint}`.",
        f"exception={type(exc).__name__}",
    ]
    cause = exc.__cause__ or exc.__context__
    if cause is not None:
        details.append(f"cause={type(cause).__name__}: {_one_line(str(cause))}")
    message = _one_line(str(exc))
    if message:
        details.append(f"message={message}")
    details.append(
        "Check container DNS/proxy/firewall access to the provider endpoint and verify "
        "the configured base URL, API key, and model ID are present inside the "
        "evaluation worker container."
    )
    return CortexError(
        code="deepeval_provider_connection_failed",
        detail=" ".join(details),
        status_code=502,
    )


def _one_line(value: str, *, max_chars: int = 500) -> str:
    return value.replace("\r", " ").replace("\n", " ")[:max_chars]


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
    try:
        if hasattr(schema, "model_validate_json"):
            return schema.model_validate_json(payload)
        if hasattr(schema, "parse_raw"):
            return schema.parse_raw(payload)
        if hasattr(schema, "model_validate"):
            return schema.model_validate(json.loads(payload))
    except Exception:
        return content
    return content


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


def _enum_member(enum_like: Any, name: str) -> Any | None:
    if enum_like is None:
        return None
    return getattr(enum_like, name, None)


_build_deepeval_judge_model = build_deepeval_judge_model
_build_deepeval_case = build_deepeval_case
_build_deepeval_metric = build_deepeval_metric
_construct_supported = construct_supported
_select_test_cases = select_test_cases
