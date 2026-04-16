"""Compile the simplified public Parse API into the internal execution contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cortex_common import ValidationError
from cortex_contracts import (
    BrowserProfile,
    CaptureOptions,
    ChunkingOptions,
    ChunkingStrategy,
    CrawlOptions,
    FallbackMode,
    FallbackOnError,
    FallbackPolicy,
    ParseEngineDescriptor,
    ParseEngineList,
    ParseInputKind,
    ParseJobRequest,
    ParseJobSubmitRequest,
    ParseLlmReadyMode,
    ParseNormalizationOptions,
    ParseOutputOptions,
    ParsePersistenceOptions,
    ParserSelection,
    ParseSource,
    ParseSourceInput,
    ParseSubmitRequest,
    ParseSyncRequest,
)


@dataclass(frozen=True, slots=True)
class ParseScenePreset:
    engine_key: str
    scene_id: str
    profile_ref: str
    description: str
    source_kinds: tuple[ParseInputKind, ...]
    timeout_seconds: int = 45
    crawl: dict[str, Any] = field(default_factory=dict)
    normalization: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    persistence: dict[str, Any] = field(default_factory=dict)


def _default_browser_profile() -> dict[str, Any]:
    return BrowserProfile(
        browser_type="chromium",
        headless=True,
        viewport_width=1280,
        viewport_height=900,
    ).model_dump(mode="json")


def _default_capture_options() -> dict[str, Any]:
    return CaptureOptions().model_dump(mode="json")


def _default_crawl_options() -> dict[str, Any]:
    return CrawlOptions(
        respect_robots_txt=True,
        browser_profile=BrowserProfile(),
        remove_overlay_elements=True,
        cache_mode="bypass",
        timeout_ms=60_000,
        capture=CaptureOptions(),
    ).model_dump(mode="json")


def _default_normalization_options() -> dict[str, Any]:
    return ParseNormalizationOptions().model_dump(mode="json")


def _default_output_options() -> dict[str, Any]:
    return ParseOutputOptions(
        llm_ready_mode=ParseLlmReadyMode.MARKDOWN,
        metadata_fields=["title", "language", "summary", "category_tags"],
        return_engine_payload_summary=True,
        chunking=ChunkingOptions(
            enabled=True,
            strategy=ChunkingStrategy.SEMANTIC,
            target_tokens=512,
            overlap_tokens=64,
            max_chunks=256,
        ),
    ).model_dump(mode="json")


def _document_output_options() -> dict[str, Any]:
    return ParseOutputOptions(
        llm_ready_mode=ParseLlmReadyMode.FIT_MARKDOWN,
        metadata_fields=["title", "author", "publish_date", "keywords"],
        return_engine_payload_summary=True,
        chunking=ChunkingOptions(
            enabled=True,
            strategy=ChunkingStrategy.HEADING,
            target_tokens=768,
            overlap_tokens=96,
            max_chunks=512,
        ),
    ).model_dump(mode="json")


def _default_persistence_options() -> dict[str, Any]:
    return ParsePersistenceOptions().model_dump(mode="json")


DEFAULT_FALLBACK_POLICY = FallbackPolicy(
    enabled=False,
    mode=FallbackMode.NONE,
    on_error=FallbackOnError.FAIL_FAST,
    max_engine_attempts=1,
)


PRESETS: tuple[ParseScenePreset, ...] = (
    ParseScenePreset(
        engine_key="crawl4ai",
        scene_id="balanced",
        profile_ref="crawl4ai_balanced",
        description="Balanced interactive web parsing for most public pages.",
        source_kinds=(ParseInputKind.URL, ParseInputKind.URI, ParseInputKind.OBJECT),
        timeout_seconds=45,
        crawl={
            **_default_crawl_options(),
            "browser_profile": {
                **_default_browser_profile(),
                "enable_stealth": False,
                "use_undetected_browser": False,
                "use_persistent_context": False,
            },
            "capture": {
                **_default_capture_options(),
                "capture_pdf": False,
                "capture_screenshot": False,
                "fetch_ssl_certificate": False,
                "capture_network_log": False,
                "capture_console_log": False,
                "scan_full_page": False,
                "flatten_shadow_dom": False,
            },
        },
        normalization=_default_normalization_options(),
        output=_default_output_options(),
        persistence=_default_persistence_options(),
    ),
    ParseScenePreset(
        engine_key="crawl4ai",
        scene_id="deep_web",
        profile_ref="crawl4ai_deep_web",
        description=(
            "High-intensity Crawl4AI preset with artifacts, full-page scan, "
            "and diagnostics."
        ),
        source_kinds=(ParseInputKind.URL, ParseInputKind.URI, ParseInputKind.OBJECT),
        timeout_seconds=90,
        crawl={
            **_default_crawl_options(),
            "browser_profile": {
                **_default_browser_profile(),
                "enable_stealth": True,
                "use_undetected_browser": True,
                "use_persistent_context": True,
            },
            "timeout_ms": 120_000,
            "capture": {
                **_default_capture_options(),
                "capture_pdf": True,
                "capture_screenshot": True,
                "fetch_ssl_certificate": True,
                "capture_network_log": True,
                "capture_console_log": True,
                "scan_full_page": True,
                "flatten_shadow_dom": True,
            },
        },
        normalization=_default_normalization_options(),
        output=_default_output_options(),
        persistence=_default_persistence_options(),
    ),
    ParseScenePreset(
        engine_key="crawl4ai",
        scene_id="authenticated_web",
        profile_ref="crawl4ai_authenticated_web",
        description="Interactive Crawl4AI preset optimized for authenticated or stateful pages.",
        source_kinds=(ParseInputKind.URL, ParseInputKind.URI, ParseInputKind.OBJECT),
        timeout_seconds=90,
        crawl={
            **_default_crawl_options(),
            "browser_profile": {
                **_default_browser_profile(),
                "enable_stealth": True,
                "use_undetected_browser": True,
                "use_persistent_context": True,
            },
            "timeout_ms": 120_000,
            "capture": {
                **_default_capture_options(),
                "capture_pdf": False,
                "capture_screenshot": True,
                "fetch_ssl_certificate": True,
                "capture_network_log": True,
                "capture_console_log": True,
                "scan_full_page": True,
                "flatten_shadow_dom": True,
            },
        },
        normalization=_default_normalization_options(),
        output=_default_output_options(),
        persistence=_default_persistence_options(),
    ),
    ParseScenePreset(
        engine_key="jina_reader",
        scene_id="balanced",
        profile_ref="jina_reader_balanced",
        description="Balanced Jina Reader mode with ReaderLM-v2 enabled when configured.",
        source_kinds=(ParseInputKind.URL, ParseInputKind.URI, ParseInputKind.OBJECT),
        timeout_seconds=30,
        normalization=_default_normalization_options(),
        output=_default_output_options(),
        persistence=_default_persistence_options(),
    ),
    ParseScenePreset(
        engine_key="jina_reader",
        scene_id="fast_extract",
        profile_ref="jina_reader_fast_extract",
        description="Low-latency Jina Reader mode without extra high-cost response shaping.",
        source_kinds=(ParseInputKind.URL, ParseInputKind.URI, ParseInputKind.OBJECT),
        timeout_seconds=20,
        normalization=_default_normalization_options(),
        output=_default_output_options(),
        persistence=_default_persistence_options(),
    ),
    ParseScenePreset(
        engine_key="llama_parse",
        scene_id="document_fidelity",
        profile_ref="llama_parse_document_fidelity",
        description="High-fidelity cloud document parsing for PDFs and office formats.",
        source_kinds=(ParseInputKind.URL, ParseInputKind.URI, ParseInputKind.OBJECT),
        timeout_seconds=90,
        normalization=_default_normalization_options(),
        output=_document_output_options(),
        persistence=_default_persistence_options(),
    ),
    ParseScenePreset(
        engine_key="markitdown",
        scene_id="lightweight",
        profile_ref="markitdown_lightweight",
        description="Lightweight local conversion for text-like documents.",
        source_kinds=(ParseInputKind.URL, ParseInputKind.URI, ParseInputKind.OBJECT),
        timeout_seconds=30,
        normalization=_default_normalization_options(),
        output=_document_output_options(),
        persistence=_default_persistence_options(),
    ),
    ParseScenePreset(
        engine_key="docling",
        scene_id="document_ai",
        profile_ref="docling_document_ai",
        description="Structured local document conversion with OCR- and layout-friendly defaults.",
        source_kinds=(ParseInputKind.URL, ParseInputKind.URI, ParseInputKind.OBJECT),
        timeout_seconds=90,
        normalization=_default_normalization_options(),
        output=_document_output_options(),
        persistence=_default_persistence_options(),
    ),
)


DEFAULT_SCENE_BY_ENGINE: dict[str, str] = {
    "crawl4ai": "balanced",
    "jina_reader": "balanced",
    "llama_parse": "document_fidelity",
    "markitdown": "lightweight",
    "docling": "document_ai",
}


class ParseRequestCompiler:
    """Compile the simplified public Parse request into the internal execution contract."""

    def __init__(
        self,
        available_engine_keys: set[str] | None = None,
        *,
        presets: tuple[ParseScenePreset, ...] | None = None,
        default_scene_by_engine: dict[str, str] | None = None,
    ) -> None:
        self._available_engine_keys = set(available_engine_keys or set())
        self._preset_values = presets or PRESETS
        self._default_scene_by_engine = default_scene_by_engine or DEFAULT_SCENE_BY_ENGINE
        self._presets = {
            (preset.engine_key, preset.scene_id): preset
            for preset in self._preset_values
        }

    def describe_engines(self, descriptors: ParseEngineList) -> ParseEngineList:
        annotated: list[ParseEngineDescriptor] = []
        for descriptor in descriptors.engines:
            scenes = [
                preset.scene_id
                for preset in self._preset_values
                if preset.engine_key == descriptor.engine_key
            ]
            annotated.append(
                descriptor.model_copy(
                    update={
                        "default_scene_id": self._default_scene_by_engine.get(
                            descriptor.engine_key
                        ),
                        "supported_scene_ids": scenes,
                        "default_profile_ref": self._default_profile_ref(descriptor.engine_key),
                    }
                )
            )
        return ParseEngineList(engines=annotated)

    def compile_sync(
        self,
        request: ParseSubmitRequest,
        *,
        resolved_source: ParseSource | None = None,
    ) -> ParseSyncRequest:
        source = self._compile_source(request.source, resolved_source=resolved_source)
        preset = self._preset_for(
            engine_key=request.engine_id,
            scene_id=request.scene,
            source=source,
        )
        return ParseSyncRequest(
            source=source,
            parser=ParserSelection(
                profile_ref=preset.profile_ref,
                preferred_engine_key=request.engine_id,
                allowed_engines=[request.engine_id],
                fallback_policy=DEFAULT_FALLBACK_POLICY,
            ),
            crawl=CrawlOptions.model_validate(preset.crawl or _default_crawl_options()),
            normalization=ParseNormalizationOptions.model_validate(
                preset.normalization or _default_normalization_options()
            ),
            output=ParseOutputOptions.model_validate(preset.output or _default_output_options()),
            persistence=ParsePersistenceOptions.model_validate(
                preset.persistence or _default_persistence_options()
            ),
            timeout_seconds=preset.timeout_seconds,
        )

    def compile_job(
        self,
        request: ParseJobSubmitRequest,
        *,
        resolved_source: ParseSource | None = None,
    ) -> ParseJobRequest:
        sync_request = self.compile_sync(
            ParseSubmitRequest(
                source=request.source,
                engine_id=request.engine_id,
                scene=request.scene,
            ),
            resolved_source=resolved_source,
        )
        return ParseJobRequest(
            **sync_request.model_dump(mode="json"),
            priority=request.priority,
            webhook=request.webhook,
        )

    def _compile_source(
        self,
        source: ParseSourceInput,
        *,
        resolved_source: ParseSource | None = None,
    ) -> ParseSource:
        if resolved_source is not None:
            return resolved_source.model_copy(
                update={
                    "filename": source.filename or resolved_source.filename,
                    "canonical_url": source.canonical_url or resolved_source.canonical_url,
                    "expected_content_type": source.mime_type
                    or resolved_source.expected_content_type,
                }
            )

        kind = source.kind or self._infer_kind(source)
        if kind is ParseInputKind.OBJECT:
            raise ValidationError(
                "Object-backed public Parse requests must be resolved to an "
                "engine-accessible source first."
            )
        if source.uri is None:
            raise ValidationError("`source.uri` is required for non-object Parse requests.")
        if kind is ParseInputKind.URL:
            return ParseSource(
                input_kind=ParseInputKind.URL,
                url=source.uri,
                filename=source.filename,
                canonical_url=source.canonical_url,
                expected_content_type=source.mime_type,
            )
        return ParseSource(
            input_kind=kind,
            uri=source.uri,
            filename=source.filename,
            canonical_url=source.canonical_url,
            expected_content_type=source.mime_type,
        )

    @staticmethod
    def _infer_kind(source: ParseSourceInput) -> ParseInputKind:
        if source.object_id:
            return ParseInputKind.OBJECT
        if source.uri and source.uri.startswith(("http://", "https://")):
            return ParseInputKind.URL
        return ParseInputKind.URI

    def _preset_for(
        self,
        *,
        engine_key: str,
        scene_id: str | None,
        source: ParseSource,
    ) -> ParseScenePreset:
        if self._available_engine_keys and engine_key not in self._available_engine_keys:
            raise ValidationError(f"Parse engine `{engine_key}` is not currently available.")
        effective_scene = scene_id or self._default_scene_by_engine.get(engine_key)
        if effective_scene is None:
            raise ValidationError(f"Parse engine `{engine_key}` does not expose a default scene.")
        preset = self._presets.get((engine_key, effective_scene))
        if preset is None:
            supported = sorted(
                scene.scene_id for scene in self._preset_values if scene.engine_key == engine_key
            )
            raise ValidationError(
                f"Parse scene `{effective_scene}` is not supported for engine `{engine_key}`. "
                f"Supported scenes: {', '.join(supported) or 'none'}."
            )
        if source.input_kind not in preset.source_kinds:
            raise ValidationError(
                f"Parse scene `{effective_scene}` on engine `{engine_key}` does not support "
                f"source kind `{source.input_kind.value}`."
            )
        return preset

    def _default_profile_ref(self, engine_key: str) -> str | None:
        default_scene = self._default_scene_by_engine.get(engine_key)
        if default_scene is None:
            return None
        preset = self._presets.get((engine_key, default_scene))
        return preset.profile_ref if preset is not None else None
