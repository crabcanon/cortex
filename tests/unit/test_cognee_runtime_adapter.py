"""Focused tests for Cognee runtime argument translation and result normalization."""

from __future__ import annotations

import asyncio
from enum import Enum

import pytest
from cortex_common import ConfigError
from cortex_knowledge.runtime import PythonCogneeRuntime


class _FakeSearchType(Enum):
    GRAPH_COMPLETION = "GRAPH_COMPLETION"


class _FakeSearchResult:
    def __init__(self, *, search_result: object, dataset_id: str, dataset_name: str) -> None:
        self.search_result = search_result
        self.dataset_id = dataset_id
        self.dataset_name = dataset_name


class _FakeCogneeModule:
    SearchType = _FakeSearchType

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

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
    assert add_result["data"] == ["hello world", "https://example.com/guide"]
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


def test_python_cognee_runtime_translates_memify_and_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, fake_module = _build_runtime(monkeypatch)
    fake_user = object()

    async def _fake_triplet_pipeline(**kwargs: object) -> dict[str, object]:
        return {"pipeline": "triplet_embeddings", **kwargs}

    monkeypatch.setattr(
        runtime, "_resolve_memify_callable", lambda pipeline: _fake_triplet_pipeline
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
