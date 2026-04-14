"""OpenAPI contract tests against the published specification."""

from collections.abc import Mapping
from pathlib import Path

import pytest
import yaml
from cortex_api.main import create_app
from cortex_common import load_settings
from cortex_contracts import (
    AddJobRequest,
    CognifyJobRequest,
    DownloadUrlResponse,
    HealthResponse,
    JobAccepted,
    JobStatusDetail,
    KnowledgeDataset,
    KnowledgeDatasetCreateRequest,
    MemifyJobRequest,
    ParseJobRequest,
    ParseResult,
    ParseSyncRequest,
    SearchRequest,
    SearchResponse,
    StorageObject,
    StorageUploadCompleteRequest,
    StorageUploadCreateRequest,
    StorageUploadSession,
)
from fastapi.testclient import TestClient

SPEC_PATH = Path("specs/cortex-api.yaml")
SCHEMA_MODELS: dict[str, type] = {
    "HealthResponse": HealthResponse,
    "JobAccepted": JobAccepted,
    "JobStatus": JobStatusDetail,
    "ParseSyncRequest": ParseSyncRequest,
    "ParseJobRequest": ParseJobRequest,
    "ParseResult": ParseResult,
    "StorageUploadCreateRequest": StorageUploadCreateRequest,
    "StorageUploadCompleteRequest": StorageUploadCompleteRequest,
    "StorageUploadSession": StorageUploadSession,
    "StorageObject": StorageObject,
    "DownloadUrlResponse": DownloadUrlResponse,
    "KnowledgeDatasetCreateRequest": KnowledgeDatasetCreateRequest,
    "KnowledgeDataset": KnowledgeDataset,
    "AddJobRequest": AddJobRequest,
    "CognifyJobRequest": CognifyJobRequest,
    "MemifyJobRequest": MemifyJobRequest,
    "SearchRequest": SearchRequest,
    "SearchResponse": SearchResponse,
}


def _load_documented_openapi() -> dict[str, object]:
    payload = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _runtime_openapi() -> dict[str, object]:
    app = create_app()
    return app.openapi()  # type: ignore[no-any-return]


def _english_summary(value: str | None) -> str | None:
    if value is None:
        return None
    return value.split(" / ")[0].strip()


def _schema_signature(schema: Mapping[str, object]) -> tuple[str | None, set[str], set[str]]:
    schema_type = schema.get("type")
    required_value = schema.get("required", [])
    required = set(required_value) if isinstance(required_value, list) else set()
    properties = schema.get("properties")
    property_names = set(properties) if isinstance(properties, dict) else set()
    return (
        str(schema_type) if schema_type is not None else None,
        required,
        property_names,
    )


def _resolve_documented_schema(
    schema: Mapping[str, object],
    schemas: Mapping[str, object],
) -> dict[str, object]:
    ref = schema.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
        target_name = ref.rsplit("/", maxsplit=1)[-1]
        target = schemas[target_name]
        assert isinstance(target, Mapping)
        return _resolve_documented_schema(target, schemas)

    if "allOf" in schema:
        all_of_items = schema.get("allOf")
        assert isinstance(all_of_items, list)
        merged_type = schema.get("type")
        merged_required: set[str] = set()
        merged_properties: dict[str, object] = {}
        for item in all_of_items:
            assert isinstance(item, Mapping)
            resolved = _resolve_documented_schema(item, schemas)
            if merged_type is None and resolved.get("type") is not None:
                merged_type = resolved.get("type")
            required_value = resolved.get("required", [])
            if isinstance(required_value, list):
                merged_required.update(str(value) for value in required_value)
            properties_value = resolved.get("properties", {})
            if isinstance(properties_value, dict):
                merged_properties.update(properties_value)
        merged: dict[str, object] = {}
        if merged_type is not None:
            merged["type"] = merged_type
        if merged_required:
            merged["required"] = sorted(merged_required)
        if merged_properties:
            merged["properties"] = merged_properties
        return merged

    return dict(schema)


def test_runtime_openapi_paths_match_documented_contract() -> None:
    documented = _load_documented_openapi()
    runtime = _runtime_openapi()

    documented_paths = documented["paths"]
    runtime_paths = runtime["paths"]
    assert isinstance(documented_paths, dict)
    assert isinstance(runtime_paths, dict)
    assert set(runtime_paths) == set(documented_paths)

    for path, runtime_operations in runtime_paths.items():
        documented_operations = documented_paths[path]
        assert isinstance(runtime_operations, dict)
        assert isinstance(documented_operations, dict)
        assert set(runtime_operations) == set(documented_operations)
        for method, runtime_operation in runtime_operations.items():
            documented_operation = documented_operations[method]
            assert isinstance(runtime_operation, dict)
            assert isinstance(documented_operation, dict)
            assert runtime_operation["operationId"] == documented_operation["operationId"]
            assert _english_summary(runtime_operation.get("summary")) == _english_summary(
                documented_operation.get("summary")
            )
            assert runtime_operation["tags"] == documented_operation["tags"]
            runtime_success_codes = {
                code for code in runtime_operation["responses"] if code[0] in {"2", "3"}
            }
            documented_success_codes = {
                code for code in documented_operation["responses"] if code[0] in {"2", "3"}
            }
            assert runtime_success_codes == documented_success_codes
            assert ("requestBody" in runtime_operation) == ("requestBody" in documented_operation)


def test_contract_model_signatures_match_documented_schemas() -> None:
    documented = _load_documented_openapi()
    documented_components = documented["components"]
    assert isinstance(documented_components, dict)
    documented_schemas = documented_components["schemas"]
    assert isinstance(documented_schemas, dict)

    for schema_name, model in SCHEMA_MODELS.items():
        documented_schema = documented_schemas[schema_name]
        assert isinstance(documented_schema, dict)
        resolved_documented_schema = _resolve_documented_schema(
            documented_schema,
            documented_schemas,
        )
        generated_schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
        assert _schema_signature(generated_schema) == _schema_signature(
            resolved_documented_schema
        )


def test_metrics_endpoint_returns_prometheus_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORTEX_DB_DSN", "sqlite+aiosqlite:///./runtime-test-data/openapi.db")
    monkeypatch.setenv("CORTEX_AUTH_MODE", "dev")
    monkeypatch.setenv("CORTEX_OTEL_ENABLED", "false")
    load_settings.cache_clear()
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/metrics")

    load_settings.cache_clear()
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "cortex_build_info" in response.text
    assert "cortex_runtime_up" in response.text
