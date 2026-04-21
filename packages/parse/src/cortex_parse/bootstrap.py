"""Runtime bootstrap helpers for parse orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cortex_common import LoadedRuntimeConfig, ParseSettings, load_runtime_config
from cortex_contracts import ParseEngineStatus

from .adapters import (
    Crawl4AIParseEngine,
    DoclingParseEngine,
    JinaReaderParseEngine,
    LlamaParseEngine,
    MarkItDownParseEngine,
)
from .playwright_runtime import prepare_crawl4ai_playwright_runtime
from .profile_loader import ParseProfileLoader
from .registry import ParseEngineRegistry
from .service import ParseService


def build_parse_service(
    settings: ParseSettings,
    runtime_config: LoadedRuntimeConfig | None = None,
) -> ParseService:
    """Build the default parse runtime for the API process."""
    loaded_runtime = runtime_config or load_runtime_config()
    prepare_crawl4ai_playwright_runtime(loaded_runtime, probe=False)
    parse_runtime = loaded_runtime.config.parse
    registry = ParseEngineRegistry()
    for engine in (
        Crawl4AIParseEngine(_crawl4ai_config(loaded_runtime)),
        JinaReaderParseEngine(_jina_reader_config(loaded_runtime)),
        LlamaParseEngine(_llama_parse_config(loaded_runtime)),
        MarkItDownParseEngine(_markitdown_config(loaded_runtime)),
        DoclingParseEngine(_docling_config(loaded_runtime)),
    ):
        if engine.descriptor.status is ParseEngineStatus.ACTIVE:
            registry.register(engine)

    return ParseService(
        registry=registry,
        profile_loader=ParseProfileLoader(),
        default_profile_ref=settings.default_profile or parse_runtime.default_profile_ref,
    )


def _crawl4ai_config(runtime_config: LoadedRuntimeConfig) -> dict[str, Any]:
    config = runtime_config.config.parse.engines.crawl4ai
    browser_config = dict(config.browser_config)
    base_directory = runtime_config.resolve_reference(config.base_directory_ref)
    proxy = runtime_config.resolve_reference(config.proxy_ref)
    if proxy and "proxy" not in browser_config:
        browser_config["proxy"] = proxy
    storage_state = _resolve_existing_storage_state(runtime_config, config.storage_state_ref)
    if storage_state and "storage_state" not in browser_config:
        browser_config["storage_state"] = storage_state
    return {
        "enabled": config.enabled,
        "base_directory": base_directory,
        "playwright_browsers_path": runtime_config.resolve_reference(
            config.playwright_browsers_path_ref
        ),
        "playwright_browser": config.playwright_browser,
        "browser_config": browser_config,
        "crawler_run_config": dict(config.crawler_run_config),
    }


def _resolve_existing_storage_state(
    runtime_config: LoadedRuntimeConfig,
    reference: str | None,
) -> str | None:
    storage_state = runtime_config.resolve_reference(reference)
    if not storage_state:
        return None

    storage_path = Path(storage_state)
    if not storage_path.is_absolute():
        storage_path = runtime_config.source_path.parent / storage_path
    if storage_path.exists():
        return str(storage_path.resolve())
    return None


def _jina_reader_config(runtime_config: LoadedRuntimeConfig) -> dict[str, Any]:
    config = runtime_config.config.parse.engines.jina_reader
    return {
        "enabled": config.enabled,
        "base_url": config.base_url,
        "timeout_seconds": config.timeout_seconds,
        "use_readerlm_v2": config.use_readerlm_v2,
        "headers": dict(config.headers),
        "api_key": runtime_config.resolve_reference(config.api_key_ref),
    }


def _llama_parse_config(runtime_config: LoadedRuntimeConfig) -> dict[str, Any]:
    config = runtime_config.config.parse.engines.llama_parse
    return {
        "enabled": config.enabled,
        "mode": config.mode,
        "llama_parse": dict(config.options),
        "api_key": runtime_config.resolve_reference(config.api_key_ref),
    }


def _markitdown_config(runtime_config: LoadedRuntimeConfig) -> dict[str, Any]:
    config = runtime_config.config.parse.engines.markitdown
    return {
        "enabled": config.enabled,
        "markitdown": dict(config.options),
    }


def _docling_config(runtime_config: LoadedRuntimeConfig) -> dict[str, Any]:
    config = runtime_config.config.parse.engines.docling
    return {
        "enabled": config.enabled,
        "docling": dict(config.converter_options),
        "docling_convert": dict(config.convert_options),
    }
