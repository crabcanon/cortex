"""IBM Docling adapter."""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import importlib.metadata
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from cortex_common import ConfigError, ValidationError, utc_now
from cortex_contracts import (
    ParseEngineDeploymentMode,
    ParseEngineDescriptor,
    ParseEngineStatus,
    ParseInputKind,
)

from ..models import EngineExecutionContext, EngineExecutionResult, ParseEngineProtocol


def _load_document_converter_cls() -> type[Any]:
    try:
        module = importlib.import_module("docling.document_converter")
    except ImportError as exc:  # pragma: no cover - depends on optional dependency
        raise ConfigError(
            "Docling is not installed. Install `docling` to enable this adapter."
        ) from exc
    return module.DocumentConverter


def _docling_version() -> str | None:
    try:
        return importlib.metadata.version("docling")
    except importlib.metadata.PackageNotFoundError:  # pragma: no cover - optional dependency
        return None


def _docling_available() -> bool:
    return _docling_version() is not None


class DoclingParseEngine(ParseEngineProtocol):
    """Use Docling for higher-fidelity local document conversion."""

    def __init__(self, config: dict[str, object] | None = None) -> None:
        self._config = dict(config) if isinstance(config, dict) else {}
        self._cached_converter: Any | None = None
        self._converter_cache_key: str | None = None
        enabled = bool(self._config.get("enabled", True))
        self._local_available = _docling_available()

        status = ParseEngineStatus.ACTIVE if enabled else ParseEngineStatus.DISABLED
        if enabled and not self._local_available:
            status = ParseEngineStatus.DISABLED

        self._descriptor = ParseEngineDescriptor(
            engine_key="docling",
            display_name="Docling",
            engine_family="document_local",
            deployment_mode=ParseEngineDeploymentMode.LOCAL,
            status=status,
            supported_source_types=[
                ParseInputKind.URI.value,
                ParseInputKind.URL.value,
                ParseInputKind.OBJECT.value,
            ],
            supported_formats=[
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                "text/html",
                "text/markdown",
                "image/*",
                "audio/*",
            ],
            capabilities=["markdown", "structured_document", "pdf", "ocr", "tables"],
        )

    @property
    def descriptor(self) -> ParseEngineDescriptor:
        return self._descriptor

    async def execute(self, context: EngineExecutionContext) -> EngineExecutionResult:
        if not self._local_available:
            raise ConfigError(
                "Docling is enabled in the Cortex runtime catalog but is not installed in this "
                "process. Submit an async parse job to a `cortex-parse-worker-docling` worker, or "
                "install the `cortex-parse[docling]` extra in the API process for synchronous "
                "Docling execution."
            )
        source_ref = context.source.uri or context.source.url
        if source_ref is None:
            raise ValidationError("Docling requires `source.uri` or `source.url`.")
        converter = self._get_converter(context)
        result = await asyncio.to_thread(
            converter.convert,
            source_ref,
            **self._convert_options(context),
        )
        document = getattr(result, "document", None)
        if document is None:
            raise ConfigError("Docling completed without returning a document.")
        markdown = str(document.export_to_markdown()).strip()
        if not markdown:
            raise ConfigError("Docling completed without producing Markdown content.")
        title = self._title(source_ref, context)
        content_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
        return EngineExecutionResult(
            markdown=markdown,
            source_format=context.source.expected_content_type or self._format(source_ref),
            detected_mime_type=context.source.expected_content_type,
            title=title,
            metadata={"title": title, "source_ref": source_ref},
            raw_metadata={"source_ref": source_ref, "status": str(getattr(result, "status", ""))},
            fetched_at=utc_now(),
            final_url=source_ref if source_ref.startswith(("http://", "https://")) else None,
            parser_version=_docling_version(),
            content_hash_sha256=content_hash,
            engine_payload_summary={"converter": "docling"},
        )

    def _get_converter(self, context: EngineExecutionContext) -> Any:
        options = self._converter_options(context)
        cache_key = json.dumps(options, sort_keys=True, default=str)
        if self._cached_converter is not None and self._converter_cache_key == cache_key:
            return self._cached_converter
        converter_cls = _load_document_converter_cls()
        self._cached_converter = converter_cls(**options)
        self._converter_cache_key = cache_key
        return self._cached_converter

    def _converter_options(self, context: EngineExecutionContext) -> dict[str, Any]:
        options = self._config.get("docling")
        converter_options = dict(options) if isinstance(options, dict) else {}
        request_options = context.engine_options.get("docling")
        if isinstance(request_options, dict):
            converter_options.update(request_options)
        return converter_options

    def _convert_options(self, context: EngineExecutionContext) -> dict[str, Any]:
        options = self._config.get("docling_convert")
        convert_options = dict(options) if isinstance(options, dict) else {}
        request_options = context.engine_options.get("docling_convert")
        if isinstance(request_options, dict):
            convert_options.update(request_options)
        return convert_options

    @staticmethod
    def _title(source_ref: str, context: EngineExecutionContext) -> str:
        if context.source.filename:
            return context.source.filename
        parsed = urlparse(source_ref)
        if parsed.scheme in {"http", "https"}:
            return parsed.path.rsplit("/", 1)[-1] or parsed.netloc
        return Path(source_ref).name or source_ref

    @staticmethod
    def _format(source_ref: str) -> str:
        suffix = Path(urlparse(source_ref).path or source_ref).suffix.lower()
        return {
            ".md": "text/markdown",
            ".html": "text/html",
            ".htm": "text/html",
            ".pdf": "application/pdf",
            ".docx": (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
            ".pptx": (
                "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            ),
        }.get(suffix, "application/octet-stream")
