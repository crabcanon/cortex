"""Focused unit tests for unified runtime config loading and wiring."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from cortex_common import CogneeSettings, ParseSettings, load_runtime_config
from cortex_knowledge.runtime import build_cognee_runtime
from cortex_parse import build_parse_service
from cortex_parse.adapters import (
    crawl4ai as crawl4ai_adapter,
)
from cortex_parse.adapters import (
    docling as docling_adapter,
)
from cortex_parse.adapters import (
    llama_parse as llama_parse_adapter,
)
from cortex_parse.adapters import (
    markitdown as markitdown_adapter,
)


def _case_dir(name: str) -> Path:
    root = Path("runtime-test-data")
    root.mkdir(parents=True, exist_ok=True)
    case_dir = root / f"{name}-{time.time_ns()}"
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir


def test_runtime_config_loader_resolves_env_file_and_path_refs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_dir = _case_dir("unit-runtime-config-loader")
    secret_file = case_dir / "reader.key"
    secret_file.write_text("jina-secret", encoding="utf-8")
    config_path = case_dir / "cortex.runtime.yaml"
    config_path.write_text(
        "\n".join(
            [
                "schema_version: cortex.runtime.v1",
                "parse:",
                "  default_profile_ref: runtime_profile",
                "  engines:",
                "    jina_reader:",
                "      base_url: https://r.jina.ai",
                "      api_key_ref: file:./reader.key",
                "knowledge:",
                "  cognee:",
                "    enabled: true",
                "    llm:",
                "      llm_api_key_ref: env:TEST_RUNTIME_TOKEN",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("TEST_RUNTIME_TOKEN", "env-secret")

    loaded = load_runtime_config(config_path)

    assert loaded.config.parse.default_profile_ref == "runtime_profile"
    assert loaded.resolve_reference("env:TEST_RUNTIME_TOKEN") == "env-secret"
    assert loaded.resolve_reference("file:./reader.key") == "jina-secret"
    assert loaded.resolve_reference("path:./reader.key") == str(secret_file.resolve())
    assert loaded.resolve_mapping(
        {
            "api_key_ref": "env:TEST_RUNTIME_TOKEN",
            "artifact_path_ref": "path:./reader.key",
        }
    ) == {
        "api_key": "env-secret",
        "artifact_path": str(secret_file.resolve()),
    }


def test_runtime_config_loader_falls_back_to_project_dotenv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_dir = _case_dir("unit-runtime-config-dotenv")
    (case_dir / "cortex.runtime.yaml").write_text(
        "\n".join(
            [
                "schema_version: cortex.runtime.v1",
                "parse:",
                "  engines:",
                "    jina_reader:",
                "      api_key_ref: env:TEST_DOTENV_TOKEN",
            ]
        ),
        encoding="utf-8",
    )
    (case_dir / ".env").write_text("TEST_DOTENV_TOKEN=dotenv-secret\n", encoding="utf-8")
    monkeypatch.chdir(case_dir)
    monkeypatch.delenv("TEST_DOTENV_TOKEN", raising=False)

    loaded = load_runtime_config("cortex.runtime.yaml")

    assert loaded.resolve_reference("env:TEST_DOTENV_TOKEN") == "dotenv-secret"


@pytest.mark.parametrize(
    ("relative_path", "expected_graph_provider"),
    [
        ("configs/cortex.runtime.local.yaml", "kuzu"),
        ("configs/cortex.runtime.staging.yaml", "kuzu-remote"),
        ("configs/cortex.runtime.prod.yaml", "kuzu-remote"),
    ],
)
def test_environment_runtime_configs_load(relative_path: str, expected_graph_provider: str) -> None:
    loaded = load_runtime_config(relative_path)

    assert loaded.config.parse.engines.llama_parse.mode == "cloud_api"
    assert (
        loaded.config.knowledge.cognee.graph_db["graph_database_provider"]
        == expected_graph_provider
    )


def test_build_parse_service_respects_runtime_engine_enablement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_dir = _case_dir("unit-runtime-config-parse")
    config_path = case_dir / "cortex.runtime.yaml"
    config_path.write_text(
        "\n".join(
            [
                "schema_version: cortex.runtime.v1",
                "parse:",
                "  default_profile_ref: auto_default",
                "  engines:",
                "    crawl4ai:",
                "      enabled: false",
                "    jina_reader:",
                "      enabled: false",
                "    llama_parse:",
                "      enabled: false",
                "    markitdown:",
                "      enabled: true",
                "      options:",
                "        enable_plugins: false",
                "    docling:",
                "      enabled: false",
            ]
        ),
        encoding="utf-8",
    )

    def _fake_load_crawl4ai_sdk():
        raise ImportError("not installed")
    def _fake_load_llama_parse_cls():
        raise ImportError("not installed")
    def _fake_load_markitdown_cls():
        pass
    def _fake_load_docling_cls():
        pass

    monkeypatch.setattr(crawl4ai_adapter, "_load_crawl4ai_sdk", _fake_load_crawl4ai_sdk)
    monkeypatch.setattr(llama_parse_adapter, "_load_llama_parse_cls", _fake_load_llama_parse_cls)
    monkeypatch.setattr(markitdown_adapter, "_load_markitdown_cls", _fake_load_markitdown_cls)
    monkeypatch.setattr(docling_adapter, "_load_document_converter_cls", _fake_load_docling_cls)

    service = build_parse_service(ParseSettings(), load_runtime_config(config_path))
    engines = service._router.list_engines().engines

    assert [engine.engine_key for engine in engines] == ["markitdown"]


class _FakeCogneeConfig:
    def __init__(self) -> None:
        self.calls: dict[str, object] = {}

    def set_llm_config(self, payload: dict[str, object]) -> None:
        self.calls["llm"] = payload

    def set_embedding_config(self, payload: dict[str, object]) -> None:
        self.calls["embedding"] = payload

    def set_vector_db_config(self, payload: dict[str, object]) -> None:
        self.calls["vector_db"] = payload

    def set_graph_db_config(self, payload: dict[str, object]) -> None:
        self.calls["graph_db"] = payload

    def set_relational_db_config(self, payload: dict[str, object]) -> None:
        self.calls["relational_db"] = payload

    def set_migration_db_config(self, payload: dict[str, object]) -> None:
        self.calls["migration_db"] = payload

    def system_root_directory(self, value: str) -> None:
        self.calls["system_root_directory"] = value

    def data_root_directory(self, value: str) -> None:
        self.calls["data_root_directory"] = value

    def monitoring_tool(self, value: str) -> None:
        self.calls["monitoring_tool"] = value


class _FakeCogneeModule:
    def __init__(self) -> None:
        self.config = _FakeCogneeConfig()

    async def add(self, **kwargs: object) -> dict[str, object]:
        return {"method": "add", **kwargs}

    async def cognify(self, **kwargs: object) -> dict[str, object]:
        return {"method": "cognify", **kwargs}

    async def memify(self, **kwargs: object) -> dict[str, object]:
        return {"method": "memify", **kwargs}

    async def search(self, **kwargs: object) -> dict[str, object]:
        return {"method": "search", **kwargs}


def test_build_cognee_runtime_applies_unified_runtime_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_dir = _case_dir("unit-runtime-config-cognee")
    vector_dir = case_dir / "vector-db"
    config_path = case_dir / "cortex.runtime.yaml"
    config_path.write_text(
        "\n".join(
            [
                "schema_version: cortex.runtime.v1",
                "knowledge:",
                "  provider: cognee",
                "  cognee:",
                "    enabled: true",
                "    monitoring_tool: noop",
                "    system_root_directory: ./system",
                "    data_root_directory: ./data",
                "    llm:",
                "      llm_provider: openai",
                "      llm_model: gpt-4.1-mini",
                "      llm_api_key_ref: env:TEST_COGNEE_TOKEN",
                "    embedding:",
                "      embedding_provider: openai",
                "      embedding_model: text-embedding-3-small",
                "      embedding_api_key_ref: env:TEST_COGNEE_TOKEN",
                "    vector_db:",
                "      vector_db_provider: lancedb",
                "      vector_db_url_ref: path:./vector-db",
                "    graph_db:",
                "      graph_database_provider: networkx",
                "    relational_db:",
                "      db_provider: sqlite",
                "      db_url: sqlite:///./.data/cognee.sqlite",
                "    migration_db:",
                "      db_provider: postgres",
                "      db_url: postgresql+asyncpg://cognee:secret@db.internal:5433/migration_db",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("TEST_COGNEE_TOKEN", "cognee-secret")
    fake_module = _FakeCogneeModule()
    monkeypatch.setattr("cortex_knowledge.runtime._cognee_available", lambda: True)
    monkeypatch.setattr("cortex_knowledge.runtime._cognee_version", lambda: "1.2.test")
    monkeypatch.setattr("cortex_knowledge.runtime._load_cognee_module", lambda: fake_module)

    runtime = build_cognee_runtime(CogneeSettings(), load_runtime_config(config_path))

    assert runtime.descriptor.status == "active"
    assert fake_module.config.calls["llm"] == {
        "llm_provider": "openai",
        "llm_model": "gpt-4.1-mini",
        "llm_api_key": "cognee-secret",
    }
    assert fake_module.config.calls["embedding"] == {
        "embedding_provider": "openai",
        "embedding_model": "text-embedding-3-small",
        "embedding_api_key": "cognee-secret",
    }
    assert fake_module.config.calls["vector_db"] == {
        "vector_db_provider": "lancedb",
        "vector_db_url": str(vector_dir.resolve()),
    }
    assert fake_module.config.calls["graph_db"] == {
        "graph_database_provider": "networkx",
    }
    assert fake_module.config.calls["relational_db"] == {
        "db_provider": "sqlite",
        "db_path": str((Path.cwd() / ".data").resolve()),
        "db_name": "cognee.sqlite",
    }
    assert fake_module.config.calls["migration_db"] == {
        "migration_db_provider": "postgres",
        "migration_db_host": "db.internal",
        "migration_db_port": "5433",
        "migration_db_username": "cognee",
        "migration_db_password": "secret",
        "migration_db_name": "migration_db",
    }
    assert fake_module.config.calls["monitoring_tool"] == "none"
    assert fake_module.config.calls["system_root_directory"] == str((case_dir / "system").resolve())
    assert fake_module.config.calls["data_root_directory"] == str((case_dir / "data").resolve())
