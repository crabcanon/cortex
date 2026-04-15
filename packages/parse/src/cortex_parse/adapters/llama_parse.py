"""LlamaParse adapter."""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import importlib.metadata
import os
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


def _load_llama_parse_cls() -> type[Any]:
    try:
        module = importlib.import_module("llama_parse")
    except ImportError as exc:  # pragma: no cover - depends on optional dependency
        raise ConfigError(
            "LlamaParse is not installed. Install `llama-parse` to enable this adapter."
        ) from exc
    return module.LlamaParse


def _llama_parse_available() -> bool:
    try:
        _load_llama_parse_cls()
    except Exception:
        return False
    return True


def _llama_parse_version() -> str | None:
    for package_name in ("llama-parse", "llama-index-readers-llama-parse"):
        try:
            return importlib.metadata.version(package_name)
        except importlib.metadata.PackageNotFoundError:
            continue
    return None


class LlamaParseEngine(ParseEngineProtocol):
    """Use LlamaParse for remote high-fidelity document parsing."""

    def __init__(self, config: dict[str, object] | None = None) -> None:
        self._config = dict(config) if isinstance(config, dict) else {}
        enabled = bool(self._config.get("enabled", False))
        available = _llama_parse_available()
        self._descriptor = ParseEngineDescriptor(
            engine_key="llama_parse",
            display_name="LlamaParse",
            engine_family="document_remote",
            deployment_mode=ParseEngineDeploymentMode.REMOTE,
            status=(
                ParseEngineStatus.ACTIVE
                if enabled and available
                else ParseEngineStatus.DISABLED
            ),
            supported_source_types=[ParseInputKind.URI.value, ParseInputKind.URL.value],
            supported_formats=[
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "text/html",
                "image/*",
            ],
            capabilities=[
                "markdown",
                "high_fidelity",
                "tables",
                "layout",
                "ocr",
                "remote_parse",
            ],
        )

    @property
    def descriptor(self) -> ParseEngineDescriptor:
        return self._descriptor

    async def execute(self, context: EngineExecutionContext) -> EngineExecutionResult:
        source_ref = context.source.uri or context.source.url
        if source_ref is None:
            raise ValidationError("LlamaParse requires `source.uri` or `source.url`.")
        if context.source.input_kind is ParseInputKind.OBJECT:
            raise ValidationError("LlamaParse object sources must be resolved to a URI first.")

        parser_cls = _load_llama_parse_cls()
        parser = parser_cls(**self._parser_options(context))
        documents = await self._load_documents(parser, source_ref)
        markdown, metadata = self._documents_to_markdown(documents)
        title = self._title(source_ref, context, metadata)
        content_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
        return EngineExecutionResult(
            markdown=markdown,
            source_format=context.source.expected_content_type or self._format(source_ref),
            detected_mime_type=context.source.expected_content_type,
            title=title,
            metadata={
                "title": title,
                "source_ref": source_ref,
                "document_count": len(documents),
                **metadata,
            },
            raw_metadata={
                "source_ref": source_ref,
                "documents": [self._document_metadata(document) for document in documents],
            },
            fetched_at=utc_now(),
            final_url=source_ref if source_ref.startswith(("http://", "https://")) else None,
            parser_version=_llama_parse_version(),
            content_hash_sha256=content_hash,
            engine_payload_summary={"parser": "llama_parse", "document_count": len(documents)},
        )

    def _parser_options(self, context: EngineExecutionContext) -> dict[str, Any]:
        options = self._config.get("llama_parse")
        parser_options = dict(options) if isinstance(options, dict) else {}
        request_options = context.engine_options.get("llama_parse")
        if isinstance(request_options, dict):
            parser_options.update(request_options)
        api_key = (
            parser_options.get("api_key")
            or self._config.get("api_key")
            or os.getenv("LLAMA_CLOUD_API_KEY")
        )
        mode = str(self._config.get("mode", "cloud_api")).strip() or "cloud_api"
        if mode != "cloud_api":
            raise ConfigError(
                "Only `cloud_api` mode is currently supported by the LlamaParse adapter."
            )
        if not api_key:
            raise ConfigError(
                "LlamaParse requires a unified runtime config `api_key_ref`, "
                "`engine_options.llama_parse.api_key`, or `LLAMA_CLOUD_API_KEY`."
            )
        parser_options["api_key"] = api_key
        parser_options.setdefault("result_type", "markdown")
        parser_options.setdefault("verbose", False)
        return parser_options

    @staticmethod
    async def _load_documents(parser: Any, source_ref: str) -> list[Any]:
        if hasattr(parser, "aload_data"):
            documents = await parser.aload_data(source_ref)
        elif hasattr(parser, "load_data"):
            documents = await asyncio.to_thread(parser.load_data, source_ref)
        else:
            raise ConfigError("LlamaParse adapter did not expose load_data/aload_data.")
        if not isinstance(documents, list):
            documents = list(documents)
        if not documents:
            raise ConfigError("LlamaParse completed without returning documents.")
        return documents

    @staticmethod
    def _documents_to_markdown(documents: list[Any]) -> tuple[str, dict[str, Any]]:
        chunks: list[str] = []
        merged_metadata: dict[str, Any] = {}
        for index, document in enumerate(documents):
            text = LlamaParseEngine._document_text(document)
            if text:
                chunks.append(text)
            metadata = LlamaParseEngine._document_metadata(document)
            for key, value in metadata.items():
                merged_metadata.setdefault(str(key), value)
            merged_metadata[f"document_{index}_metadata"] = metadata
        markdown = "\n\n".join(chunk.strip() for chunk in chunks if chunk.strip()).strip()
        if not markdown:
            raise ConfigError("LlamaParse completed without producing Markdown content.")
        return markdown, merged_metadata

    @staticmethod
    def _document_text(document: Any) -> str | None:
        text = getattr(document, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()
        if hasattr(document, "get_content"):
            content = document.get_content()
            if isinstance(content, str) and content.strip():
                return content.strip()
        if isinstance(document, dict):
            value = document.get("text") or document.get("content")
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _document_metadata(document: Any) -> dict[str, Any]:
        metadata = getattr(document, "metadata", None)
        if isinstance(metadata, dict):
            return dict(metadata)
        if isinstance(document, dict) and isinstance(document.get("metadata"), dict):
            return dict(document["metadata"])
        return {}

    @staticmethod
    def _title(source_ref: str, context: EngineExecutionContext, metadata: dict[str, Any]) -> str:
        for key in ("title", "file_name", "filename"):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
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
            ".pdf": "application/pdf",
            ".docx": (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
            ".pptx": (
                "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            ),
            ".xlsx": (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            ".html": "text/html",
            ".htm": "text/html",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
        }.get(suffix, "application/octet-stream")
