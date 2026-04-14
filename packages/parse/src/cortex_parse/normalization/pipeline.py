"""Markdown, metadata, provenance, and chunk normalization."""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from cortex_common import new_prefixed_id, utc_now
from cortex_contracts import (
    AppliedParseEngine,
    AuditFields,
    ChunkingOptions,
    ChunkingStrategy,
    DocumentProvenance,
    ParsedDocument,
    ParseDiagnostics,
    ParseEngineAttempt,
    ParseResult,
    ParseSyncRequest,
    ParseTimingSummary,
    StandardMetadata,
    TelemetryContext,
)
from cortex_observability import MetricsFacade, get_trace_context
from opentelemetry import trace

from ..models import EngineExecutionResult, LoadedParserProfile, NormalizedChunk

_MULTI_BLANK_LINES = re.compile(r"\n{3,}")


@dataclass(slots=True)
class NormalizationResult:
    result: ParseResult
    chunks: list[NormalizedChunk] = field(default_factory=list)


class ParseNormalizationPipeline:
    """Convert engine output into the canonical parse result shape."""

    def __init__(self) -> None:
        self._tracer = trace.get_tracer("cortex.parse.normalization")
        self._metrics = MetricsFacade("cortex.parse")

    def normalize(
        self,
        *,
        request: ParseSyncRequest,
        execution: EngineExecutionResult,
        selected_engine,
        profile: LoadedParserProfile | None,
        attempts: list[ParseEngineAttempt],
        fallback_used: bool,
        started_at: datetime,
        created_by: str | None,
    ) -> NormalizationResult:
        timer_started = time.perf_counter()
        with self._tracer.start_as_current_span("parse.normalize.markdown") as span:
            markdown = self._normalize_markdown(execution.markdown, request)
            now = utc_now()
            markdown_sha256 = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
            normalized_metadata = self._standard_metadata(execution, request)
            telemetry = TelemetryContext(**get_trace_context())
            timings = dict(execution.timings_ms)
            timings["normalize"] = int((time.perf_counter() - timer_started) * 1000)
            if "total" not in timings:
                fetch = timings.get("fetch", 0)
                render = timings.get("render", 0)
                timings["total"] = fetch + render + timings["normalize"]

            document = ParsedDocument(
                document_id=new_prefixed_id("doc"),
                source_type=request.source.input_kind,
                source_format=execution.source_format,
                markdown=markdown,
                audit=AuditFields(
                    created_at=now,
                    updated_at=now,
                    created_by=created_by,
                ),
                source_url=request.source.url,
                source_object_id=request.source.object_id,
                source_uri=request.source.uri or request.source.url,
                canonical_url=(
                    execution.final_url
                    or request.source.canonical_url
                    or request.source.url
                ),
                title=self._resolve_title(execution, markdown, request),
                language_code=self._resolve_language(execution, request),
                detected_mime_type=execution.detected_mime_type,
                category_tags=self._string_list(execution.metadata.get("category_tags")),
                labels=self._string_list(execution.metadata.get("labels")),
                access_policy=request.persistence.access_policy,
                markdown_sha256=markdown_sha256,
                normalized_metadata=normalized_metadata,
                metadata=self._document_metadata(execution, request),
                parser=AppliedParseEngine(
                    engine_key=selected_engine.engine_key,
                    display_name=selected_engine.display_name,
                    engine_family=selected_engine.engine_family,
                    engine_version=execution.parser_version,
                    profile_ref=profile.descriptor.profile_ref if profile else None,
                    template_ref=request.parser.engine_template_ref,
                    fallback_used=fallback_used,
                ),
                provenance=DocumentProvenance(
                    input_kind=request.source.input_kind,
                    fetched_at=execution.fetched_at or started_at,
                    final_url=execution.final_url or request.source.url or request.source.uri,
                    http_status=execution.http_status,
                    content_length_bytes=execution.content_length_bytes,
                    parser_version=execution.parser_version,
                    content_hash_sha256=execution.content_hash_sha256 or markdown_sha256,
                ),
            )
            diagnostics = ParseDiagnostics(
                selected_engine_key=selected_engine.engine_key,
                fallback_used=fallback_used,
                engine_attempts=attempts,
                warnings=list(execution.warnings),
                link_counts=dict(execution.link_counts),
                media_counts=dict(execution.media_counts),
                anti_bot_strategy=execution.anti_bot_strategy,
                used_proxy=execution.used_proxy,
                timings_ms=ParseTimingSummary(**timings),
                telemetry=telemetry,
            )
            chunks = self._chunk_markdown(markdown, request.output.chunking)
            span.set_attribute("cortex.parse.engine", selected_engine.engine_key)
            span.set_attribute("cortex.parse.chunk_count", len(chunks))
            self._metrics.counter(
                "cortex.parse.requests",
                description="Count of normalized parse requests.",
            ).add(1, {"cortex.parse.engine": selected_engine.engine_key})
            self._metrics.histogram(
                "cortex.parse.duration",
                unit="ms",
                description="End-to-end parse duration in milliseconds.",
            ).record(
                float(timings.get("total", 0)),
                {"cortex.parse.engine": selected_engine.engine_key},
            )
            return NormalizationResult(
                result=ParseResult(
                    document=document,
                    artifacts=execution.artifacts,
                    diagnostics=diagnostics,
                    telemetry=telemetry,
                ),
                chunks=chunks,
            )

    @staticmethod
    def _normalize_markdown(markdown: str, request: ParseSyncRequest) -> str:
        normalized = markdown.replace("\r\n", "\n").strip()
        if request.normalization.deduplicate_whitespace:
            normalized = _MULTI_BLANK_LINES.sub("\n\n", normalized)
        if not request.normalization.preserve_source_blocks:
            normalized = "\n".join(line.rstrip() for line in normalized.splitlines())
        return normalized.strip()

    def _standard_metadata(
        self,
        execution: EngineExecutionResult,
        request: ParseSyncRequest,
    ) -> StandardMetadata:
        metadata = execution.metadata
        publish_date = metadata.get("publish_date")
        parsed_publish_date = publish_date if isinstance(publish_date, datetime) else None
        return StandardMetadata(
            title=self._resolve_title(execution, execution.markdown, request),
            author=self._string_value(metadata.get("author")),
            publish_date=parsed_publish_date,
            language=self._resolve_language(execution, request),
            description=self._string_value(metadata.get("description")),
            summary=self._string_value(metadata.get("summary")),
            keywords=self._string_list(metadata.get("keywords")),
            category_tags=self._string_list(metadata.get("category_tags")),
        )

    def _resolve_title(
        self,
        execution: EngineExecutionResult,
        markdown: str,
        request: ParseSyncRequest,
    ) -> str | None:
        if execution.title:
            return execution.title
        if request.normalization.infer_title:
            title = self._string_value(execution.metadata.get("title"))
            if title:
                return title
            for line in markdown.splitlines():
                stripped = line.strip()
                if stripped.startswith("#"):
                    return stripped.lstrip("#").strip() or None
        return None

    @staticmethod
    def _resolve_language(
        execution: EngineExecutionResult,
        request: ParseSyncRequest,
    ) -> str | None:
        if "language" in execution.metadata:
            return ParseNormalizationPipeline._string_value(execution.metadata.get("language"))
        if "language_code" in execution.metadata:
            return ParseNormalizationPipeline._string_value(execution.metadata.get("language_code"))
        if request.normalization.infer_language:
            return "und"
        return None

    @staticmethod
    def _document_metadata(
        execution: EngineExecutionResult,
        request: ParseSyncRequest,
    ) -> dict[str, Any]:
        metadata = dict(execution.metadata)
        if request.normalization.include_page_metadata and execution.raw_metadata:
            metadata.setdefault("raw_metadata", dict(execution.raw_metadata))
        if request.output.return_engine_payload_summary and execution.engine_payload_summary:
            metadata.setdefault("engine_payload_summary", dict(execution.engine_payload_summary))
        return metadata

    def _chunk_markdown(self, markdown: str, options: ChunkingOptions) -> list[NormalizedChunk]:
        if not options.enabled or options.strategy is ChunkingStrategy.NONE or not markdown:
            return []
        if options.strategy is ChunkingStrategy.HEADING:
            chunks = self._heading_chunks(markdown)
            if chunks:
                return chunks[: options.max_chunks]
        return self._token_chunks(markdown, options)

    def _heading_chunks(self, markdown: str) -> list[NormalizedChunk]:
        chunks: list[NormalizedChunk] = []
        current_heading: str | None = None
        current_lines: list[str] = []
        for line in markdown.splitlines():
            if line.lstrip().startswith("#"):
                if current_lines:
                    chunks.append(self._build_chunk(len(chunks), current_lines, current_heading))
                    current_lines = []
                current_heading = line.lstrip("#").strip() or current_heading
            current_lines.append(line)
        if current_lines:
            chunks.append(self._build_chunk(len(chunks), current_lines, current_heading))
        return [chunk for chunk in chunks if chunk.text]

    def _token_chunks(self, markdown: str, options: ChunkingOptions) -> list[NormalizedChunk]:
        paragraphs = [
            paragraph.strip() for paragraph in markdown.split("\n\n") if paragraph.strip()
        ]
        chunks: list[NormalizedChunk] = []
        current: list[str] = []
        current_tokens = 0
        for paragraph in paragraphs:
            paragraph_tokens = self._token_count(paragraph)
            if current and current_tokens + paragraph_tokens > options.target_tokens:
                chunks.append(self._build_chunk(len(chunks), current, None))
                if len(chunks) >= options.max_chunks:
                    return chunks
                current = []
                current_tokens = 0
            current.append(paragraph)
            current_tokens += paragraph_tokens
        if current and len(chunks) < options.max_chunks:
            chunks.append(self._build_chunk(len(chunks), current, None))
        return chunks

    def _build_chunk(
        self,
        chunk_index: int,
        lines: list[str],
        heading_path: str | None,
    ) -> NormalizedChunk:
        text = "\n\n".join(line.strip() for line in lines if line.strip())
        return NormalizedChunk(
            chunk_index=chunk_index,
            text=text,
            heading_path=heading_path,
            token_count=self._token_count(text),
            char_count=len(text),
            metadata={"heading_path": heading_path} if heading_path else {},
        )

    @staticmethod
    def _token_count(text: str) -> int:
        return len([token for token in re.split(r"\s+", text.strip()) if token])

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item).strip()]

    @staticmethod
    def _string_value(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
