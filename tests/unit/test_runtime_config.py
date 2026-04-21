"""Focused unit tests for unified runtime config loading and wiring."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
from cortex_common import CogneeSettings, ConfigError, ParseSettings, load_runtime_config
from cortex_knowledge.runtime import build_cognee_runtime
from cortex_parse import (
    bootstrap as parse_bootstrap,
)
from cortex_parse import (
    build_parse_service,
    prepare_crawl4ai_playwright_runtime,
)
from cortex_parse import (
    playwright_runtime as playwright_runtime_module,
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

    service = build_parse_service(ParseSettings(), load_runtime_config(config_path))
    engines = service._router.list_engines().engines

    assert [engine.engine_key for engine in engines] == ["markitdown"]


def test_crawl4ai_runtime_skips_missing_optional_storage_state() -> None:
    case_dir = _case_dir("unit-runtime-config-crawl4ai-missing-storage-state")
    config_path = case_dir / "cortex.runtime.yaml"
    config_path.write_text(
        "\n".join(
            [
                "schema_version: cortex.runtime.v1",
                "parse:",
                "  engines:",
                "    crawl4ai:",
                "      enabled: true",
                "      storage_state_ref: path:./secrets/storage_state.json",
            ]
        ),
        encoding="utf-8",
    )

    config = parse_bootstrap._crawl4ai_config(load_runtime_config(config_path))

    assert "storage_state" not in config["browser_config"]


def test_crawl4ai_runtime_uses_existing_storage_state_file() -> None:
    case_dir = _case_dir("unit-runtime-config-crawl4ai-existing-storage-state")
    storage_state = case_dir / "secrets" / "storage_state.json"
    storage_state.parent.mkdir(parents=True, exist_ok=True)
    storage_state.write_text('{"cookies":[],"origins":[]}', encoding="utf-8")
    config_path = case_dir / "cortex.runtime.yaml"
    config_path.write_text(
        "\n".join(
            [
                "schema_version: cortex.runtime.v1",
                "parse:",
                "  engines:",
                "    crawl4ai:",
                "      enabled: true",
                "      storage_state_ref: path:./secrets/storage_state.json",
            ]
        ),
        encoding="utf-8",
    )

    config = parse_bootstrap._crawl4ai_config(load_runtime_config(config_path))

    assert config["browser_config"]["storage_state"] == str(storage_state.resolve())


def test_prepare_crawl4ai_playwright_runtime_exports_configured_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_dir = _case_dir("unit-runtime-config-crawl4ai-playwright")
    config_path = case_dir / "cortex.runtime.yaml"
    config_path.write_text(
        "\n".join(
            [
                "schema_version: cortex.runtime.v1",
                "parse:",
                "  engines:",
                "    crawl4ai:",
                "      enabled: true",
                "      base_directory_ref: path:./crawl4ai-state",
                "      playwright_browsers_path_ref: path:./playwright-browsers",
                "      playwright_validate_on_startup: false",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("CRAWL4_AI_BASE_DIRECTORY", raising=False)
    monkeypatch.delenv("CRAWL4AI_BASE_DIRECTORY", raising=False)
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)

    runtime = prepare_crawl4ai_playwright_runtime(load_runtime_config(config_path), probe=False)

    expected_base = (case_dir / "crawl4ai-state").resolve()
    expected_browsers = (case_dir / "playwright-browsers").resolve()
    assert runtime.base_directory == expected_base
    assert runtime.browsers_path == expected_browsers
    assert Path(os.environ["CRAWL4_AI_BASE_DIRECTORY"]).resolve() == expected_base
    assert Path(os.environ["CRAWL4AI_BASE_DIRECTORY"]).resolve() == expected_base
    assert Path(os.environ["PLAYWRIGHT_BROWSERS_PATH"]).resolve() == expected_browsers
    assert expected_base.exists()
    assert expected_browsers.exists()


def test_prepare_crawl4ai_playwright_runtime_installs_and_retries_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_dir = _case_dir("unit-runtime-config-crawl4ai-playwright-retry")
    config_path = case_dir / "cortex.runtime.yaml"
    config_path.write_text(
        "\n".join(
            [
                "schema_version: cortex.runtime.v1",
                "parse:",
                "  engines:",
                "    crawl4ai:",
                "      enabled: true",
                "      playwright_validate_on_startup: true",
            ]
        ),
        encoding="utf-8",
    )
    events: list[str] = []
    attempts = {"count": 0}

    def _fake_probe(runtime) -> None:  # type: ignore[no-untyped-def]
        events.append(f"probe:{runtime.browser_name}")
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise ConfigError("missing browser")

    def _fake_install(runtime, *, python_executable=None, with_deps=False) -> None:  # type: ignore[no-untyped-def]
        del runtime, python_executable
        events.append(f"install:{with_deps}")

    monkeypatch.setattr(playwright_runtime_module, "probe_playwright_browser", _fake_probe)
    monkeypatch.setattr(playwright_runtime_module, "install_playwright_browser", _fake_install)

    runtime = prepare_crawl4ai_playwright_runtime(
        load_runtime_config(config_path),
        install_if_missing=True,
        probe=True,
    )

    assert runtime.enabled is True
    assert events == ["probe:chromium", "install:False", "probe:chromium"]


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
