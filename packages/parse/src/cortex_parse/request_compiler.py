"""Compile the public Parse API into the internal execution contract."""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urlparse

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

AUTO_ENGINE_ID = "auto"


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


@dataclass(frozen=True, slots=True)
class CompiledEngineSelection:
    engine_key: str
    scene_id: str | None
    allowed_engines: list[str] = field(default_factory=list)


DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".csv",
    ".png",
    ".jpg",
    ".jpeg",
    ".tiff",
    ".bmp",
    ".gif",
    ".webp",
}
TEXT_LIKE_EXTENSIONS = {
    ".md",
    ".markdown",
    ".txt",
    ".rst",
    ".json",
    ".xml",
    ".yaml",
    ".yml",
    ".html",
    ".htm",
    ".csv",
}


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


AUTO_FALLBACK_POLICY = FallbackPolicy(
    enabled=True,
    mode=FallbackMode.ORDERED,
    on_error=FallbackOnError.TRY_NEXT,
    max_engine_attempts=3,
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
            "High-intensity Crawl4AI preset with artifacts, full-page scan, and diagnostics."
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
        description="Interactive Crawl4AI preset optimized for authenticated pages.",
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
        description="Balanced Jina Reader mode with ReaderLM-v2 when configured.",
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
        description="Low-latency Jina Reader mode for lightweight extraction.",
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
        description="High-fidelity cloud document parsing for complex files.",
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
        description="Structured local document conversion with OCR-friendly defaults.",
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
    """Compile the public Parse request into the internal execution contract."""

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
            (preset.engine_key, preset.scene_id): preset for preset in self._preset_values
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
        source_input: ParseSourceInput,
        *,
        resolved_source: ParseSource | None = None,
    ) -> ParseSyncRequest:
        source = self._compile_source(source_input, resolved_source=resolved_source)
        selection = self._compile_engine_selection(request, source, source_input)
        preset = self._preset_for(
            engine_key=selection.engine_key,
            scene_id=selection.scene_id,
            source=source,
        )
        return ParseSyncRequest(
            source=source,
            parser=ParserSelection(
                profile_ref=preset.profile_ref,
                preferred_engine_key=selection.engine_key,
                allowed_engines=selection.allowed_engines or [selection.engine_key],
                fallback_policy=(
                    AUTO_FALLBACK_POLICY
                    if request.engine_id.strip().lower() == AUTO_ENGINE_ID
                    else DEFAULT_FALLBACK_POLICY
                ),
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
        source_input: ParseSourceInput,
        *,
        resolved_source: ParseSource | None = None,
    ) -> ParseJobRequest:
        sync_request = self.compile_sync(
            ParseSubmitRequest(
                sources=request.sources,
                engine_id=request.engine_id,
                scene=request.scene,
            ),
            source_input,
            resolved_source=resolved_source,
        )
        return ParseJobRequest(
            **sync_request.model_dump(mode="json"),
            priority=request.priority,
            webhook=request.webhook,
        )

    @staticmethod
    def source_input_from_locator(locator: str) -> ParseSourceInput:
        text = locator.strip()
        if not text:
            raise ValidationError("Parse source locator must not be empty.")
        if text.startswith("cortex://objects/"):
            object_id = text.removeprefix("cortex://objects/").strip("/")
            if not object_id:
                raise ValidationError(
                    "Object-backed parse locators must follow `cortex://objects/{object_id}`."
                )
            return ParseSourceInput(object_id=object_id, kind=ParseInputKind.OBJECT)
        if text.startswith("obj_"):
            return ParseSourceInput(object_id=text, kind=ParseInputKind.OBJECT)
        parsed = urlparse(text)
        if parsed.scheme in {"http", "https"}:
            return ParseSourceInput(
                uri=text,
                kind=ParseInputKind.URL,
                filename=ParseRequestCompiler._filename_from_locator(text),
                mime_type=ParseRequestCompiler._mime_type_from_locator(text),
                canonical_url=text,
            )
        storage_object_id = ParseRequestCompiler._object_id_from_storage_locator(text)
        if storage_object_id is not None:
            return ParseSourceInput(
                object_id=storage_object_id,
                kind=ParseInputKind.OBJECT,
                filename=ParseRequestCompiler._filename_from_locator(text),
                mime_type=ParseRequestCompiler._mime_type_from_locator(text),
            )
        return ParseSourceInput(
            uri=text,
            kind=ParseInputKind.URI,
            filename=ParseRequestCompiler._filename_from_locator(text),
            mime_type=ParseRequestCompiler._mime_type_from_locator(text),
        )

    @staticmethod
    def _filename_from_locator(locator: str) -> str | None:
        parsed = urlparse(locator)
        path = parsed.path or locator
        name = PurePosixPath(path).name
        return name or None

    @staticmethod
    def _mime_type_from_locator(locator: str) -> str | None:
        parsed = urlparse(locator)
        path = parsed.path or locator
        mime_type, _ = mimetypes.guess_type(path)
        return mime_type

    @staticmethod
    def _object_id_from_storage_locator(locator: str) -> str | None:
        parsed = urlparse(locator)
        if parsed.scheme and parsed.scheme != "s3":
            return None
        if parsed.scheme == "":
            first_segment = locator.strip("/").split("/", 1)[0]
            if first_segment.startswith(("http:", "https:", "file:")):
                return None
        path = parsed.path if parsed.scheme else locator
        for segment in path.strip("/").split("/"):
            if segment.startswith("obj_"):
                return segment
        return None

    def _compile_engine_selection(
        self,
        request: ParseSubmitRequest,
        source: ParseSource,
        source_input: ParseSourceInput,
    ) -> CompiledEngineSelection:
        engine_id = request.engine_id.strip().lower()
        if engine_id != AUTO_ENGINE_ID:
            self._require_available(engine_id)
            return CompiledEngineSelection(
                engine_key=engine_id,
                scene_id=request.scene,
                allowed_engines=[engine_id],
            )
        available = self._available_in_priority_order()
        if not available:
            raise ValidationError("No active parse engine is currently available for auto routing.")
        preferred, fallback = self._auto_route_candidates(
            source=source,
            source_input=source_input,
            scene_id=request.scene,
            available_engine_keys=available,
        )
        selected_scene = request.scene or self._default_scene_by_engine.get(preferred)
        return CompiledEngineSelection(
            engine_key=preferred,
            scene_id=selected_scene,
            allowed_engines=[preferred, *fallback],
        )

    def _compile_source(
        self,
        source_input: ParseSourceInput,
        *,
        resolved_source: ParseSource | None = None,
    ) -> ParseSource:
        if resolved_source is not None:
            return resolved_source.model_copy(
                update={
                    "filename": source_input.filename or resolved_source.filename,
                    "expected_content_type": source_input.mime_type
                    or resolved_source.expected_content_type,
                }
            )
        kind = source_input.kind or self._infer_kind(source_input)
        if kind is ParseInputKind.OBJECT:
            raise ValidationError(
                "Object-backed public Parse requests must be resolved to an "
                "engine-accessible source first."
            )
        if source_input.uri is None:
            raise ValidationError("Parse source URI is required for non-object locators.")
        if kind is ParseInputKind.URL:
            return ParseSource(
                input_kind=ParseInputKind.URL,
                url=source_input.uri,
                filename=source_input.filename,
                canonical_url=source_input.canonical_url,
                expected_content_type=source_input.mime_type,
            )
        return ParseSource(
            input_kind=kind,
            uri=source_input.uri,
            filename=source_input.filename,
            expected_content_type=source_input.mime_type,
        )

    @staticmethod
    def _infer_kind(source_input: ParseSourceInput) -> ParseInputKind:
        if source_input.object_id:
            return ParseInputKind.OBJECT
        if source_input.uri and source_input.uri.startswith(("http://", "https://")):
            return ParseInputKind.URL
        return ParseInputKind.URI

    def _available_in_priority_order(self) -> list[str]:
        ordered = [
            "crawl4ai",
            "jina_reader",
            "llama_parse",
            "docling",
            "markitdown",
        ]
        if not self._available_engine_keys:
            return ordered
        priority = [engine for engine in ordered if engine in self._available_engine_keys]
        remainder = sorted(self._available_engine_keys - set(priority))
        return [*priority, *remainder]

    def _auto_route_candidates(
        self,
        *,
        source: ParseSource,
        source_input: ParseSourceInput,
        scene_id: str | None,
        available_engine_keys: list[str],
    ) -> tuple[str, list[str]]:
        extension = self._source_extension(source_input, source)
        scene = (scene_id or "").strip().lower()
        if scene == "fast_extract":
            return self._choose_with_fallback(
                ["jina_reader", "crawl4ai"],
                available_engine_keys,
            )
        if scene == "document_ai":
            return self._choose_with_fallback(
                ["docling", "llama_parse", "markitdown"],
                available_engine_keys,
            )
        if scene == "document_fidelity":
            return self._choose_with_fallback(
                ["llama_parse", "docling"],
                available_engine_keys,
            )
        if scene == "lightweight":
            return self._choose_with_fallback(
                ["markitdown", "docling", "llama_parse"],
                available_engine_keys,
            )
        if source.input_kind is ParseInputKind.URL:
            if extension in DOCUMENT_EXTENSIONS:
                return self._choose_with_fallback(
                    ["llama_parse", "docling", "jina_reader"],
                    available_engine_keys,
                )
            return self._choose_with_fallback(
                ["crawl4ai", "jina_reader"],
                available_engine_keys,
            )
        if extension in DOCUMENT_EXTENSIONS:
            return self._choose_with_fallback(
                ["llama_parse", "docling", "markitdown"],
                available_engine_keys,
            )
        if extension in TEXT_LIKE_EXTENSIONS:
            return self._choose_with_fallback(
                ["markitdown", "docling", "llama_parse"],
                available_engine_keys,
            )
        return self._choose_with_fallback(
            ["docling", "markitdown", "llama_parse"],
            available_engine_keys,
        )

    @staticmethod
    def _choose_with_fallback(
        candidates: list[str],
        available_engine_keys: list[str],
    ) -> tuple[str, list[str]]:
        chosen = [engine for engine in candidates if engine in available_engine_keys]
        if chosen:
            return chosen[0], chosen[1:]
        return available_engine_keys[0], available_engine_keys[1:]

    @staticmethod
    def _source_extension(
        source_input: ParseSourceInput,
        source: ParseSource,
    ) -> str | None:
        filename = source_input.filename or source.filename
        if filename:
            suffix = PurePosixPath(filename).suffix.lower()
            if suffix:
                return suffix
        locator = source.url or source.uri
        if locator:
            return PurePosixPath(urlparse(locator).path).suffix.lower() or None
        return None

    def _preset_for(
        self,
        *,
        engine_key: str,
        scene_id: str | None,
        source: ParseSource,
    ) -> ParseScenePreset:
        self._require_available(engine_key)
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

    def _require_available(self, engine_key: str) -> None:
        if self._available_engine_keys and engine_key not in self._available_engine_keys:
            raise ValidationError(f"Parse engine `{engine_key}` is not currently available.")

    def _default_profile_ref(self, engine_key: str) -> str | None:
        default_scene = self._default_scene_by_engine.get(engine_key)
        if default_scene is None:
            return None
        preset = self._presets.get((engine_key, default_scene))
        return preset.profile_ref if preset is not None else None
