"""IBM Docling adapter."""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import importlib.metadata
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


def _docling_available() -> bool:
    try:
        _load_document_converter_cls()
    except Exception:
        return False
    return True


def _docling_version() -> str | None:
    try:
        return importlib.metadata.version("docling")
    except importlib.metadata.PackageNotFoundError:  # pragma: no cover - optional dependency
        return None


class DoclingParseEngine(ParseEngineProtocol):
    """Use Docling for higher-fidelity local document conversion."""

    def __init__(self) -> None:
        available = _docling_available()
        self._descriptor = ParseEngineDescriptor(
            engine_key="docling",
            display_name="Docling",
            engine_family="document_local",
            deployment_mode=ParseEngineDeploymentMode.LOCAL,
            status=ParseEngineStatus.ACTIVE if available else ParseEngineStatus.DISABLED,
            supported_source_types=[ParseInputKind.URI.value, ParseInputKind.URL.value],
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
        source_ref = context.source.uri or context.source.url
        if source_ref is None:
            raise ValidationError("Docling requires `source.uri` or `source.url`.")
        converter_cls = _load_document_converter_cls()
        converter = converter_cls(**self._converter_options(context))
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

    @staticmethod
    def _converter_options(context: EngineExecutionContext) -> dict[str, Any]:
        options = context.engine_options.get("docling")
        return options if isinstance(options, dict) else {}

    @staticmethod
    def _convert_options(context: EngineExecutionContext) -> dict[str, Any]:
        options = context.engine_options.get("docling_convert")
        return options if isinstance(options, dict) else {}

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
