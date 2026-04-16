"""Unit tests for the public Parse request compiler."""

from __future__ import annotations

import pytest
from cortex_common import ValidationError
from cortex_contracts import (
    ParseEngineDeploymentMode,
    ParseEngineDescriptor,
    ParseEngineList,
    ParseEngineStatus,
    ParseInputKind,
    ParseSource,
    ParseSourceInput,
    ParseSubmitRequest,
)
from cortex_parse import ParseRequestCompiler


def test_compiler_maps_two_parameter_request_to_default_scene_and_profile() -> None:
    compiler = ParseRequestCompiler({"crawl4ai"})

    compiled = compiler.compile_sync(
        ParseSubmitRequest(
            source=ParseSourceInput(
                uri="https://example.com/docs",
                mime_type="text/html",
            ),
            engine_id="crawl4ai",
        )
    )

    assert compiled.source.input_kind is ParseInputKind.URL
    assert compiled.source.url == "https://example.com/docs"
    assert compiled.parser.profile_ref == "crawl4ai_balanced"
    assert compiled.parser.allowed_engines == ["crawl4ai"]
    assert compiled.timeout_seconds == 45
    assert compiled.crawl.browser_profile.use_undetected_browser is False
    assert compiled.crawl.capture.capture_pdf is False


def test_compiler_enables_crawl4ai_deep_web_advanced_features() -> None:
    compiler = ParseRequestCompiler({"crawl4ai"})

    compiled = compiler.compile_sync(
        ParseSubmitRequest(
            source=ParseSourceInput(
                uri="https://example.com/interactive",
                mime_type="text/html",
            ),
            engine_id="crawl4ai",
            scene="deep_web",
        )
    )

    assert compiled.parser.profile_ref == "crawl4ai_deep_web"
    assert compiled.timeout_seconds == 90
    assert compiled.crawl.browser_profile.enable_stealth is True
    assert compiled.crawl.browser_profile.use_undetected_browser is True
    assert compiled.crawl.browser_profile.use_persistent_context is True
    assert compiled.crawl.capture.capture_pdf is True
    assert compiled.crawl.capture.capture_screenshot is True
    assert compiled.crawl.capture.fetch_ssl_certificate is True
    assert compiled.crawl.capture.capture_network_log is True
    assert compiled.crawl.capture.capture_console_log is True
    assert compiled.crawl.capture.scan_full_page is True
    assert compiled.crawl.capture.flatten_shadow_dom is True


def test_compiler_requires_resolved_object_source_for_public_object_requests() -> None:
    compiler = ParseRequestCompiler({"docling"})

    with pytest.raises(
        ValidationError,
        match="must be resolved to an engine-accessible source first",
    ):
        compiler.compile_sync(
            ParseSubmitRequest(
                source=ParseSourceInput(
                    object_id="obj_123",
                    filename="guide.pdf",
                    mime_type="application/pdf",
                ),
                engine_id="docling",
            )
        )


def test_compiler_preserves_resolved_object_sources_and_annotates_engine_catalog() -> None:
    compiler = ParseRequestCompiler({"docling"})
    resolved_source = ParseSource(
        input_kind=ParseInputKind.OBJECT,
        object_id="obj_123",
        url="https://storage.test/objects/obj_123?signature=demo",
        filename="guide.pdf",
        expected_content_type="application/pdf",
    )

    compiled = compiler.compile_sync(
        ParseSubmitRequest(
            source=ParseSourceInput(
                object_id="obj_123",
                filename="guide.pdf",
                mime_type="application/pdf",
                canonical_url="https://example.com/guide.pdf",
            ),
            engine_id="docling",
        ),
        resolved_source=resolved_source,
    )
    described = compiler.describe_engines(
        ParseEngineList(
            engines=[
                ParseEngineDescriptor(
                    engine_key="docling",
                    display_name="Docling",
                    engine_family="document_local",
                    deployment_mode=ParseEngineDeploymentMode.LOCAL,
                    status=ParseEngineStatus.ACTIVE,
                    supported_source_types=["object", "url", "uri"],
                    supported_formats=["application/pdf"],
                    capabilities=["markdown", "layout"],
                )
            ]
        )
    )

    assert compiled.source.input_kind is ParseInputKind.OBJECT
    assert compiled.source.object_id == "obj_123"
    assert compiled.source.url is not None
    assert compiled.source.canonical_url == "https://example.com/guide.pdf"
    assert compiled.parser.profile_ref == "docling_document_ai"
    assert described.engines[0].default_scene_id == "document_ai"
    assert described.engines[0].supported_scene_ids == ["document_ai"]
    assert described.engines[0].default_profile_ref == "docling_document_ai"
