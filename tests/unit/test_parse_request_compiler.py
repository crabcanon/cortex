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
    ParseJobSubmitRequest,
    ParseSource,
    ParseSubmitRequest,
)
from cortex_parse import ParseRequestCompiler


def test_compiler_maps_two_parameter_request_to_default_scene_and_profile() -> None:
    compiler = ParseRequestCompiler({"crawl4ai"})
    request = ParseSubmitRequest(
        sources=["https://example.com/docs"],
        engine_id="crawl4ai",
    )
    source_input = compiler.source_input_from_locator(request.sources[0])

    compiled = compiler.compile_sync(request, source_input)

    assert compiled.source.input_kind is ParseInputKind.URL
    assert compiled.source.url == "https://example.com/docs"
    assert compiled.parser.profile_ref == "crawl4ai_balanced"
    assert compiled.parser.allowed_engines == ["crawl4ai"]
    assert compiled.timeout_seconds == 45
    assert compiled.crawl.browser_profile.use_undetected_browser is False
    assert compiled.crawl.capture.capture_pdf is False


def test_compiler_enables_crawl4ai_deep_web_advanced_features() -> None:
    compiler = ParseRequestCompiler({"crawl4ai"})
    request = ParseSubmitRequest(
        sources=["https://example.com/interactive"],
        engine_id="crawl4ai",
        scene="deep_web",
    )
    source_input = compiler.source_input_from_locator(request.sources[0])

    compiled = compiler.compile_sync(request, source_input)

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
    request = ParseSubmitRequest(
        sources=["cortex://objects/obj_123"],
        engine_id="docling",
    )
    source_input = compiler.source_input_from_locator(request.sources[0])

    with pytest.raises(
        ValidationError,
        match="must be resolved to an engine-accessible source first",
    ):
        compiler.compile_sync(request, source_input)


def test_compiler_preserves_resolved_object_sources_and_annotates_engine_catalog() -> None:
    compiler = ParseRequestCompiler({"docling"})
    request = ParseSubmitRequest(
        sources=["cortex://objects/obj_123"],
        engine_id="docling",
    )
    source_input = compiler.source_input_from_locator(request.sources[0])
    resolved_source = ParseSource(
        input_kind=ParseInputKind.OBJECT,
        object_id="obj_123",
        url="https://storage.test/objects/obj_123?signature=demo",
        filename="guide.pdf",
        expected_content_type="application/pdf",
        canonical_url="https://example.com/guide.pdf",
    )

    compiled = compiler.compile_sync(
        request,
        source_input,
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


def test_compiler_uses_longer_document_timeout_for_async_jobs() -> None:
    compiler = ParseRequestCompiler({"docling"})
    sync_request = ParseSubmitRequest(
        sources=["https://example.com/manual.pdf"],
        engine_id="docling",
    )
    job_request = ParseJobSubmitRequest(
        sources=["https://example.com/manual.pdf"],
        engine_id="docling",
    )
    source_input = compiler.source_input_from_locator(sync_request.sources[0])

    compiled_sync = compiler.compile_sync(sync_request, source_input)
    compiled_job = compiler.compile_job(job_request, source_input)

    assert compiled_sync.timeout_seconds == 90
    assert compiled_job.timeout_seconds == 900


def test_compiler_auto_selects_available_web_engine_and_fallbacks() -> None:
    compiler = ParseRequestCompiler({"crawl4ai", "jina_reader"})
    request = ParseSubmitRequest(
        sources=["https://example.com/docs"],
        engine_id="auto",
    )
    source_input = compiler.source_input_from_locator(request.sources[0])

    compiled = compiler.compile_sync(request, source_input)

    assert compiled.parser.preferred_engine_key == "crawl4ai"
    assert compiled.parser.allowed_engines == ["crawl4ai", "jina_reader"]
    assert compiled.parser.profile_ref == "crawl4ai_balanced"
    assert compiled.parser.fallback_policy.enabled is True
    assert compiled.parser.fallback_policy.max_engine_attempts == 3


def test_compiler_auto_selects_document_engine_from_source_extension() -> None:
    compiler = ParseRequestCompiler({"llama_parse", "docling", "markitdown"})
    request = ParseSubmitRequest(
        sources=["s3://demo-bucket/manuals/architecture.pdf"],
        engine_id="auto",
    )
    source_input = compiler.source_input_from_locator(request.sources[0])

    compiled = compiler.compile_sync(request, source_input)

    assert compiled.source.input_kind is ParseInputKind.URI
    assert compiled.source.filename == "architecture.pdf"
    assert compiled.source.expected_content_type == "application/pdf"
    assert compiled.parser.preferred_engine_key == "llama_parse"
    assert compiled.parser.allowed_engines == ["llama_parse", "docling", "markitdown"]
    assert compiled.parser.profile_ref == "llama_parse_document_fidelity"


def test_compiler_extracts_cortex_object_id_from_minio_s3_locator() -> None:
    compiler = ParseRequestCompiler({"docling"})

    source_input = compiler.source_input_from_locator(
        "s3://cortex-local/tenant_demo/obj_a3da967e3ca446cab3631bb7/bofa_note.pdf"
    )
    raw_source_input = compiler.source_input_from_locator(
        "cortex-local/tenant_demo/obj_a3da967e3ca446cab3631bb7/bofa_note.pdf"
    )

    assert source_input.kind is ParseInputKind.OBJECT
    assert source_input.object_id == "obj_a3da967e3ca446cab3631bb7"
    assert source_input.filename == "bofa_note.pdf"
    assert source_input.mime_type == "application/pdf"
    assert raw_source_input.kind is ParseInputKind.OBJECT
    assert raw_source_input.object_id == "obj_a3da967e3ca446cab3631bb7"


def test_compiler_explicit_engine_disables_fallback_for_each_batch_source() -> None:
    compiler = ParseRequestCompiler({"docling", "markitdown", "llama_parse"})
    request = ParseSubmitRequest(
        sources=[
            "https://example.com/a.pdf",
            "https://example.com/b.pdf",
        ],
        engine_id="docling",
    )

    compiled = [
        compiler.compile_sync(request, compiler.source_input_from_locator(source))
        for source in request.sources
    ]

    assert [item.parser.allowed_engines for item in compiled] == [
        ["docling"],
        ["docling"],
    ]
    assert all(
        item.parser.preferred_engine_key == "docling"
        and item.parser.fallback_policy.enabled is False
        for item in compiled
    )


def test_compiler_auto_honors_scene_override_when_supported() -> None:
    compiler = ParseRequestCompiler({"crawl4ai", "jina_reader"})
    request = ParseSubmitRequest(
        sources=["https://example.com/docs"],
        engine_id="auto",
        scene="fast_extract",
    )
    source_input = compiler.source_input_from_locator(request.sources[0])

    compiled = compiler.compile_sync(request, source_input)

    assert compiled.parser.preferred_engine_key == "jina_reader"
    assert compiled.parser.profile_ref == "jina_reader_fast_extract"
    assert compiled.parser.allowed_engines == ["jina_reader", "crawl4ai"]
