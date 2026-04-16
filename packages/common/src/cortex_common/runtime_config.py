"""Unified runtime configuration models and loader."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .exceptions import ConfigError


class RuntimeConfigSettings(BaseSettings):
    """Location of the unified runtime configuration file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    path: str = Field(
        default="configs/cortex.runtime.local.yaml",
        alias="CORTEX_RUNTIME_CONFIG_PATH",
    )


class _RuntimeModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Crawl4AIRuntimeConfig(_RuntimeModel):
    enabled: bool = True
    browser_config: dict[str, Any] = Field(default_factory=dict)
    crawler_run_config: dict[str, Any] = Field(default_factory=dict)
    base_directory_ref: str | None = None
    proxy_ref: str | None = None
    storage_state_ref: str | None = None


class JinaReaderRuntimeConfig(_RuntimeModel):
    enabled: bool = True
    base_url: str = "https://r.jina.ai"
    timeout_seconds: float = 45.0
    use_readerlm_v2: bool = False
    headers: dict[str, str] = Field(default_factory=dict)
    api_key_ref: str | None = None


class LlamaParseRuntimeConfig(_RuntimeModel):
    enabled: bool = False
    mode: str = "cloud_api"
    options: dict[str, Any] = Field(default_factory=dict)
    api_key_ref: str | None = None


class MarkItDownRuntimeConfig(_RuntimeModel):
    enabled: bool = True
    options: dict[str, Any] = Field(default_factory=dict)


class DoclingRuntimeConfig(_RuntimeModel):
    enabled: bool = True
    converter_options: dict[str, Any] = Field(default_factory=dict)
    convert_options: dict[str, Any] = Field(default_factory=dict)


class ParseEngineRuntimeCatalog(_RuntimeModel):
    crawl4ai: Crawl4AIRuntimeConfig = Field(default_factory=Crawl4AIRuntimeConfig)
    jina_reader: JinaReaderRuntimeConfig = Field(default_factory=JinaReaderRuntimeConfig)
    llama_parse: LlamaParseRuntimeConfig = Field(default_factory=LlamaParseRuntimeConfig)
    markitdown: MarkItDownRuntimeConfig = Field(default_factory=MarkItDownRuntimeConfig)
    docling: DoclingRuntimeConfig = Field(default_factory=DoclingRuntimeConfig)


class ParseRuntimeConfig(_RuntimeModel):
    default_profile_ref: str = "auto_default"
    engines: ParseEngineRuntimeCatalog = Field(default_factory=ParseEngineRuntimeCatalog)


class CogneeRuntimeConfig(_RuntimeModel):
    enabled: bool = False
    monitoring_tool: str | None = None
    system_root_directory: str | None = None
    data_root_directory: str | None = None
    llm: dict[str, Any] = Field(default_factory=dict)
    embedding: dict[str, Any] = Field(default_factory=dict)
    vector_db: dict[str, Any] = Field(default_factory=dict)
    graph_db: dict[str, Any] = Field(default_factory=dict)
    relational_db: dict[str, Any] = Field(default_factory=dict)
    migration_db: dict[str, Any] = Field(default_factory=dict)
    chunking: dict[str, Any] = Field(default_factory=dict)


class KnowledgeRuntimeConfig(_RuntimeModel):
    provider: str = "cognee"
    cognee: CogneeRuntimeConfig = Field(default_factory=CogneeRuntimeConfig)


class CortexRuntimeConfig(_RuntimeModel):
    schema_version: str = "cortex.runtime.v1"
    parse: ParseRuntimeConfig = Field(default_factory=ParseRuntimeConfig)
    knowledge: KnowledgeRuntimeConfig = Field(default_factory=KnowledgeRuntimeConfig)

    @model_validator(mode="after")
    def _validate_schema_version(self) -> CortexRuntimeConfig:
        if self.schema_version != "cortex.runtime.v1":
            raise ValueError(
                "Unsupported runtime config schema version. Expected `cortex.runtime.v1`."
            )
        return self


@dataclass(frozen=True, slots=True)
class LoadedRuntimeConfig:
    """Loaded runtime config plus helpers for resolving references."""

    config: CortexRuntimeConfig
    source_path: Path
    env_values: dict[str, str] = field(repr=False)

    def resolve_reference(self, reference: str | None) -> str | None:
        if reference is None:
            return None
        text = reference.strip()
        if not text:
            return None
        if text.startswith(("http://", "https://")):
            return text
        if ":" not in text:
            return text
        scheme, raw_value = text.split(":", 1)
        value = raw_value.strip()
        if not value:
            return None
        if scheme == "env":
            resolved = os.getenv(value)
            if isinstance(resolved, str) and resolved.strip():
                return resolved.strip()
            fallback = self.env_values.get(value)
            return fallback.strip() if isinstance(fallback, str) and fallback.strip() else None
        if scheme == "file":
            path = self.resolve_path(value)
            if path is None or not path.exists():
                return None
            return path.read_text(encoding="utf-8").strip()
        if scheme == "path":
            path = self.resolve_path(value)
            return str(path) if path is not None else None
        if scheme == "literal":
            return value
        return text

    def resolve_path(self, path_value: str | None) -> Path | None:
        if path_value is None:
            return None
        text = path_value.strip()
        if not text:
            return None
        path = Path(text)
        if not path.is_absolute():
            path = (self.source_path.parent / path).resolve()
        return path

    def resolve_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return self.resolve_mapping(value)
        if isinstance(value, list):
            return [self.resolve_value(item) for item in value]
        return value

    def resolve_mapping(self, mapping: dict[str, Any]) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        deferred_refs: dict[str, str | None] = {}
        for key, value in mapping.items():
            text_key = str(key)
            if text_key.endswith("_ref") and isinstance(value, str):
                deferred_refs[text_key[: -len("_ref")]] = self.resolve_reference(value)
                continue
            resolved[text_key] = self.resolve_value(value)
        resolved.update(deferred_refs)
        return resolved


def load_runtime_config(
    path: str | Path = "configs/cortex.runtime.local.yaml",
) -> LoadedRuntimeConfig:
    """Load and cache the unified runtime config."""
    return _load_runtime_config_cached(str(path))


@lru_cache(maxsize=4)
def _load_runtime_config_cached(path: str) -> LoadedRuntimeConfig:
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = (Path.cwd() / config_path).resolve()
    if not config_path.exists():
        raise ConfigError(f"Runtime config `{config_path}` was not found.")
    with config_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ConfigError("Runtime config must load to a mapping.")
    return LoadedRuntimeConfig(
        config=CortexRuntimeConfig.model_validate(payload),
        source_path=config_path,
        env_values=_load_dotenv_values(Path.cwd() / ".env"),
    )


def _load_dotenv_values(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        env_key = key.strip()
        if not env_key:
            continue
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[env_key] = value
    return values
