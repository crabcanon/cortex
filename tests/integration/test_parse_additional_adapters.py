"""Tests for additional optional parse adapters."""

from __future__ import annotations

import httpx
import pytest
import respx
from cortex_common import ConfigError
from cortex_contracts import ParseInputKind, ParseSource, ParseSyncRequest
from cortex_parse import EngineExecutionContext
from cortex_parse.adapters import (
    DoclingParseEngine,
    JinaReaderParseEngine,
    LlamaParseEngine,
    MarkItDownParseEngine,
)
from cortex_parse.adapters import docling as docling_adapter
from cortex_parse.adapters import llama_parse as llama_parse_adapter
from cortex_parse.adapters import markitdown as markitdown_adapter


@pytest.mark.asyncio
@respx.mock
async def test_jina_reader_adapter_fetches_markdown() -> None:
    route = respx.get("https://r.jina.ai/https://example.com/article").mock(
        return_value=httpx.Response(
            status_code=200,
            text="# Jina Title\n\nReader body.",
            headers={"content-type": "text/plain"},
        )
    )

    engine = JinaReaderParseEngine(
        {
            "enabled": True,
            "base_url": "https://r.jina.ai",
            "timeout_seconds": 15,
            "api_key": "jina-runtime-token",
            "headers": {"x-runtime-header": "1"},
        }
    )
    result = await engine.execute(
        EngineExecutionContext(
            request=ParseSyncRequest(
                source=ParseSource(
                    input_kind=ParseInputKind.URL,
                    url="https://example.com/article",
                    expected_content_type="text/html",
                )
            ),
            source=ParseSource(
                input_kind=ParseInputKind.URL,
                url="https://example.com/article",
                expected_content_type="text/html",
            ),
            engine_options={"use_readerlm_v2": True},
        )
    )

    assert route.called
    request_headers = route.calls[0].request.headers
    assert request_headers["authorization"] == "Bearer jina-runtime-token"
    assert request_headers["x-runtime-header"] == "1"
    assert request_headers["x-respond-with"] == "readerlm-v2"
    assert result.markdown == "# Jina Title\n\nReader body."
    assert result.title == "Jina Title"
    assert result.metadata["source_host"] == "example.com"
    assert result.engine_payload_summary["used_readerlm_v2"] is True


class _FakeMarkItDownResult:
    text_content = "# MarkItDown Title\n\nConverted content."


class _FakeMarkItDown:
    last_source: str | None = None
    last_options: dict[str, object] | None = None

    def __init__(self, **kwargs: object) -> None:
        type(self).last_options = kwargs

    def convert(self, source_ref: str) -> _FakeMarkItDownResult:
        type(self).last_source = source_ref
        return _FakeMarkItDownResult()


@pytest.mark.asyncio
async def test_markitdown_adapter_uses_optional_converter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(markitdown_adapter, "_load_markitdown_cls", lambda: _FakeMarkItDown)
    monkeypatch.setattr(markitdown_adapter, "_markitdown_version", lambda: "1.0.test")

    engine = MarkItDownParseEngine(
        {"enabled": True, "markitdown": {"enable_plugins": True, "output_format": "markdown"}}
    )
    result = await engine.execute(
        EngineExecutionContext(
            request=ParseSyncRequest(
                source=ParseSource(
                    input_kind=ParseInputKind.URI,
                    uri="file:///tmp/report.pdf",
                    filename="report.pdf",
                    expected_content_type="application/pdf",
                )
            ),
            source=ParseSource(
                input_kind=ParseInputKind.URI,
                uri="file:///tmp/report.pdf",
                filename="report.pdf",
                expected_content_type="application/pdf",
            ),
            engine_options={"markitdown": {"enable_plugins": False}},
        )
    )

    assert engine.descriptor.status.value == "active"
    assert _FakeMarkItDown.last_source == "file:///tmp/report.pdf"
    assert _FakeMarkItDown.last_options == {
        "enable_plugins": False,
        "output_format": "markdown",
    }
    assert result.markdown == "# MarkItDown Title\n\nConverted content."
    assert result.title == "report.pdf"
    assert result.parser_version == "1.0.test"


class _FakeDoclingDocument:
    def export_to_markdown(self) -> str:
        return "# Docling Title\n\nStructured content."


class _FakeDoclingResult:
    document = _FakeDoclingDocument()
    status = "success"


class _FakeDocumentConverter:
    last_source: str | None = None
    last_init_options: dict[str, object] | None = None
    last_convert_options: dict[str, object] | None = None

    def __init__(self, **kwargs: object) -> None:
        type(self).last_init_options = kwargs

    def convert(self, source_ref: str, **kwargs: object) -> _FakeDoclingResult:
        type(self).last_source = source_ref
        type(self).last_convert_options = kwargs
        return _FakeDoclingResult()


def test_docling_adapter_is_disabled_when_optional_dependency_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(docling_adapter, "_docling_version", lambda: None)

    engine = DoclingParseEngine({"enabled": True})

    assert engine.descriptor.status.value == "active"


@pytest.mark.asyncio
async def test_docling_adapter_uses_optional_converter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        docling_adapter,
        "_load_document_converter_cls",
        lambda: _FakeDocumentConverter,
    )
    monkeypatch.setattr(docling_adapter, "_docling_available", lambda: True)
    monkeypatch.setattr(docling_adapter, "_docling_version", lambda: "2.0.test")

    engine = DoclingParseEngine(
        {
            "enabled": True,
            "docling": {"allowed_formats": ["pdf", "pptx"], "enable_remote_services": False},
            "docling_convert": {"raises_on_error": True},
        }
    )
    result = await engine.execute(
        EngineExecutionContext(
            request=ParseSyncRequest(
                source=ParseSource(
                    input_kind=ParseInputKind.URI,
                    uri="file:///tmp/slides.pptx",
                    filename="slides.pptx",
                    expected_content_type=(
                        "application/vnd.openxmlformats-officedocument."
                        "presentationml.presentation"
                    ),
                )
            ),
            source=ParseSource(
                input_kind=ParseInputKind.URI,
                uri="file:///tmp/slides.pptx",
                filename="slides.pptx",
                expected_content_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "presentationml.presentation"
                ),
            ),
            engine_options={
                "docling": {"allowed_formats": ["pptx"]},
                "docling_convert": {"raises_on_error": False},
            },
        )
    )

    assert engine.descriptor.status.value == "active"
    assert _FakeDocumentConverter.last_source == "file:///tmp/slides.pptx"
    assert _FakeDocumentConverter.last_init_options == {
        "allowed_formats": ["pptx"],
        "enable_remote_services": False,
    }
    assert _FakeDocumentConverter.last_convert_options == {"raises_on_error": False}
    assert result.markdown == "# Docling Title\n\nStructured content."
    assert result.title == "slides.pptx"
    assert result.parser_version == "2.0.test"


class _FakeLlamaDocument:
    def __init__(self, text: str, metadata: dict[str, object]) -> None:
        self.text = text
        self.metadata = metadata


class _FakeLlamaParse:
    last_options: dict[str, object] | None = None
    last_source: str | None = None

    def __init__(self, **kwargs: object) -> None:
        type(self).last_options = kwargs

    async def aload_data(self, source_ref: str) -> list[_FakeLlamaDocument]:
        type(self).last_source = source_ref
        return [
            _FakeLlamaDocument(
                "# LlamaParse Title\n\nPage one.",
                {"title": "LlamaParse Title", "page_label": "1"},
            ),
            _FakeLlamaDocument("Page two.", {"page_label": "2"}),
        ]


@pytest.mark.asyncio
async def test_llama_parse_adapter_maps_async_documents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(llama_parse_adapter, "_load_llama_parse_cls", lambda: _FakeLlamaParse)
    monkeypatch.setattr(llama_parse_adapter, "_llama_parse_version", lambda: "0.7.test")

    engine = LlamaParseEngine(
        {
            "enabled": True,
            "api_key": "llx-runtime",
            "llama_parse": {"language": "en", "premium_mode": False},
        }
    )
    result = await engine.execute(
        EngineExecutionContext(
            request=ParseSyncRequest(
                source=ParseSource(
                    input_kind=ParseInputKind.URI,
                    uri="file:///tmp/whitepaper.pdf",
                    filename="whitepaper.pdf",
                    expected_content_type="application/pdf",
                )
            ),
            source=ParseSource(
                input_kind=ParseInputKind.URI,
                uri="file:///tmp/whitepaper.pdf",
                filename="whitepaper.pdf",
                expected_content_type="application/pdf",
            ),
            engine_options={
                "llama_parse": {
                    "api_key": "llx-test",
                    "language": "en",
                    "premium_mode": True,
                }
            },
        )
    )

    assert engine.descriptor.status.value == "active"
    assert _FakeLlamaParse.last_source == "file:///tmp/whitepaper.pdf"
    assert _FakeLlamaParse.last_options == {
        "api_key": "llx-test",
        "language": "en",
        "premium_mode": True,
        "result_type": "markdown",
        "verbose": False,
    }
    assert result.markdown == "# LlamaParse Title\n\nPage one.\n\nPage two."
    assert result.title == "LlamaParse Title"
    assert result.metadata["document_count"] == 2
    assert result.raw_metadata["documents"][0]["page_label"] == "1"
    assert result.parser_version == "0.7.test"


@pytest.mark.asyncio
async def test_llama_parse_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llama_parse_adapter, "_load_llama_parse_cls", lambda: _FakeLlamaParse)
    monkeypatch.delenv("LLAMA_CLOUD_API_KEY", raising=False)

    with pytest.raises(ConfigError):
        await LlamaParseEngine({"enabled": True}).execute(
            EngineExecutionContext(
                request=ParseSyncRequest(
                    source=ParseSource(
                        input_kind=ParseInputKind.URI,
                        uri="file:///tmp/whitepaper.pdf",
                    )
                ),
                source=ParseSource(
                    input_kind=ParseInputKind.URI,
                    uri="file:///tmp/whitepaper.pdf",
                ),
            )
        )
