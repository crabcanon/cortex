"""Focused unit tests for parse profile loading and registry behavior."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from cortex_common import ConfigError
from cortex_contracts import (
    ParseEngineDeploymentMode,
    ParseEngineDescriptor,
    ParseEngineStatus,
)
from cortex_parse import EngineExecutionContext, EngineExecutionResult, ParseEngineProtocol
from cortex_parse.profile_loader import ParseProfileLoader
from cortex_parse.registry import ParseEngineRegistry


class _Engine(ParseEngineProtocol):
    def __init__(self, engine_key: str, status: ParseEngineStatus) -> None:
        self._descriptor = ParseEngineDescriptor(
            engine_key=engine_key,
            display_name=engine_key.title(),
            engine_family="test",
            deployment_mode=ParseEngineDeploymentMode.LOCAL,
            status=status,
            supported_source_types=["url"],
        )

    @property
    def descriptor(self) -> ParseEngineDescriptor:
        return self._descriptor

    async def execute(self, context: EngineExecutionContext) -> EngineExecutionResult:
        del context
        raise AssertionError("registry tests should not execute engines")


def _case_dir(name: str) -> Path:
    root = Path("runtime-test-data")
    root.mkdir(parents=True, exist_ok=True)
    case_dir = root / f"{name}-{time.time_ns()}"
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir


def test_parse_profile_loader_normalizes_optional_fields_and_list_order() -> None:
    tmp_path = _case_dir("unit-parse-profiles")
    (tmp_path / "beta.yaml").write_text(
        "\n".join(
            [
                "profile_ref: beta",
                "display_name: Beta Profile",
                "description: '  Beta profile  '",
                "preferred_engine_key: crawl4ai",
                "allowed_engines: [crawl4ai, jina_reader]",
                "source_constraints:",
                "  allow_domains: [example.com]",
                "engine_overrides:",
                "  jina_reader:",
                "    timeout_ms: 15000",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "alpha.yaml").write_text(
        "\n".join(
            [
                "profile_ref: alpha",
                "display_name: Alpha Profile",
            ]
        ),
        encoding="utf-8",
    )

    loader = ParseProfileLoader(tmp_path)
    loaded = loader.load("beta")
    listed = loader.list()

    assert loaded.descriptor.description == "Beta profile"
    assert loaded.descriptor.allowed_engines == ["crawl4ai", "jina_reader"]
    assert loaded.source_constraints == {"allow_domains": ["example.com"]}
    assert loaded.engine_overrides == {"jina_reader": {"timeout_ms": 15000}}
    assert [profile.profile_ref for profile in listed.profiles] == ["alpha", "beta"]


def test_parse_profile_loader_raises_for_missing_or_invalid_profiles() -> None:
    tmp_path = _case_dir("unit-parse-invalid")
    (tmp_path / "invalid.yaml").write_text("- not-a-mapping\n", encoding="utf-8")
    loader = ParseProfileLoader(tmp_path)

    with pytest.raises(ConfigError, match="was not found"):
        loader.load("missing")

    with pytest.raises(ConfigError, match="must load to a mapping"):
        loader.load("invalid")


def test_parse_engine_registry_filters_inactive_engines() -> None:
    registry = ParseEngineRegistry()
    registry.register(_Engine("crawl4ai", ParseEngineStatus.ACTIVE))
    registry.register(_Engine("docling", ParseEngineStatus.DISABLED))

    active = registry.list()
    all_engines = registry.list(include_inactive=True)

    assert [engine.engine_key for engine in active.engines] == ["crawl4ai"]
    assert [engine.engine_key for engine in all_engines.engines] == ["crawl4ai", "docling"]
