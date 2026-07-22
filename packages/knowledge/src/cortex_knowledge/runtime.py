"""Optional Cognee runtime adapter."""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import importlib.metadata
import inspect
import warnings
from collections.abc import Awaitable, Callable
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote, urlparse
from uuid import NAMESPACE_URL, UUID, uuid5

from cortex_common import (
    CogneeSettings,
    ConfigError,
    LoadedRuntimeConfig,
    OpenAICompatibleConfig,
    apply_openai_compatible_environment,
    load_runtime_config,
)

from .models import CogneeRuntimeDescriptor, CogneeRuntimeProtocol

_COGNEE_EMBEDDING_TOKENIZER_OPTIONS: dict[str, Any] = {}
_COGNEE_EMBEDDING_TOKENIZER_INTERNAL_KEYS = {
    "tokenizer",
    "embedding_tokenizer_strategy",
    "embedding_tokenizer_model",
    "embedding_tokenizer_encoding",
    "embedding_tokenizer_fallback_strategy",
}

try:  # pragma: no cover - import path depends on installed pydantic version
    from pydantic.warnings import PydanticDeprecatedSince20
except Exception:  # pragma: no cover - fallback for older/newer pydantic
    PydanticDeprecatedSince20 = DeprecationWarning


@contextmanager
def _suppress_known_cognee_import_warnings() -> Any:
    """Suppress known upstream Cognee/Pydantic deprecations during optional imports."""
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=(
                r"'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated\. "
                r"Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead\."
            ),
            category=DeprecationWarning,
            module=r"cognee\.exceptions\.exceptions",
        )
        warnings.filterwarnings(
            "ignore",
            message=(
                r"Using extra keyword arguments on `Field` is deprecated "
                r"and will be removed\..*"
            ),
            category=PydanticDeprecatedSince20,
            module=r"cognee\.infrastructure\.databases\.graph\.config",
        )
        warnings.filterwarnings(
            "ignore",
            message=r"`json_encoders` is deprecated\..*",
            category=PydanticDeprecatedSince20,
            module=r"pydantic\._internal\._generate_schema",
        )
        yield


def _import_cognee_module(module_name: str) -> Any:
    with _suppress_known_cognee_import_warnings():
        return importlib.import_module(module_name)


def _load_cognee_module() -> Any:
    try:
        return _import_cognee_module("cognee")
    except ImportError as exc:  # pragma: no cover - depends on optional dependency
        raise ConfigError(
            "Cognee runtime is not installed. Install `cognee` to enable knowledge operations."
        ) from exc


def _cognee_available() -> bool:
    try:
        _load_cognee_module()
    except Exception:
        return False
    return True


def _cognee_version() -> str | None:
    try:
        return importlib.metadata.version("cognee")
    except importlib.metadata.PackageNotFoundError:  # pragma: no cover - optional dependency
        return None


class DisabledCogneeRuntime(CogneeRuntimeProtocol):
    def __init__(self, *, reason: str) -> None:
        self._descriptor = CogneeRuntimeDescriptor(
            provider_key="cognee",
            display_name="Cognee",
            status="disabled",
            capabilities=[],
            version=_cognee_version(),
            reason=reason,
        )

    @property
    def descriptor(self) -> CogneeRuntimeDescriptor:
        return self._descriptor

    async def add(self, *, dataset: str, payload: dict[str, Any]) -> dict[str, Any]:
        del dataset, payload
        raise ConfigError(self._descriptor.reason or "Cognee runtime is disabled.")

    async def cognify(self, *, dataset: str, payload: dict[str, Any]) -> dict[str, Any]:
        del dataset, payload
        raise ConfigError(self._descriptor.reason or "Cognee runtime is disabled.")

    async def memify(self, *, dataset: str, payload: dict[str, Any]) -> dict[str, Any]:
        del dataset, payload
        raise ConfigError(self._descriptor.reason or "Cognee runtime is disabled.")

    async def search(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        del payload
        raise ConfigError(self._descriptor.reason or "Cognee runtime is disabled.")


class PythonCogneeRuntime(CogneeRuntimeProtocol):
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = dict(config) if isinstance(config, dict) else {}
        available = _cognee_available()
        self._descriptor = CogneeRuntimeDescriptor(
            provider_key="cognee",
            display_name="Cognee",
            status="active" if available else "disabled",
            capabilities=["add", "cognify", "memify", "search"] if available else [],
            version=_cognee_version(),
            reason=None if available else "Cognee runtime module is unavailable.",
        )
        self._module = _load_cognee_module() if available else None
        if self._module is not None:
            _apply_cognee_model_environment(self._config)
            _patch_cognee_embedding_tokenizer_strategy(self._config)
            self._apply_config()

    @property
    def descriptor(self) -> CogneeRuntimeDescriptor:
        return self._descriptor

    async def add(self, *, dataset: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._invoke("add", **self._build_add_kwargs(dataset=dataset, payload=payload))

    async def cognify(self, *, dataset: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._invoke(
            "cognify",
            **self._build_cognify_kwargs(dataset=dataset, payload=payload),
        )

    async def memify(self, *, dataset: str, payload: dict[str, Any]) -> dict[str, Any]:
        pipeline = str(payload.get("pipeline", "")).strip().lower()
        if pipeline in {"", "triplet_embeddings"}:
            callable_ = self._resolve_memify_callable("triplet_embeddings")
            kwargs = await self._build_memify_kwargs(callable_, dataset=dataset)
            return await self._invoke_callable(callable_, **kwargs)
        if pipeline == "session_persistence":
            callable_ = self._resolve_memify_callable("session_persistence")
            session_ids = payload.get("session_ids")
            kwargs = await self._build_memify_kwargs(
                callable_,
                dataset=dataset,
                session_ids=session_ids if isinstance(session_ids, list) else None,
            )
            return await self._invoke_callable(callable_, **kwargs)
        raise ConfigError(f"Cognee memify pipeline `{pipeline or 'default'}` is not supported yet.")

    async def search(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        result = await self._invoke_raw("search", **self._build_search_kwargs(payload=payload))
        return self._normalize_search_result(result)

    async def _invoke(self, method_name: str, **kwargs: Any) -> dict[str, Any]:
        result = await self._invoke_raw(method_name, **kwargs)
        if isinstance(result, dict):
            return result
        return {"result": result}

    async def _invoke_raw(self, method_name: str, **kwargs: Any) -> Any:
        if self._module is None:
            raise ConfigError("Cognee runtime module is unavailable.")
        target = getattr(self._module, method_name, None)
        if target is None:
            raise ConfigError(f"Cognee runtime does not expose `{method_name}`.")
        if asyncio.iscoroutinefunction(target):
            result = await cast(Callable[..., Awaitable[Any]], target)(**kwargs)
        else:
            result = await asyncio.to_thread(cast(Callable[..., Any], target), **kwargs)
        return result

    async def _invoke_callable(self, target: Callable[..., Any], **kwargs: Any) -> dict[str, Any]:
        if asyncio.iscoroutinefunction(target):
            result = await cast(Callable[..., Awaitable[Any]], target)(**kwargs)
        else:
            result = await asyncio.to_thread(cast(Callable[..., Any], target), **kwargs)
        if isinstance(result, dict):
            return result
        return {"result": result}

    def _build_add_kwargs(self, *, dataset: str, payload: dict[str, Any]) -> dict[str, Any]:
        inputs = payload.get("inputs")
        if not isinstance(inputs, list) or not inputs:
            raise ConfigError("Cognee add requires at least one input.")
        data_items: list[Any] = []
        seen_data_ids: set[str] = set()
        node_sets: set[str] = set()
        for raw_input in inputs:
            if not isinstance(raw_input, dict):
                raise ConfigError("Cognee add only accepts structured Cortex knowledge inputs.")
            input_type = str(raw_input.get("input_type", "")).strip().lower()
            if input_type == "text":
                value = raw_input.get("text")
            elif input_type == "uri":
                value = raw_input.get("uri")
            else:
                raise ConfigError(
                    "Cognee add currently supports only `text` and `uri` inputs "
                    "for live runtime execution."
                )
            if not isinstance(value, str) or not value.strip():
                raise ConfigError(f"Cognee add input `{input_type}` is missing its content.")
            normalized_value = value.strip()
            data_id = _cognee_stable_data_id(
                dataset=dataset,
                input_type=input_type,
                raw_input=raw_input,
                value=normalized_value,
            )
            data_id_key = str(data_id)
            if data_id_key in seen_data_ids:
                continue
            seen_data_ids.add(data_id_key)
            metadata = raw_input.get("metadata")
            data_items.append(
                _cognee_data_item(
                    data=normalized_value,
                    label=_strip_optional_string(raw_input.get("label")),
                    data_id=data_id,
                    metadata=metadata if isinstance(metadata, dict) else None,
                )
            )
            if isinstance(raw_input.get("node_set"), list):
                node_sets.update(str(item) for item in raw_input["node_set"] if str(item).strip())

        if not data_items:
            raise ConfigError("Cognee add inputs were all duplicates after normalization.")

        options: dict[str, Any] = (
            dict(payload["options"]) if isinstance(payload.get("options"), dict) else {}
        )
        return {
            "data": data_items,
            "dataset_name": dataset,
            "node_set": sorted(node_sets) or None,
            "incremental_loading": bool(options.get("incremental", True)),
        }

    @staticmethod
    def _build_cognify_kwargs(*, dataset: str, payload: dict[str, Any]) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "datasets": [dataset],
            "incremental_loading": bool(payload.get("incremental_loading", True)),
        }
        chunking = payload.get("chunking")
        if isinstance(chunking, dict):
            target_tokens = chunking.get("target_tokens")
            if isinstance(target_tokens, int | float):
                kwargs["chunk_size"] = int(target_tokens)
        return kwargs

    def _build_search_kwargs(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        query_text = payload.get("query_text")
        if not isinstance(query_text, str) or not query_text.strip():
            raise ConfigError("Cognee search requires a non-empty `query_text`.")
        kwargs: dict[str, Any] = {
            "query_text": query_text,
            "datasets": payload.get("datasets"),
            "top_k": payload.get("top_k", 10),
            "only_context": bool(payload.get("only_context", False)),
            "session_id": payload.get("session_id"),
        }
        search_type_name = str(payload.get("search_type", "GRAPH_COMPLETION"))
        search_type_enum = (
            getattr(self._module, "SearchType", None) if self._module is not None else None
        )
        if isinstance(search_type_enum, type) and issubclass(search_type_enum, Enum):
            try:
                kwargs["query_type"] = search_type_enum[search_type_name]
            except KeyError:
                try:
                    kwargs["query_type"] = search_type_enum(search_type_name)
                except Exception:
                    pass
        return kwargs

    @staticmethod
    def _normalize_search_result(result: Any) -> dict[str, Any]:
        if isinstance(result, dict):
            return dict(result)
        if not isinstance(result, list):
            return {"result": result}

        answer: str | None = None
        context_items: list[dict[str, Any]] = []
        for index, raw_item in enumerate(result, start=1):
            item = PythonCogneeRuntime._object_to_mapping(raw_item)
            dataset_name = item.get("dataset_name")
            dataset_id = item.get("dataset_id")
            raw_result = item.get("search_result")
            if isinstance(raw_result, str):
                answer = answer or raw_result
                context_items.append(
                    {
                        "rank": index,
                        "hit_type": "chunk",
                        "score": max(0.0, 1.0 - ((index - 1) * 0.01)),
                        "source_id": str(dataset_id or f"search_result_{index}"),
                        "title": dataset_name,
                        "snippet": raw_result,
                        "metadata": {
                            "dataset_name": dataset_name,
                            "dataset_id": str(dataset_id) if dataset_id is not None else None,
                        },
                    }
                )
                continue
            mapping = PythonCogneeRuntime._object_to_mapping(raw_result)
            mapping.setdefault("rank", index)
            mapping.setdefault("hit_type", "chunk")
            mapping.setdefault("score", max(0.0, 1.0 - ((index - 1) * 0.01)))
            metadata = mapping.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}
            if dataset_name is not None:
                metadata.setdefault("dataset_name", dataset_name)
            if dataset_id is not None:
                metadata.setdefault("dataset_id", str(dataset_id))
            mapping["metadata"] = metadata
            context_items.append(mapping)
        return {
            "answer": answer,
            "context_items": context_items,
            "graph_paths": [],
        }

    def _resolve_memify_callable(self, pipeline: str) -> Callable[..., Any]:
        if pipeline == "triplet_embeddings":
            module = _import_cognee_module("cognee.memify_pipelines.create_triplet_embeddings")
            return module.create_triplet_embeddings  # type: ignore[attr-defined]
        if pipeline == "session_persistence":
            module = _import_cognee_module(
                "cognee.memify_pipelines.persist_sessions_in_knowledge_graph"
            )
            return module.persist_sessions_in_knowledge_graph_pipeline  # type: ignore[attr-defined]
        raise ConfigError(f"Unknown Cognee memify pipeline `{pipeline}`.")

    @staticmethod
    def _object_to_mapping(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)
        if hasattr(value, "model_dump"):
            dumped = value.model_dump(mode="json")
            return dumped if isinstance(dumped, dict) else {}
        if hasattr(value, "__dict__"):
            return {key: val for key, val in vars(value).items() if not key.startswith("_")}
        return {}

    async def _build_memify_kwargs(
        self,
        target: Callable[..., Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        payload = dict(kwargs)
        if self._callable_accepts_argument(target, "user"):
            payload["user"] = await self._resolve_cognee_user()
        return payload

    async def _resolve_cognee_user(self) -> Any:
        methods_module = _import_cognee_module("cognee.modules.users.methods")
        getter = getattr(methods_module, "get_default_user", None)
        if getter is None:
            raise ConfigError(
                "Cognee runtime does not expose `get_default_user` for memify execution."
            )
        if asyncio.iscoroutinefunction(getter):
            return await cast(Callable[..., Awaitable[Any]], getter)()
        return await asyncio.to_thread(cast(Callable[..., Any], getter))

    @staticmethod
    def _callable_accepts_argument(target: Callable[..., Any], argument_name: str) -> bool:
        try:
            signature = inspect.signature(target)
        except (TypeError, ValueError):
            return False
        if argument_name in signature.parameters:
            return True
        return any(
            parameter.kind is inspect.Parameter.VAR_KEYWORD
            for parameter in signature.parameters.values()
        )

    def _apply_config(self) -> None:
        if self._module is None or not self._config:
            return
        config_api = getattr(self._module, "config", None)
        if config_api is None:
            return
        for field_name, setter_names in (
            ("system_root_directory", ("set_system_root_directory", "system_root_directory")),
            ("data_root_directory", ("set_data_root_directory", "data_root_directory")),
        ):
            value = self._config.get(field_name)
            if not isinstance(value, str) or not value:
                continue
            for setter_name in setter_names:
                setter = getattr(config_api, setter_name, None)
                if callable(setter):
                    setter(value)
                    break

        for field_name, setter_name in (
            ("llm", "set_llm_config"),
            ("embedding", "set_embedding_config"),
            ("vector_db", "set_vector_db_config"),
            ("graph_db", "set_graph_db_config"),
            ("relational_db", "set_relational_db_config"),
            ("migration_db", "set_migration_db_config"),
            ("chunking", "set_chunking_config"),
        ):
            payload = self._config.get(field_name)
            setter = getattr(config_api, setter_name, None)
            if isinstance(payload, dict) and payload and callable(setter):
                setter(_cognee_sdk_payload(field_name, payload))

        monitoring_tool = self._config.get("monitoring_tool")
        if isinstance(monitoring_tool, str) and monitoring_tool:
            for setter_name in ("set_monitoring_tool", "monitoring_tool"):
                setter = getattr(config_api, setter_name, None)
                if callable(setter):
                    setter(monitoring_tool)
                    break
            else:
                if hasattr(config_api, "monitoring_tool"):
                    config_api.monitoring_tool = monitoring_tool


def build_cognee_runtime(
    settings: CogneeSettings,
    runtime_config: LoadedRuntimeConfig | None = None,
) -> CogneeRuntimeProtocol:
    loaded_runtime = runtime_config or load_runtime_config()
    knowledge_config = loaded_runtime.config.knowledge
    if knowledge_config.provider != "cognee":
        return DisabledCogneeRuntime(
            reason=f"Knowledge provider `{knowledge_config.provider}` is not supported yet."
        )

    cognee_config = knowledge_config.cognee
    enabled = settings.enabled if settings.enabled is not None else cognee_config.enabled
    if not enabled:
        return DisabledCogneeRuntime(reason="Cognee runtime is disabled by configuration.")
    runtime = PythonCogneeRuntime(config=_resolved_cognee_config(loaded_runtime))
    if runtime.descriptor.status != "active":
        return DisabledCogneeRuntime(
            reason=runtime.descriptor.reason or "Cognee runtime module is unavailable."
        )
    return runtime


def _resolved_cognee_config(runtime_config: LoadedRuntimeConfig) -> dict[str, Any]:
    config = runtime_config.config.knowledge.cognee
    resolved: dict[str, Any] = {}
    if config.monitoring_tool:
        resolved["monitoring_tool"] = _normalize_monitoring_tool(config.monitoring_tool)
    if config.system_root_directory:
        path = runtime_config.resolve_path(config.system_root_directory)
        resolved["system_root_directory"] = (
            str(path) if path is not None else config.system_root_directory
        )
    if config.data_root_directory:
        path = runtime_config.resolve_path(config.data_root_directory)
        resolved["data_root_directory"] = (
            str(path) if path is not None else config.data_root_directory
        )
    for field_name in (
        "llm",
        "embedding",
        "vector_db",
        "graph_db",
        "relational_db",
        "migration_db",
        "chunking",
    ):
        payload = getattr(config, field_name)
        if payload:
            mapped = runtime_config.resolve_mapping(payload)
            mapped = _normalize_provider_payload(
                field_name,
                {key: value for key, value in mapped.items() if value is not None},
            )
            if field_name == "relational_db":
                mapped = _translate_relational_payload(mapped)
            elif field_name == "migration_db":
                mapped = _translate_migration_payload(mapped)
            resolved[field_name] = mapped
    return resolved


def _normalize_monitoring_tool(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"noop", "none", "disabled", "off", "false", "0"}:
        return "none"
    return value


def _normalize_provider_payload(field_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    if field_name == "llm" and normalized:
        normalized.setdefault("llm_provider", "openai")
        normalized["llm_provider"] = _cognee_openai_compatible_provider(
            normalized.get("llm_provider")
        )
        normalized.setdefault("baml_llm_provider", normalized.get("llm_provider", "openai"))
        normalized["baml_llm_provider"] = _cognee_openai_compatible_provider(
            normalized.get("baml_llm_provider")
        )
        _copy_if_absent(normalized, source_key="llm_model", target_key="baml_llm_model")
        _copy_if_absent(normalized, source_key="llm_endpoint", target_key="baml_llm_endpoint")
        _copy_if_absent(normalized, source_key="llm_api_key", target_key="baml_llm_api_key")
        _require_provider_values(
            normalized,
            field_name="Cognee LLM",
            required_keys=("llm_model", "llm_api_key"),
        )
        return normalized
    if field_name == "embedding" and normalized:
        raw_provider = str(normalized.get("embedding_provider") or "openai").strip().lower()
        normalized.setdefault("embedding_provider", raw_provider or "openai")
        provider = _cognee_openai_compatible_provider(normalized.get("embedding_provider"))
        normalized["embedding_provider"] = provider
        model = normalized.get("embedding_model")
        if isinstance(model, str):
            normalized["embedding_model"] = _litellm_embedding_model_for_provider(
                provider=raw_provider,
                model=model,
            )
        dimensions = normalized.get("embedding_dimensions")
        if isinstance(dimensions, str) and dimensions.strip().isdigit():
            normalized["embedding_dimensions"] = int(dimensions.strip())
        _require_provider_values(
            normalized,
            field_name="Cognee embedding",
            required_keys=("embedding_model", "embedding_api_key"),
        )
    return normalized


def _litellm_embedding_model_for_provider(*, provider: str, model: str) -> str:
    cleaned_model = model.strip()
    if not cleaned_model:
        return cleaned_model
    cleaned_provider = provider.strip().lower()
    prefix = _litellm_embedding_provider_prefix(cleaned_provider)
    if prefix is None:
        return cleaned_model
    if cleaned_model == prefix or cleaned_model.startswith(f"{prefix}/"):
        return cleaned_model
    return f"{prefix}/{cleaned_model}"


def _litellm_embedding_provider_prefix(provider: str) -> str | None:
    if provider in {"openrouter"}:
        return "openrouter"
    if provider in {"ollama"}:
        return "ollama"
    if provider in {"gemini"}:
        return "gemini"
    if provider in {"openai-compatible", "openai_compatible"}:
        return "openai"
    return None


def _cognee_sdk_payload(field_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    if field_name != "embedding":
        return payload
    return {
        key: value
        for key, value in payload.items()
        if key not in _COGNEE_EMBEDDING_TOKENIZER_INTERNAL_KEYS
    }


def _cognee_data_item(
    *,
    data: str,
    label: str | None,
    data_id: UUID,
    metadata: dict[str, Any] | None,
) -> Any:
    try:
        data_item_module = _import_cognee_module("cognee.tasks.ingestion.data_item")
        data_item_class = getattr(data_item_module, "DataItem", None)
        if isinstance(data_item_class, type):
            return data_item_class(
                data=data,
                label=label,
                external_metadata=dict(metadata or {}),
                data_id=data_id,
            )
    except Exception:
        return data
    return data


def _cognee_stable_data_id(
    *,
    dataset: str,
    input_type: str,
    raw_input: dict[str, Any],
    value: str,
) -> UUID:
    metadata = raw_input.get("metadata") if isinstance(raw_input.get("metadata"), dict) else {}
    source_parts = [
        str(dataset),
        input_type,
        _strip_optional_string(raw_input.get("label")) or "",
        _strip_optional_string(metadata.get("source_url")) or "",
        _strip_optional_string(metadata.get("source_name")) or "",
        _strip_optional_string(metadata.get("engine_id")) or "",
        _strip_optional_string(metadata.get("object_id")) or "",
        _strip_optional_string(metadata.get("document_id")) or "",
        _strip_optional_string(metadata.get("markdown_sha256")) or "",
        hashlib.sha256(value.encode("utf-8")).hexdigest(),
    ]
    return uuid5(NAMESPACE_URL, "cortex:cognee-data:" + "\x1f".join(source_parts))


def _cognee_openai_compatible_provider(value: Any) -> str:
    provider = str(value or "openai").strip().lower()
    if provider in {"ollama", "openrouter", "openai-compatible", "openai_compatible"}:
        return "openai"
    return provider


def _apply_cognee_model_environment(config: dict[str, Any]) -> None:
    llm = config.get("llm")
    if not isinstance(llm, dict):
        return
    apply_openai_compatible_environment(
        OpenAICompatibleConfig(
            api_url=_strip_optional_string(llm.get("llm_endpoint")),
            api_key=_strip_optional_string(llm.get("llm_api_key")),
        )
    )


def _patch_cognee_embedding_tokenizer_strategy(config: dict[str, Any]) -> None:
    """Let Cognee chunk arbitrary OpenAI-compatible embedding models.

    Embedding provider model IDs and local tokenizer choices are separate
    concerns. Provider catalogs such as OpenRouter, Ollama, TEI, vLLM, LocalAI,
    or proxy gateways can expose model IDs that are valid for /embeddings but
    unknown to tiktoken. Cortex therefore owns the tokenizer strategy used for
    chunk sizing while preserving the configured embedding model ID for the
    actual provider call.
    """

    global _COGNEE_EMBEDDING_TOKENIZER_OPTIONS
    embedding = config.get("embedding")
    _COGNEE_EMBEDDING_TOKENIZER_OPTIONS = _embedding_tokenizer_options(
        embedding if isinstance(embedding, dict) else {}
    )
    _patch_cognee_litellm_embedding_tokenizer()
    _patch_cognee_tiktoken_unknown_model_fallback()


def _patch_cognee_litellm_embedding_tokenizer() -> None:
    try:
        engine_module = _import_cognee_module(
            "cognee.infrastructure.databases.vector.embeddings.LiteLLMEmbeddingEngine"
        )
    except Exception:
        return

    engine_class = getattr(engine_module, "LiteLLMEmbeddingEngine", None)
    if not isinstance(engine_class, type):
        return
    if getattr(engine_class, "_cortex_tokenizer_strategy_patch", False):
        return

    original_get_tokenizer = engine_class.get_tokenizer

    def _get_tokenizer_with_strategy(self: Any) -> Any:
        strategy = str(_COGNEE_EMBEDDING_TOKENIZER_OPTIONS.get("strategy") or "auto").lower()
        if strategy in {"approximate", "none", "word"}:
            return _CortexApproximateTokenizer(
                max_completion_tokens=int(getattr(self, "max_completion_tokens", 8191) or 8191)
            )
        if strategy in {"tiktoken", "tiktoken_encoding", "cl100k_base"}:
            return _CortexTiktokenEncodingTokenizer(
                encoding_name=str(
                    _COGNEE_EMBEDDING_TOKENIZER_OPTIONS.get("encoding") or "cl100k_base"
                ),
                max_completion_tokens=int(getattr(self, "max_completion_tokens", 8191) or 8191),
            )
        if strategy in {"huggingface", "hf"}:
            return _build_huggingface_tokenizer(self)

        try:
            return original_get_tokenizer(self)
        except Exception:
            fallback = str(
                _COGNEE_EMBEDDING_TOKENIZER_OPTIONS.get("fallback_strategy") or "tiktoken"
            ).lower()
            if fallback in {"approximate", "none", "word"}:
                return _CortexApproximateTokenizer(
                    max_completion_tokens=int(getattr(self, "max_completion_tokens", 8191) or 8191)
                )
            return _CortexTiktokenEncodingTokenizer(
                encoding_name=str(
                    _COGNEE_EMBEDDING_TOKENIZER_OPTIONS.get("encoding") or "cl100k_base"
                ),
                max_completion_tokens=int(getattr(self, "max_completion_tokens", 8191) or 8191),
            )

    engine_class.get_tokenizer = _get_tokenizer_with_strategy
    engine_class._cortex_tokenizer_strategy_patch = True


def _build_huggingface_tokenizer(engine: Any) -> Any:
    model = _COGNEE_EMBEDDING_TOKENIZER_OPTIONS.get("model") or getattr(engine, "model", None)
    try:
        tokenizer_module = _import_cognee_module(
            "cognee.infrastructure.llm.tokenizer.HuggingFace.adapter"
        )
        tokenizer_class = tokenizer_module.HuggingFaceTokenizer
        return tokenizer_class(
            model=str(model),
            max_completion_tokens=int(getattr(engine, "max_completion_tokens", 8191) or 8191),
        )
    except Exception:
        fallback = str(
            _COGNEE_EMBEDDING_TOKENIZER_OPTIONS.get("fallback_strategy") or "tiktoken"
        ).lower()
        if fallback in {"approximate", "none", "word"}:
            return _CortexApproximateTokenizer(
                max_completion_tokens=int(getattr(engine, "max_completion_tokens", 8191) or 8191)
            )
        return _CortexTiktokenEncodingTokenizer(
            encoding_name=str(_COGNEE_EMBEDDING_TOKENIZER_OPTIONS.get("encoding") or "cl100k_base"),
            max_completion_tokens=int(getattr(engine, "max_completion_tokens", 8191) or 8191),
        )


def _patch_cognee_tiktoken_unknown_model_fallback() -> None:
    try:
        tokenizer_module = _import_cognee_module(
            "cognee.infrastructure.llm.tokenizer.TikToken.adapter"
        )
        tiktoken_module = importlib.import_module("tiktoken")
    except Exception:
        return

    tokenizer_class = getattr(tokenizer_module, "TikTokenTokenizer", None)
    if not isinstance(tokenizer_class, type):
        return
    if getattr(tokenizer_class, "_cortex_unknown_model_fallback", False):
        return

    original_init = tokenizer_class.__init__

    def _init_with_fallback(
        self: Any,
        model: str | None = None,
        max_completion_tokens: int = 8191,
    ) -> None:
        try:
            original_init(
                self,
                model=model,
                max_completion_tokens=max_completion_tokens,
            )
        except Exception as exc:
            if not _is_tiktoken_unknown_model_error(exc):
                raise
            self.model = model
            self.max_completion_tokens = max_completion_tokens
            self.tokenizer = tiktoken_module.get_encoding(
                str(_COGNEE_EMBEDDING_TOKENIZER_OPTIONS.get("encoding") or "cl100k_base")
            )

    tokenizer_class.__init__ = _init_with_fallback
    tokenizer_class._cortex_unknown_model_fallback = True


def _is_tiktoken_unknown_model_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "could not automatically map" in message and (
        "tokeniser" in message or "tokenizer" in message
    )


def _embedding_tokenizer_options(embedding: dict[str, Any]) -> dict[str, Any]:
    raw = embedding.get("tokenizer")
    nested = raw if isinstance(raw, dict) else {}
    strategy = _strip_optional_string(
        nested.get("strategy") or embedding.get("embedding_tokenizer_strategy")
    )
    model = _strip_optional_string(
        nested.get("model") or embedding.get("embedding_tokenizer_model")
    )
    encoding = _strip_optional_string(
        nested.get("encoding") or embedding.get("embedding_tokenizer_encoding")
    )
    fallback_strategy = _strip_optional_string(
        nested.get("fallback_strategy") or embedding.get("embedding_tokenizer_fallback_strategy")
    )
    return {
        "strategy": (strategy or "auto").lower(),
        "model": model,
        "encoding": encoding or "cl100k_base",
        "fallback_strategy": (fallback_strategy or "tiktoken").lower(),
    }


class _CortexTiktokenEncodingTokenizer:
    def __init__(self, *, encoding_name: str, max_completion_tokens: int) -> None:
        self.encoding_name = encoding_name
        self.max_completion_tokens = max_completion_tokens
        tiktoken_module = importlib.import_module("tiktoken")
        self.tokenizer = tiktoken_module.get_encoding(encoding_name)

    def extract_tokens(self, text: str) -> list[Any]:
        return list(self.tokenizer.encode(text))

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    def decode_single_token(self, token: int) -> str:
        return self.tokenizer.decode_single_token_bytes(token).decode(
            "utf-8",
            errors="replace",
        )


class _CortexApproximateTokenizer:
    def __init__(self, *, max_completion_tokens: int) -> None:
        self.max_completion_tokens = max_completion_tokens

    def extract_tokens(self, text: str) -> list[str]:
        return text.split()

    def count_tokens(self, text: str) -> int:
        words = text.split()
        if words:
            return len(words)
        return 1 if text else 0

    def decode_single_token(self, token: int) -> str:
        return str(token)


def _require_provider_values(
    payload: dict[str, Any],
    *,
    field_name: str,
    required_keys: tuple[str, ...],
) -> None:
    missing = [
        key
        for key in required_keys
        if not isinstance(payload.get(key), str) or not str(payload.get(key)).strip()
    ]
    if missing:
        raise ConfigError(
            f"{field_name} runtime configuration is incomplete. Missing: {', '.join(missing)}."
        )


def _strip_optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _copy_if_absent(
    payload: dict[str, Any],
    *,
    source_key: str,
    target_key: str,
) -> None:
    value = payload.get(source_key)
    if target_key not in payload and value not in (None, ""):
        payload[target_key] = value


def _translate_relational_payload(payload: dict[str, Any]) -> dict[str, Any]:
    translated = dict(payload)
    provider = str(translated.get("db_provider", "")).lower()
    db_url = translated.pop("db_url", None)
    if isinstance(db_url, str) and db_url:
        translated.update(_translate_db_url(db_url, provider=provider, migration=False))
    return translated


def _translate_migration_payload(payload: dict[str, Any]) -> dict[str, Any]:
    translated = dict(payload)
    provider = str(translated.get("db_provider", "")).lower()
    db_url = translated.pop("db_url", None)
    generic_pairs = (
        ("db_provider", "migration_db_provider"),
        ("db_path", "migration_db_path"),
        ("db_name", "migration_db_name"),
        ("db_host", "migration_db_host"),
        ("db_port", "migration_db_port"),
        ("db_username", "migration_db_username"),
        ("db_password", "migration_db_password"),
    )
    for source_key, target_key in generic_pairs:
        value = translated.pop(source_key, None)
        if value not in (None, "") and target_key not in translated:
            translated[target_key] = value
    if isinstance(db_url, str) and db_url:
        translated.update(_translate_db_url(db_url, provider=provider, migration=True))
    return translated


def _translate_db_url(db_url: str, *, provider: str, migration: bool) -> dict[str, Any]:
    parsed = urlparse(db_url)
    scheme = provider or parsed.scheme.split("+", 1)[0].lower()
    if scheme in {"sqlite"}:
        raw_path = (
            db_url.split("sqlite:///", 1)[1] if db_url.startswith("sqlite:///") else parsed.path
        )
        path = Path(unquote(raw_path))
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        if migration:
            return {
                "migration_db_provider": "sqlite",
                "migration_db_path": str(path.parent),
                "migration_db_name": path.name,
            }
        return {
            "db_provider": "sqlite",
            "db_path": str(path.parent),
            "db_name": path.name,
        }
    if scheme in {"postgres", "postgresql"}:
        db_name = parsed.path.lstrip("/")
        if migration:
            return {
                "migration_db_provider": "postgres",
                "migration_db_host": parsed.hostname or "",
                "migration_db_port": str(parsed.port or 5432),
                "migration_db_username": unquote(parsed.username or ""),
                "migration_db_password": unquote(parsed.password or ""),
                "migration_db_name": db_name,
            }
        return {
            "db_provider": "postgres",
            "db_host": parsed.hostname or "",
            "db_port": str(parsed.port or 5432),
            "db_username": unquote(parsed.username or ""),
            "db_password": unquote(parsed.password or ""),
            "db_name": db_name,
        }
    return {}
