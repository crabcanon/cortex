"""Integration-style tests for the Crawl4AI adapter mapping."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from cortex_contracts import (
    BrowserProfile,
    CaptureOptions,
    CrawlOptions,
    ParseInputKind,
    ParseLlmReadyMode,
    ParseOutputOptions,
    ParseSource,
    ParseSyncRequest,
)
from cortex_parse import Crawl4AIParseEngine, EngineExecutionContext
from cortex_parse.adapters import crawl4ai as crawl4ai_adapter


class _FakeMarkdownResult:
    raw_markdown = "# Raw Title\n\nRaw body."
    fit_markdown = "# Fit Title\n\nFit body."
    markdown_with_citations = "# Citation Title\n\nCitation body."


class _FakeSslCertificate:
    issuer_common_name = "Example CA"
    valid_from = datetime(2026, 4, 1, tzinfo=UTC)
    valid_until = datetime(2027, 4, 1, tzinfo=UTC)
    fingerprint = "sha256:example"


class _FakeCrawlResult:
    success = True
    markdown = _FakeMarkdownResult()
    metadata = {
        "title": "Example Page",
        "language": "en",
        "category_tags": ["docs"],
        "timings_ms": {"fetch": 25, "render": 55},
    }
    response_headers = {"Content-Type": "text/html", "Content-Length": "321"}
    links = {"internal": [{"href": "/a"}, {"href": "/b"}], "external": [{"href": "https://x"}]}
    media = {"images": [{"src": "a.png"}], "videos": []}
    html = "<html><body>Example</body></html>"
    cleaned_html = "<body>Example</body>"
    status_code = 200
    redirected_url = "https://example.com/final"
    redirected_status_code = 200
    screenshot = "base64-image"
    pdf = b"%PDF-1.7"
    network_requests = [{"url": "https://example.com/api"}]
    console_messages = [{"type": "log", "text": "ok"}]
    downloaded_files = ["downloaded.txt"]
    ssl_certificate = _FakeSslCertificate()
    tables = [{"headers": ["A"], "rows": [["1"]]}]
    session_id = "session-123"


class _FakeBrowserConfig:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs


class _FakeCrawlerRunConfig:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs


class _FakeCacheMode:
    BYPASS = "BYPASS"
    DISABLED = "DISABLED"


class _FakeAsyncWebCrawler:
    last_browser_config: _FakeBrowserConfig | None = None
    last_run_config: _FakeCrawlerRunConfig | None = None
    last_url: str | None = None

    def __init__(self, *, config: _FakeBrowserConfig) -> None:
        type(self).last_browser_config = config

    async def __aenter__(self) -> _FakeAsyncWebCrawler:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb

    async def arun(self, *, url: str, config: _FakeCrawlerRunConfig) -> _FakeCrawlResult:
        type(self).last_url = url
        type(self).last_run_config = config
        return _FakeCrawlResult()


@pytest.mark.asyncio
async def test_crawl4ai_adapter_maps_request_into_engine_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        crawl4ai_adapter,
        "_load_crawl4ai_sdk",
        lambda: crawl4ai_adapter._Crawl4AISdk(
            async_web_crawler=_FakeAsyncWebCrawler,
            browser_config=_FakeBrowserConfig,
            crawler_run_config=_FakeCrawlerRunConfig,
            cache_mode=_FakeCacheMode,
        ),
    )
    monkeypatch.setattr(crawl4ai_adapter, "_crawl4ai_version", lambda: "0.8.test")

    engine = Crawl4AIParseEngine()
    result = await engine.execute(
        EngineExecutionContext(
            request=ParseSyncRequest(
                source=ParseSource(
                    input_kind=ParseInputKind.URL,
                    url="https://example.com/start",
                ),
                crawl=CrawlOptions(
                    respect_robots_txt=True,
                    wait_for="css:.article",
                    js_code=["window.scrollTo(0, document.body.scrollHeight)"],
                    browser_profile=BrowserProfile(
                        browser_type="chromium",
                        headless=True,
                        locale="en-US",
                        timezone_id="Asia/Shanghai",
                        viewport_width=1440,
                        viewport_height=900,
                        user_agent="CortexBot/1.0",
                        headers={"X-Test": "1"},
                        proxy_ref="http://proxy.local:8080",
                        enable_stealth=True,
                        session_id="session-123",
                    ),
                    capture=CaptureOptions(
                        capture_screenshot=True,
                        capture_pdf=True,
                        force_viewport_screenshot=True,
                        scan_full_page=True,
                        fetch_ssl_certificate=True,
                        capture_network_log=True,
                        capture_console_log=True,
                    ),
                ),
                output=ParseOutputOptions(llm_ready_mode=ParseLlmReadyMode.FIT_MARKDOWN),
            ),
            source=ParseSource(
                input_kind=ParseInputKind.URL,
                url="https://example.com/start",
            ),
            engine_options={
                "browser_config": {"light_mode": True},
                "crawler_run_config": {"magic": True},
            },
        )
    )

    assert engine.descriptor.engine_key == "crawl4ai"
    assert _FakeAsyncWebCrawler.last_url == "https://example.com/start"
    assert _FakeAsyncWebCrawler.last_browser_config is not None
    assert _FakeAsyncWebCrawler.last_browser_config.kwargs["browser_type"] == "chromium"
    assert _FakeAsyncWebCrawler.last_browser_config.kwargs["enable_stealth"] is True
    assert _FakeAsyncWebCrawler.last_browser_config.kwargs["light_mode"] is True
    assert _FakeAsyncWebCrawler.last_run_config is not None
    assert _FakeAsyncWebCrawler.last_run_config.kwargs["check_robots_txt"] is True
    assert _FakeAsyncWebCrawler.last_run_config.kwargs["screenshot"] is True
    assert _FakeAsyncWebCrawler.last_run_config.kwargs["pdf"] is True
    assert _FakeAsyncWebCrawler.last_run_config.kwargs["magic"] is True
    assert result.markdown == "# Fit Title\n\nFit body."
    assert result.title == "Example Page"
    assert result.detected_mime_type == "text/html"
    assert result.parser_version == "0.8.test"
    assert result.link_counts == {"internal": 2, "external": 1}
    assert result.media_counts == {"images": 1, "videos": 0}
    assert result.anti_bot_strategy == "stealth"
    assert result.used_proxy is True
    assert result.content_length_bytes == 321
    assert result.artifacts.ssl_certificate is not None
    assert result.artifacts.ssl_certificate.issuer_common_name == "Example CA"
    assert result.engine_payload_summary["captured_screenshot"] is True
    assert result.engine_payload_summary["captured_pdf"] is True
    assert result.engine_payload_summary["captured_network_requests"] == 1
    assert result.engine_payload_summary["captured_console_messages"] == 1
