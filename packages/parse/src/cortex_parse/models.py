"""Internal parse orchestration models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from cortex_contracts import (
    FallbackPolicy,
    ParseArtifacts,
    ParseEngineDescriptor,
    ParseEngineList,
    ParserProfile,
    ParseSource,
    ParseSyncRequest,
)


@dataclass(slots=True)
class LoadedParserProfile:
    descriptor: ParserProfile
    source_constraints: dict[str, Any] = field(default_factory=dict)
    engine_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass(slots=True)
class EngineExecutionContext:
    request: ParseSyncRequest
    source: ParseSource
    profile: LoadedParserProfile | None = None
    engine_options: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EngineExecutionResult:
    markdown: str
    source_format: str
    detected_mime_type: str | None = None
    title: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    raw_metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    link_counts: dict[str, int] = field(default_factory=dict)
    media_counts: dict[str, int] = field(default_factory=dict)
    anti_bot_strategy: str | None = None
    used_proxy: bool | None = None
    timings_ms: dict[str, int] = field(default_factory=dict)
    fetched_at: datetime | None = None
    final_url: str | None = None
    http_status: int | None = None
    content_length_bytes: int | None = None
    parser_version: str | None = None
    content_hash_sha256: str | None = None
    artifacts: ParseArtifacts = field(default_factory=ParseArtifacts)
    engine_payload_summary: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RoutedParseEngine:
    descriptor: ParseEngineDescriptor
    engine: ParseEngineProtocol
    engine_options: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RouterSelection:
    profile: LoadedParserProfile | None
    engines: list[RoutedParseEngine]
    fallback_policy: FallbackPolicy
    fallback_used: bool = False


@dataclass(slots=True)
class NormalizedChunk:
    chunk_index: int
    text: str
    heading_path: str | None = None
    token_count: int = 0
    char_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class ParseEngineProtocol(Protocol):
    @property
    def descriptor(self) -> ParseEngineDescriptor: ...

    async def execute(self, context: EngineExecutionContext) -> EngineExecutionResult: ...


def engine_list(descriptors: list[ParseEngineDescriptor]) -> ParseEngineList:
    return ParseEngineList(engines=descriptors)
