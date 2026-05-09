"""Focused unit tests for optional knowledge runtime and helper logic."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from uuid import uuid4

import pytest
from cortex_common import CogneeSettings, ConfigError
from cortex_contracts import (
    AccessLevel,
    DatasetRetentionClass,
    KnowledgeDatasetCreateRequest,
    KnowledgeInput,
    KnowledgeInputType,
    SearchRequest,
)
from cortex_domain import DatasetRecord
from cortex_knowledge.operations import (
    KnowledgeOperationService,
    KnowledgeSearchService,
    _json_safe,
)
from cortex_knowledge.runtime import (
    DisabledCogneeRuntime,
    _apply_cognee_model_environment,
    _cognee_sdk_payload,
    _embedding_tokenizer_options,
    _litellm_embedding_model_for_provider,
    _normalize_provider_payload,
    build_cognee_runtime,
)
from cortex_knowledge.service import KnowledgeDatasetService


@dataclass
class _RawHit:
    source_id: str
    title: str
    snippet: str


def test_disabled_cognee_runtime_raises_config_error() -> None:
    runtime = DisabledCogneeRuntime(reason="disabled for tests")

    with pytest.raises(ConfigError, match="disabled for tests"):
        asyncio.run(runtime.search(payload={}))


def test_build_cognee_runtime_returns_disabled_when_configuration_or_module_disables_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disabled = build_cognee_runtime(CogneeSettings(CORTEX_COGNEE_ENABLED=False))

    monkeypatch.setattr("cortex_knowledge.runtime._cognee_available", lambda: False)
    monkeypatch.setattr("cortex_knowledge.runtime._cognee_version", lambda: "0.0-test")

    # Mock _resolved_cognee_config to avoid triggering config requirements
    monkeypatch.setattr("cortex_knowledge.runtime._resolved_cognee_config", lambda _: {})

    unavailable = build_cognee_runtime(CogneeSettings(CORTEX_COGNEE_ENABLED=True))

    assert disabled.descriptor.status == "disabled"
    assert disabled.descriptor.reason == "Cognee runtime is disabled by configuration."
    assert unavailable.descriptor.status == "disabled"
    assert unavailable.descriptor.version == "0.0-test"


def test_knowledge_dataset_service_normalizes_access_policy_and_context() -> None:
    service = KnowledgeDatasetService(DisabledCogneeRuntime(reason="disabled"))
    request = KnowledgeDatasetCreateRequest(
        dataset_key="policy_docs",
        display_name="Policy Docs",
    )
    normalized = service._normalize_access_policy(request.access_policy, owner_actor_id="alice")
    record = DatasetRecord(
        dataset_id="dataset_123",
        tenant_id="tenant_knowledge",
        dataset_key="policy_docs",
        display_name="Policy Docs",
        description=None,
        retention_class=DatasetRetentionClass.STANDARD.value,
        access_level=service._domain_access_level(normalized),
        access_policy=normalized.model_dump(mode="json"),
        metadata={},
        tags=["policy"],
        status="active",
        created_by="alice",
    )

    context = service.build_access_context(record)

    assert normalized.access_level is AccessLevel.TENANT_PRIVATE
    assert normalized.owner_actor_id == "alice"
    assert context["owner_actor_id"] == "alice"
    assert context["attributes"]["dataset_key"] == "policy_docs"
    assert context["attributes"]["tags"] == ["policy"]


def test_knowledge_operation_helpers_normalize_inputs_and_counter_deltas() -> None:
    text_input = KnowledgeInput(
        input_type=KnowledgeInputType.TEXT,
        text="hello knowledge",
        node_set=["policy", "faq"],
        metadata={"source": "inline"},
    )

    item_id = KnowledgeOperationService._dataset_item_id(text_input)
    metadata = KnowledgeOperationService._dataset_item_metadata(text_input)
    counter_delta = KnowledgeOperationService._extract_counter_delta(
        {"counters": {"objects": 1, "documents": 2.0, "graph_nodes": 3}}
    )

    assert item_id.startswith("ditem_")
    assert metadata["source"] == "inline"
    assert metadata["char_length"] == len("hello knowledge")
    assert len(metadata["text_sha256"]) == 64
    assert metadata["node_set"] == ["policy", "faq"]
    assert counter_delta == {"objects": 1, "documents": 2, "graph_nodes": 3}


def test_knowledge_search_service_normalizes_result_variants() -> None:
    response = KnowledgeSearchService._normalize_search_response(
        request=SearchRequest(query_text="rule", dataset_ids=["dataset_123"]),
        runtime_result={
            "result": "answer text",
            "hits": [
                _RawHit(
                    source_id="chunk_1",
                    title="Chunk 1",
                    snippet="A helpful chunk.",
                )
            ],
            "graph_paths": [{"nodes": [{"id": "n1"}], "edges": [{"source": "n1", "target": "n2"}]}],
        },
        dataset_ids=["dataset_123"],
        latency_ms=7,
        trace_context={"trace_id": "trace_1", "span_id": "span_1", "request_id": "req_1"},
    )

    assert response.answer == "answer text"
    assert response.dataset_scope == ["dataset_123"]
    assert response.context_items[0].rank == 1
    assert response.context_items[0].hit_type.value == "chunk"
    assert response.context_items[0].score == 0.0
    assert response.context_items[0].source_id == "chunk_1"
    assert response.graph_paths[0].nodes[0]["id"] == "n1"
    assert response.telemetry is not None
    assert response.telemetry.trace_id == "trace_1"


def test_cognee_llm_config_sets_openai_compatible_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for env_key in (
        "OPENAI_BASE_URL",
        "OPENAI_API_URL",
        "OPENAI_API_BASE",
        "OPENAI_API_KEY",
        "LITELLM_API_BASE",
        "LITELLM_API_KEY",
    ):
        monkeypatch.delenv(env_key, raising=False)

    payload = _normalize_provider_payload(
        "llm",
        {
            "llm_provider": "openrouter",
            "llm_model": "kimi-k2-0905-preview",
            "llm_endpoint": "https://api.moonshot.cn/v1",
            "llm_api_key": "test-key",
        },
    )
    _apply_cognee_model_environment({"llm": payload})

    assert payload["baml_llm_endpoint"] == "https://api.moonshot.cn/v1"
    assert payload["baml_llm_api_key"] == "test-key"
    assert payload["llm_provider"] == "openai"
    assert payload["baml_llm_provider"] == "openai"
    assert os.environ["OPENAI_BASE_URL"] == "https://api.moonshot.cn/v1"
    assert os.environ["OPENAI_API_BASE"] == "https://api.moonshot.cn/v1"
    assert os.environ["LITELLM_API_BASE"] == "https://api.moonshot.cn/v1"
    assert os.environ["OPENAI_API_KEY"] == "test-key"
    assert os.environ["LITELLM_API_KEY"] == "test-key"


def test_cognee_provider_payload_requires_explicit_credentials() -> None:
    with pytest.raises(ConfigError, match="Cognee LLM runtime configuration is incomplete"):
        _normalize_provider_payload(
            "llm",
            {
                "llm_model": "kimi-k2-0905-preview",
                "llm_endpoint": "https://api.moonshot.cn/v1",
            },
        )


def test_cognee_openrouter_embedding_alias_maps_to_openai_with_litellm_model_prefix() -> None:
    payload = _normalize_provider_payload(
        "embedding",
        {
            "embedding_provider": "openrouter",
            "embedding_model": "baai/bge-m3",
            "embedding_endpoint": "https://openrouter.ai/api/v1",
            "embedding_api_key": "test-provider-key",
            "embedding_dimensions": "1024",
        },
    )

    assert payload["embedding_provider"] == "openai"
    assert payload["embedding_model"] == "openrouter/baai/bge-m3"
    assert payload["embedding_endpoint"] == "https://openrouter.ai/api/v1"
    assert payload["embedding_dimensions"] == 1024


def test_cognee_ollama_embedding_alias_maps_to_openai_with_litellm_model_prefix() -> None:
    payload = _normalize_provider_payload(
        "embedding",
        {
            "embedding_provider": "ollama",
            "embedding_model": "nomic-embed-text",
            "embedding_endpoint": "http://host.docker.internal:11434/v1",
            "embedding_api_key": "ollama",
            "embedding_dimensions": "768",
        },
    )

    assert payload["embedding_provider"] == "openai"
    assert payload["embedding_model"] == "ollama/nomic-embed-text"
    assert payload["embedding_endpoint"] == "http://host.docker.internal:11434/v1"
    assert payload["embedding_dimensions"] == 768


def test_litellm_embedding_model_prefix_is_idempotent() -> None:
    assert (
        _litellm_embedding_model_for_provider(
            provider="openrouter",
            model="openrouter/baai/bge-m3",
        )
        == "openrouter/baai/bge-m3"
    )


def test_cognee_embedding_tokenizer_options_are_cortex_runtime_only() -> None:
    payload = {
        "embedding_provider": "openai",
        "embedding_model": "bge-m3",
        "embedding_dimensions": 1024,
        "embedding_endpoint": "https://openrouter.ai/api/v1",
        "embedding_api_key": "test-provider-key",
        "tokenizer": {
            "strategy": "huggingface",
            "model": "BAAI/bge-m3",
            "fallback_strategy": "tiktoken",
        },
    }

    assert _embedding_tokenizer_options(payload) == {
        "strategy": "huggingface",
        "model": "BAAI/bge-m3",
        "encoding": "cl100k_base",
        "fallback_strategy": "tiktoken",
    }
    assert _cognee_sdk_payload("embedding", payload) == {
        "embedding_provider": "openai",
        "embedding_model": "bge-m3",
        "embedding_dimensions": 1024,
        "embedding_endpoint": "https://openrouter.ai/api/v1",
        "embedding_api_key": "test-provider-key",
    }


def test_knowledge_runtime_result_normalization_is_json_safe() -> None:
    class _PipelineRunCompletedLike:
        def model_dump(self, mode: str = "json") -> dict[str, object]:
            assert mode == "json"
            return {
                "status": "PipelineRunCompleted",
                "dataset_id": uuid4(),
                "details": {"nested": _RawHit("source", "title", "snippet")},
            }

    normalized = KnowledgeOperationService._normalize_runtime_result(
        {"result": _PipelineRunCompletedLike()}
    )

    json.dumps(normalized)
    assert normalized["result"]["status"] == "PipelineRunCompleted"
    assert isinstance(normalized["result"]["dataset_id"], str)
    assert normalized["result"]["details"]["nested"]["source_id"] == "source"
    assert _json_safe({"value": uuid4()})["value"]
