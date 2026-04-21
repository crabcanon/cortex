"""Integration-style tests for the Crawl4AI adapter mapping."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from cortex_common import CortexError, ValidationError
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


class _CompatBrowserConfig:
    def __init__(
        self,
        *,
        browser_type: str,
        headless: bool,
        viewport_width: int,
        viewport_height: int,
        headers: dict[str, str],
        user_agent: str | None = None,
        proxy: str | None = None,
        locale: str | None = None,
        timezone_id: str | None = None,
        use_persistent_context: bool = False,
        light_mode: bool = False,
    ) -> None:
        self.kwargs = {
            "browser_type": browser_type,
            "headless": headless,
            "viewport_width": viewport_width,
            "viewport_height": viewport_height,
            "headers": headers,
            "user_agent": user_agent,
            "proxy": proxy,
            "locale": locale,
            "timezone_id": timezone_id,
            "use_persistent_context": use_persistent_context,
            "light_mode": light_mode,
        }


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
    last_base_directory: str | None = None

    def __init__(self, *, config: _FakeBrowserConfig, base_directory: str | None = None) -> None:
        type(self).last_browser_config = config
        type(self).last_base_directory = base_directory

    async def __aenter__(self) -> _FakeAsyncWebCrawler:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb

    async def arun(self, *, url: str, config: _FakeCrawlerRunConfig) -> _FakeCrawlResult:
        type(self).last_url = url
        type(self).last_run_config = config
        return _FakeCrawlResult()


class _FailureCrawlResult:
    success = False
    error_message = "crawler failed"


class _MinimalMarkdownResult:
    markdown_with_citations = "# Citation Only\n\nCitation fallback body."


class _NoTimingsCrawlResult:
    success = True
    markdown = _MinimalMarkdownResult()
    metadata = {
        "title": "No Timing Page",
        "language": "en",
    }
    response_headers = {}
    links = {}
    media = {}
    html = "<html><body>No timing</body></html>"
    status_code = 200


class _FailureAsyncWebCrawler(_FakeAsyncWebCrawler):
    async def arun(self, *, url: str, config: _FakeCrawlerRunConfig) -> _FailureCrawlResult:
        type(self).last_url = url
        type(self).last_run_config = config
        return _FailureCrawlResult()


class _NoTimingsAsyncWebCrawler(_FakeAsyncWebCrawler):
    async def arun(self, *, url: str, config: _FakeCrawlerRunConfig) -> _NoTimingsCrawlResult:
        type(self).last_url = url
        type(self).last_run_config = config
        return _NoTimingsCrawlResult()


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

    engine = Crawl4AIParseEngine(
        {
            "enabled": True,
            "browser_config": {
                "headers": {"X-Runtime": "runtime"},
                "proxy": "http://runtime-proxy.local:8080",
                "storage_state": "C:/runtime/storage-state.json",
            },
            "crawler_run_config": {"simulate_user": True},
        }
    )
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
    browser_kwargs = _FakeAsyncWebCrawler.last_browser_config.kwargs
    headers = browser_kwargs.get("headers")
    assert browser_kwargs["browser_type"] == "chromium"
    assert browser_kwargs["enable_stealth"] is True
    assert isinstance(headers, dict)
    assert headers["X-Runtime"] == "runtime"
    assert browser_kwargs["proxy"] == "http://proxy.local:8080"
    assert browser_kwargs["light_mode"] is True
    assert _FakeAsyncWebCrawler.last_run_config is not None
    assert _FakeAsyncWebCrawler.last_run_config.kwargs["check_robots_txt"] is True
    assert _FakeAsyncWebCrawler.last_run_config.kwargs["screenshot"] is True
    assert _FakeAsyncWebCrawler.last_run_config.kwargs["pdf"] is True
    assert _FakeAsyncWebCrawler.last_run_config.kwargs["simulate_user"] is True
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


@pytest.mark.asyncio
async def test_crawl4ai_adapter_rejects_object_backed_sources() -> None:
    engine = Crawl4AIParseEngine({"enabled": True})

    with pytest.raises(ValidationError, match="does not support object-backed parse sources"):
        await engine.execute(
            EngineExecutionContext(
                request=ParseSyncRequest(
                    source=ParseSource(
                        input_kind=ParseInputKind.OBJECT,
                        object_id="obj_123",
                    )
                ),
                source=ParseSource(
                    input_kind=ParseInputKind.OBJECT,
                    object_id="obj_123",
                ),
            )
        )


@pytest.mark.asyncio
async def test_crawl4ai_adapter_surfaces_crawl_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        crawl4ai_adapter,
        "_load_crawl4ai_sdk",
        lambda: crawl4ai_adapter._Crawl4AISdk(
            async_web_crawler=_FailureAsyncWebCrawler,
            browser_config=_FakeBrowserConfig,
            crawler_run_config=_FakeCrawlerRunConfig,
            cache_mode=_FakeCacheMode,
        ),
    )

    engine = Crawl4AIParseEngine({"enabled": True})

    with pytest.raises(CortexError, match="crawler failed") as exc_info:
        await engine.execute(
            EngineExecutionContext(
                request=ParseSyncRequest(
                    source=ParseSource(
                        input_kind=ParseInputKind.URL,
                        url="https://example.com/failure",
                    )
                ),
                source=ParseSource(
                    input_kind=ParseInputKind.URL,
                    url="https://example.com/failure",
                ),
            )
        )

    assert exc_info.value.code == "crawl4ai_failed"


@pytest.mark.asyncio
async def test_crawl4ai_adapter_handles_missing_timing_fields_and_warns_on_unresolved_storage_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        crawl4ai_adapter,
        "_load_crawl4ai_sdk",
        lambda: crawl4ai_adapter._Crawl4AISdk(
            async_web_crawler=_NoTimingsAsyncWebCrawler,
            browser_config=_FakeBrowserConfig,
            crawler_run_config=_FakeCrawlerRunConfig,
            cache_mode=_FakeCacheMode,
        ),
    )
    monkeypatch.setattr(crawl4ai_adapter, "_crawl4ai_version", lambda: "0.8.test")

    engine = Crawl4AIParseEngine({"enabled": True})
    result = await engine.execute(
        EngineExecutionContext(
            request=ParseSyncRequest(
                source=ParseSource(
                    input_kind=ParseInputKind.URL,
                    url="https://example.com/no-timings",
                ),
                crawl=CrawlOptions(
                    browser_profile=BrowserProfile(
                        storage_state_ref="state/browser.json",
                    )
                ),
                output=ParseOutputOptions(llm_ready_mode=ParseLlmReadyMode.FIT_MARKDOWN),
            ),
            source=ParseSource(
                input_kind=ParseInputKind.URL,
                url="https://example.com/no-timings",
            ),
        )
    )

    assert result.markdown == "# Citation Only\n\nCitation fallback body."
    assert result.timings_ms == {}
    assert result.warnings == [
        "storage_state_ref is not resolved automatically yet; provide a concrete "
        "storage_state via engine_options.browser_config when needed."
    ]


@pytest.mark.asyncio
async def test_crawl4ai_adapter_maps_undetected_mode_for_newer_browser_config_signatures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        crawl4ai_adapter,
        "_load_crawl4ai_sdk",
        lambda: crawl4ai_adapter._Crawl4AISdk(
            async_web_crawler=_FakeAsyncWebCrawler,
            browser_config=_CompatBrowserConfig,
            crawler_run_config=_FakeCrawlerRunConfig,
            cache_mode=_FakeCacheMode,
        ),
    )

    engine = Crawl4AIParseEngine({"enabled": True})
    result = await engine.execute(
        EngineExecutionContext(
            request=ParseSyncRequest(
                source=ParseSource(
                    input_kind=ParseInputKind.URL,
                    url="https://example.com/compat",
                ),
                crawl=CrawlOptions(
                    browser_profile=BrowserProfile(
                        browser_type="chromium",
                        enable_stealth=True,
                        use_undetected_browser=True,
                    )
                ),
            ),
            source=ParseSource(
                input_kind=ParseInputKind.URL,
                url="https://example.com/compat",
            ),
        )
    )

    assert _FakeAsyncWebCrawler.last_browser_config is not None
    browser_kwargs = _FakeAsyncWebCrawler.last_browser_config.kwargs
    assert browser_kwargs["browser_type"] == "undetected"
    assert "use_undetected_browser" not in browser_kwargs
    assert "enable_stealth" not in browser_kwargs
    assert result.anti_bot_strategy == "stealth_plus_undetected"


@pytest.mark.asyncio
async def test_crawl4ai_adapter_uses_repo_local_base_directory_when_unset(
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
    monkeypatch.delenv("CRAWL4_AI_BASE_DIRECTORY", raising=False)
    monkeypatch.delenv("CRAWL4AI_BASE_DIRECTORY", raising=False)
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)

    engine = Crawl4AIParseEngine({"enabled": True})
    await engine.execute(
        EngineExecutionContext(
            request=ParseSyncRequest(
                source=ParseSource(
                    input_kind=ParseInputKind.URL,
                    url="https://example.com/cache-dir",
                )
            ),
            source=ParseSource(
                input_kind=ParseInputKind.URL,
                url="https://example.com/cache-dir",
            ),
        )
    )

    expected = (Path.cwd() / ".data" / "crawl4ai").resolve()
    expected_browsers = (Path.cwd() / ".data" / "playwright").resolve()
    assert Path(os.environ["CRAWL4_AI_BASE_DIRECTORY"]).resolve() == expected
    assert Path(os.environ["CRAWL4AI_BASE_DIRECTORY"]).resolve() == expected
    assert Path(_FakeAsyncWebCrawler.last_base_directory or "").resolve() == expected
    assert expected.exists()
    assert Path(os.environ["PLAYWRIGHT_BROWSERS_PATH"]).resolve() == expected_browsers
    assert expected_browsers.exists()


@pytest.mark.asyncio
async def test_crawl4ai_adapter_prefers_container_browser_env_over_runtime_config(
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
    env_browsers_path = str((Path.cwd() / ".data" / "playwright" / "container-env").resolve())
    configured_browsers_path = str(
        (Path.cwd() / ".data" / "playwright" / "runtime-config").resolve()
    )
    monkeypatch.setenv("CORTEX_PLAYWRIGHT_BROWSERS_PATH", env_browsers_path)
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)

    engine = Crawl4AIParseEngine(
        {
            "enabled": True,
            "playwright_browsers_path": configured_browsers_path,
        }
    )
    await engine.execute(
        EngineExecutionContext(
            request=ParseSyncRequest(
                source=ParseSource(
                    input_kind=ParseInputKind.URL,
                    url="https://example.com/container-browser-path",
                )
            ),
            source=ParseSource(
                input_kind=ParseInputKind.URL,
                url="https://example.com/container-browser-path",
            ),
        )
    )

    assert Path(os.environ["PLAYWRIGHT_BROWSERS_PATH"]).resolve() == Path(env_browsers_path)
    assert Path(configured_browsers_path).exists() is False
