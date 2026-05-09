"""Focused tests for Cognee runtime argument translation and result normalization."""

from __future__ import annotations

import asyncio
import warnings
from enum import Enum
from types import SimpleNamespace

import pytest
from cortex_common import ConfigError
from cortex_knowledge import runtime as runtime_module
from cortex_knowledge.runtime import PythonCogneeRuntime


class _FakeSearchType(Enum):
    GRAPH_COMPLETION = "GRAPH_COMPLETION"


class _FakeSearchResult:
    def __init__(self, *, search_result: object, dataset_id: str, dataset_name: str) -> None:
        self.search_result = search_result
        self.dataset_id = dataset_id
        self.dataset_name = dataset_name


class _FakeDataItem:
    def __init__(
        self,
        *,
        data: object,
        label: str | None = None,
        external_metadata: dict[str, object] | None = None,
        data_id: object | None = None,
    ) -> None:
        self.data = data
        self.label = label
        self.external_metadata = external_metadata or {}
        self.data_id = data_id


class _FakeCogneeModule:
    SearchType = _FakeSearchType

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.config: object | None = None

    async def add(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("add", dict(kwargs)))
        return dict(kwargs)

    async def cognify(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("cognify", dict(kwargs)))
        return dict(kwargs)

    async def search(self, **kwargs: object) -> list[_FakeSearchResult]:
        self.calls.append(("search", dict(kwargs)))
        return [
            _FakeSearchResult(
                search_result="answer:how does it work",
                dataset_id="dataset_123",
                dataset_name="docs",
            )
        ]


def _build_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[PythonCogneeRuntime, _FakeCogneeModule]:
    fake_module = _FakeCogneeModule()
    monkeypatch.setattr("cortex_knowledge.runtime._cognee_available", lambda: True)
    monkeypatch.setattr("cortex_knowledge.runtime._cognee_version", lambda: "0.5.test")
    monkeypatch.setattr("cortex_knowledge.runtime._load_cognee_module", lambda: fake_module)
    monkeypatch.setattr(
        runtime_module,
        "_import_cognee_module",
        lambda name: SimpleNamespace(DataItem=_FakeDataItem)
        if name == "cognee.tasks.ingestion.data_item"
        else None,
    )
    return PythonCogneeRuntime(), fake_module


def test_python_cognee_runtime_translates_add_and_cognify(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, fake_module = _build_runtime(monkeypatch)

    add_result = asyncio.run(
        runtime.add(
            dataset="docs",
            payload={
                "inputs": [
                    {"input_type": "text", "text": "hello world", "node_set": ["alpha"]},
                    {"input_type": "uri", "uri": "https://example.com/guide"},
                ],
                "options": {"incremental": False},
            },
        )
    )
    cognify_result = asyncio.run(
        runtime.cognify(
            dataset="docs",
            payload={
                "incremental_loading": False,
                "chunking": {"target_tokens": 768},
            },
        )
    )

    assert add_result["dataset_name"] == "docs"
    assert [_cognee_input_value(item) for item in add_result["data"]] == [
        "hello world",
        "https://example.com/guide",
    ]
    assert all(_cognee_input_data_id(item) is not None for item in add_result["data"])
    assert add_result["incremental_loading"] is False
    assert add_result["node_set"] == ["alpha"]
    assert cognify_result["datasets"] == ["docs"]
    assert cognify_result["incremental_loading"] is False
    assert cognify_result["chunk_size"] == 768
    assert [name for name, _kwargs in fake_module.calls] == ["add", "cognify"]


def test_python_cognee_runtime_rejects_unresolved_object_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, _fake_module = _build_runtime(monkeypatch)

    with pytest.raises(ConfigError):
        asyncio.run(
            runtime.add(
                dataset="docs",
                payload={
                    "inputs": [
                        {"input_type": "object_id", "object_id": "obj_123"},
                    ]
                },
            )
        )


def test_python_cognee_runtime_applies_root_directories_before_database_configs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeCogneeConfigApi:
        def __init__(self) -> None:
            self.calls: list[tuple[str, object]] = []

        def set_system_root_directory(self, value: str) -> None:
            self.calls.append(("system_root_directory", value))

        def set_graph_db_config(self, payload: dict[str, object]) -> None:
            self.calls.append(("graph_db", dict(payload)))

    fake_module = _FakeCogneeModule()
    fake_config = _FakeCogneeConfigApi()
    fake_module.config = fake_config
    monkeypatch.setattr("cortex_knowledge.runtime._cognee_available", lambda: True)
    monkeypatch.setattr("cortex_knowledge.runtime._cognee_version", lambda: "0.5.test")
    monkeypatch.setattr("cortex_knowledge.runtime._load_cognee_module", lambda: fake_module)

    PythonCogneeRuntime(
        config={
            "system_root_directory": "/app/.data/cognee/system",
            "graph_db": {
                "graph_database_provider": "kuzu",
                "graph_file_path": "/app/.data/cognee/graph/cognee_graph_kuzu",
            },
        }
    )

    assert fake_config.calls[0] == ("system_root_directory", "/app/.data/cognee/system")
    assert fake_config.calls[1] == (
        "graph_db",
        {
            "graph_database_provider": "kuzu",
            "graph_file_path": "/app/.data/cognee/graph/cognee_graph_kuzu",
        },
    )


def test_load_cognee_module_suppresses_known_upstream_deprecation_warnings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    try:
        from pydantic.warnings import PydanticDeprecatedSince20
    except Exception:  # pragma: no cover - fallback for older/newer pydantic
        PydanticDeprecatedSince20 = DeprecationWarning

    fake_module = object()

    def _fake_import(name: str) -> object:
        assert name == "cognee"
        warnings.warn_explicit(
            (
                "'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. "
                "Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead."
            ),
            DeprecationWarning,
            filename="cognee/exceptions/exceptions.py",
            lineno=52,
            module="cognee.exceptions.exceptions",
        )
        warnings.warn_explicit(
            (
                "Using extra keyword arguments on `Field` is deprecated and will be removed. "
                "Use `json_schema_extra` instead."
            ),
            PydanticDeprecatedSince20,
            filename="cognee/infrastructure/databases/graph/config.py",
            lineno=38,
            module="cognee.infrastructure.databases.graph.config",
        )
        warnings.warn_explicit(
            (
                "`json_encoders` is deprecated. See "
                "https://docs.pydantic.dev/2.12/concepts/serialization/"
                "#custom-serializers for alternatives."
            ),
            PydanticDeprecatedSince20,
            filename="pydantic/_internal/_generate_schema.py",
            lineno=319,
            module="pydantic._internal._generate_schema",
        )
        return fake_module

    monkeypatch.setattr(runtime_module.importlib, "import_module", _fake_import)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        loaded = runtime_module._load_cognee_module()

    assert loaded is fake_module
    assert caught == []


def test_cognee_tiktoken_fallback_handles_bge_embedding_models() -> None:
    pytest.importorskip("cognee")
    pytest.importorskip("tiktoken")

    runtime_module._patch_cognee_tiktoken_unknown_model_fallback()
    tokenizer_module = runtime_module._import_cognee_module(
        "cognee.infrastructure.llm.tokenizer.TikToken.adapter"
    )
    tokenizer = tokenizer_module.TikTokenTokenizer(model="bge-m3")

    assert tokenizer.model == "bge-m3"
    assert tokenizer.count_tokens("OpenRouter bge-m3 embedding smoke text.") > 0


def test_cognee_litellm_embedding_tokenizer_strategy_is_model_agnostic() -> None:
    pytest.importorskip("cognee")
    pytest.importorskip("tiktoken")

    runtime_module._patch_cognee_embedding_tokenizer_strategy(
        {
            "embedding": {
                "embedding_model": "provider-catalog/model-that-tiktoken-does-not-know",
                "tokenizer": {
                    "strategy": "tiktoken",
                    "encoding": "cl100k_base",
                },
            }
        }
    )
    engine_module = runtime_module._import_cognee_module(
        "cognee.infrastructure.databases.vector.embeddings.LiteLLMEmbeddingEngine"
    )

    class _FakeEngine:
        model = "provider-catalog/model-that-tiktoken-does-not-know"
        provider = "openai"
        max_completion_tokens = 8191

    tokenizer = engine_module.LiteLLMEmbeddingEngine.get_tokenizer(_FakeEngine())

    assert tokenizer.count_tokens("Any provider embedding model can share token estimation.") > 0


def test_python_cognee_runtime_translates_memify_and_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, fake_module = _build_runtime(monkeypatch)
    fake_user = object()

    async def _fake_triplet_pipeline(**kwargs: object) -> dict[str, object]:
        return {"pipeline": "triplet_embeddings", **kwargs}

    monkeypatch.setattr(
        runtime,
        "_resolve_memify_callable",
        lambda pipeline: _fake_triplet_pipeline,
    )
    monkeypatch.setattr(runtime, "_resolve_cognee_user", lambda: asyncio.sleep(0, result=fake_user))

    memify_result = asyncio.run(
        runtime.memify(
            dataset="docs",
            payload={"pipeline": "triplet_embeddings"},
        )
    )
    search_result = asyncio.run(
        runtime.search(
            payload={
                "query_text": "how does it work",
                "datasets": ["docs"],
                "search_type": "GRAPH_COMPLETION",
                "top_k": 5,
            }
        )
    )

    assert memify_result["pipeline"] == "triplet_embeddings"
    assert memify_result["dataset"] == "docs"
    assert memify_result["user"] is fake_user
    assert fake_module.calls[-1][0] == "search"
    assert fake_module.calls[-1][1]["datasets"] == ["docs"]
    assert fake_module.calls[-1][1]["query_type"] is _FakeSearchType.GRAPH_COMPLETION
    assert search_result["answer"] == "answer:how does it work"
    assert len(search_result["context_items"]) == 1
    assert search_result["context_items"][0]["title"] == "docs"


def test_python_cognee_runtime_builds_stable_data_items_and_deduplicates_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, _fake_module = _build_runtime(monkeypatch)

    kwargs = runtime._build_add_kwargs(
        dataset="docs",
        payload={
            "inputs": [
                {
                    "input_type": "text",
                    "text": "same body",
                    "label": "Doc A",
                    "metadata": {"source_url": "https://example.com/a", "engine_id": "markitdown"},
                },
                {
                    "input_type": "text",
                    "text": "same body",
                    "label": "Doc A",
                    "metadata": {"source_url": "https://example.com/a", "engine_id": "markitdown"},
                },
                {
                    "input_type": "text",
                    "text": "same body",
                    "label": "Doc A",
                    "metadata": {"source_url": "https://example.com/a", "engine_id": "crawl4ai"},
                },
            ]
        },
    )

    assert len(kwargs["data"]) == 2
    assert [_cognee_input_value(item) for item in kwargs["data"]] == ["same body", "same body"]
    assert len({_cognee_input_data_id(item) for item in kwargs["data"]}) == 2


def _cognee_input_value(item: object) -> object:
    return getattr(item, "data", item)


def _cognee_input_data_id(item: object) -> object:
    return getattr(item, "data_id", None)
