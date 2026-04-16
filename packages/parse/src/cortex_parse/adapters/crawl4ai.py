"""Crawl4AI-backed parse adapter."""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
from dataclasses import dataclass
from typing import Any

from cortex_common import ConfigError, CortexError, ValidationError, utc_now
from cortex_contracts import (
    ParseArtifacts,
    ParseEngineDeploymentMode,
    ParseEngineDescriptor,
    ParseEngineStatus,
    ParseInputKind,
    ParseLlmReadyMode,
    SslCertificateSummary,
)

from ..models import EngineExecutionContext, EngineExecutionResult, ParseEngineProtocol


@dataclass(slots=True)
class _Crawl4AISdk:
    async_web_crawler: type[Any]
    browser_config: type[Any]
    crawler_run_config: type[Any]
    cache_mode: type[Any] | None


def _load_crawl4ai_sdk() -> _Crawl4AISdk:
    try:
        module = importlib.import_module("crawl4ai")
    except ImportError as exc:  # pragma: no cover - depends on optional dependency
        raise ConfigError(
            "Crawl4AI is not installed. Install the `crawl4ai` package to enable this adapter."
        ) from exc

    browser_config = getattr(module, "BrowserConfig", None)
    crawler_run_config = getattr(module, "CrawlerRunConfig", None)
    if browser_config is None or crawler_run_config is None:
        async_configs = importlib.import_module("crawl4ai.async_configs")
        browser_config = async_configs.BrowserConfig
        crawler_run_config = async_configs.CrawlerRunConfig

    return _Crawl4AISdk(
        async_web_crawler=module.AsyncWebCrawler,
        browser_config=browser_config,
        crawler_run_config=crawler_run_config,
        cache_mode=getattr(module, "CacheMode", None),
    )


def _crawl4ai_available() -> bool:
    try:
        _load_crawl4ai_sdk()
    except Exception:
        return False
    return True


def _crawl4ai_version() -> str | None:
    try:
        return importlib.metadata.version("crawl4ai")
    except importlib.metadata.PackageNotFoundError:  # pragma: no cover - optional dependency
        return None


class Crawl4AIParseEngine(ParseEngineProtocol):
    """Map Cortex parse requests to Crawl4AI's browser and crawler configs."""

    def __init__(self, config: dict[str, object] | None = None) -> None:
        self._config = dict(config) if isinstance(config, dict) else {}
        enabled = bool(self._config.get("enabled", True))
        available = _crawl4ai_available()
        self._descriptor = ParseEngineDescriptor(
            engine_key="crawl4ai",
            display_name="Crawl4AI",
            engine_family="web_interactive",
            deployment_mode=ParseEngineDeploymentMode.LOCAL,
            status=(
                ParseEngineStatus.ACTIVE
                if enabled and available
                else ParseEngineStatus.DISABLED
            ),
            supported_source_types=[
                ParseInputKind.URL.value,
                ParseInputKind.URI.value,
                ParseInputKind.OBJECT.value,
            ],
            supported_formats=["text/html", "application/xhtml+xml"],
            capabilities=[
                "markdown",
                "browser",
                "javascript",
                "screenshot",
                "pdf",
                "ssl_certificate",
                "session_reuse",
                "proxy",
                "robots_txt",
                "network_capture",
                "console_capture",
            ],
        )

    @property
    def descriptor(self) -> ParseEngineDescriptor:
        return self._descriptor

    async def execute(self, context: EngineExecutionContext) -> EngineExecutionResult:
        source_url = context.source.url or context.source.uri
        if source_url is None:
            raise ValidationError("Crawl4AI requires `source.url` or `source.uri`.")

        sdk = _load_crawl4ai_sdk()
        browser_config = sdk.browser_config(**self._browser_kwargs(context))
        run_config = sdk.crawler_run_config(**self._run_kwargs(context, sdk.cache_mode))

        async with sdk.async_web_crawler(config=browser_config) as crawler:
            result = await crawler.arun(url=source_url, config=run_config)

        if not getattr(result, "success", False):
            raise CortexError(
                code="crawl4ai_failed",
                detail=getattr(result, "error_message", None) or "Crawl4AI crawl failed.",
                status_code=502,
            )

        markdown = self._resolve_markdown(
            getattr(result, "markdown", None),
            context.request.output.llm_ready_mode,
        )
        metadata = self._metadata_payload(getattr(result, "metadata", None))
        raw_metadata = self._raw_metadata_payload(result)
        parser_version = _crawl4ai_version()
        content_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
        response_headers = getattr(result, "response_headers", None) or {}
        content_length = self._content_length(result, response_headers)

        return EngineExecutionResult(
            markdown=markdown,
            source_format="text/html",
            detected_mime_type=self._header_value(response_headers, "content-type") or "text/html",
            title=self._string_value(metadata.get("title")),
            metadata=metadata,
            raw_metadata=raw_metadata,
            warnings=self._warnings(context, result),
            link_counts=self._count_groups(getattr(result, "links", None)),
            media_counts=self._count_groups(getattr(result, "media", None)),
            anti_bot_strategy=self._anti_bot_strategy(context),
            used_proxy=bool(
                context.request.crawl.browser_profile.proxy_ref
                or context.engine_options.get("proxy")
                or context.engine_options.get("proxy_config")
                or self._mapping(self._config.get("browser_config")).get("proxy")
            ),
            timings_ms=self._timings(result, metadata),
            fetched_at=utc_now(),
            final_url=(
                self._string_value(getattr(result, "redirected_url", None))
                or self._string_value(getattr(result, "url", None))
                or source_url
            ),
            http_status=self._http_status(result),
            content_length_bytes=content_length,
            parser_version=parser_version,
            content_hash_sha256=content_hash,
            artifacts=self._artifacts(result),
            engine_payload_summary=self._payload_summary(result),
        )

    def _browser_kwargs(self, context: EngineExecutionContext) -> dict[str, Any]:
        browser_profile = context.request.crawl.browser_profile
        runtime_browser_config = self._mapping(self._config.get("browser_config"))
        runtime_headers = self._mapping(runtime_browser_config.get("headers"))
        browser_kwargs: dict[str, Any] = {
            **runtime_browser_config,
            "browser_type": browser_profile.browser_type,
            "headless": browser_profile.headless,
            "viewport_width": browser_profile.viewport_width,
            "viewport_height": browser_profile.viewport_height,
            "headers": {
                **{str(key): str(value) for key, value in runtime_headers.items()},
                **dict(browser_profile.headers),
            },
            "enable_stealth": browser_profile.enable_stealth,
            "use_undetected_browser": browser_profile.use_undetected_browser,
            "use_persistent_context": browser_profile.use_persistent_context,
        }
        if browser_profile.user_agent:
            browser_kwargs["user_agent"] = browser_profile.user_agent
        elif "user_agent" in runtime_browser_config:
            browser_kwargs["user_agent"] = runtime_browser_config["user_agent"]
        if browser_profile.proxy_ref:
            browser_kwargs["proxy"] = browser_profile.proxy_ref
        elif "proxy" not in browser_kwargs and isinstance(self._config.get("proxy"), str):
            browser_kwargs["proxy"] = self._config["proxy"]
        override_browser = self._mapping(context.engine_options.get("browser_config"))
        override_headers = self._mapping(override_browser.pop("headers", None))
        browser_kwargs.update(override_browser)
        if override_headers:
            browser_kwargs["headers"] = {
                **self._mapping(browser_kwargs.get("headers")),
                **override_headers,
            }
        return browser_kwargs

    def _run_kwargs(
        self,
        context: EngineExecutionContext,
        cache_mode_enum: type[Any] | None,
    ) -> dict[str, Any]:
        crawl = context.request.crawl
        browser_profile = crawl.browser_profile
        capture = crawl.capture
        run_kwargs: dict[str, Any] = {
            **self._mapping(self._config.get("crawler_run_config")),
            "css_selector": crawl.content_selector,
            "excluded_selector": ", ".join(crawl.excluded_selectors)
            if crawl.excluded_selectors
            else None,
            "wait_for": crawl.wait_for,
            "js_code": crawl.js_code or None,
            "remove_overlay_elements": crawl.remove_overlay_elements,
            "cache_mode": Crawl4AIParseEngine._cache_mode_value(crawl.cache_mode, cache_mode_enum),
            "page_timeout": crawl.timeout_ms,
            "check_robots_txt": crawl.respect_robots_txt,
            "locale": browser_profile.locale,
            "timezone_id": browser_profile.timezone_id,
            "fetch_ssl_certificate": capture.fetch_ssl_certificate,
            "screenshot": capture.capture_screenshot,
            "force_viewport_screenshot": capture.force_viewport_screenshot,
            "scan_full_page": capture.scan_full_page,
            "pdf": capture.capture_pdf,
            "flatten_shadow_dom": capture.flatten_shadow_dom,
            "capture_network_requests": capture.capture_network_log,
            "capture_console_messages": capture.capture_console_log,
            "session_id": browser_profile.session_id,
            "verbose": False,
        }
        run_kwargs.update(self._mapping(context.engine_options.get("crawler_run_config")))
        return {key: value for key, value in run_kwargs.items() if value is not None}

    @staticmethod
    def _cache_mode_value(cache_mode: str, cache_mode_enum: type[Any] | None) -> Any:
        if cache_mode_enum is None:
            return cache_mode
        candidate = getattr(cache_mode_enum, cache_mode.upper(), None)
        return candidate if candidate is not None else cache_mode

    @staticmethod
    def _resolve_markdown(markdown_payload: Any, llm_ready_mode: ParseLlmReadyMode) -> str:
        if isinstance(markdown_payload, str):
            return markdown_payload

        preferred = (
            ["fit_markdown", "raw_markdown", "markdown_with_citations", "references_markdown"]
            if llm_ready_mode is ParseLlmReadyMode.FIT_MARKDOWN
            else ["raw_markdown", "markdown_with_citations", "references_markdown", "fit_markdown"]
        )
        for field_name in preferred:
            value = Crawl4AIParseEngine._nested_value(markdown_payload, field_name)
            if isinstance(value, str) and value.strip():
                return value

        raise CortexError(
            code="crawl4ai_missing_markdown",
            detail="Crawl4AI completed without producing Markdown output.",
            status_code=502,
        )

    @staticmethod
    def _metadata_payload(metadata: Any) -> dict[str, Any]:
        return metadata if isinstance(metadata, dict) else {}

    @staticmethod
    def _raw_metadata_payload(result: Any) -> dict[str, Any]:
        raw: dict[str, Any] = {}
        for field_name in (
            "response_headers",
            "downloaded_files",
            "tables",
            "network_requests",
            "console_messages",
            "js_execution_result",
            "session_id",
            "redirected_url",
            "redirected_status_code",
            "cleaned_html",
            "html",
        ):
            value = getattr(result, field_name, None)
            if value:
                raw[field_name] = value
        return raw

    def _warnings(self, context: EngineExecutionContext, result: Any) -> list[str]:
        warnings: list[str] = []
        storage_state_ref = context.request.crawl.browser_profile.storage_state_ref
        runtime_storage_state = self._mapping(self._config.get("browser_config")).get(
            "storage_state"
        )
        if storage_state_ref and not runtime_storage_state:
            warnings.append(
                "storage_state_ref is not resolved automatically yet; provide a concrete "
                "storage_state via engine_options.browser_config when needed."
            )
        if getattr(result, "redirected_url", None):
            warnings.append("source redirected during crawl")
        return warnings

    @staticmethod
    def _count_groups(groups: Any) -> dict[str, int]:
        if not isinstance(groups, dict):
            return {}
        counts: dict[str, int] = {}
        for key, value in groups.items():
            counts[str(key)] = len(value) if isinstance(value, list) else 0
        return counts

    @staticmethod
    def _timings(result: Any, metadata: dict[str, Any]) -> dict[str, int]:
        if isinstance(metadata.get("timings_ms"), dict):
            return {
                str(key): int(value)
                for key, value in metadata["timings_ms"].items()
                if isinstance(value, int | float)
            }
        dispatch_result = getattr(result, "dispatch_result", None)
        if isinstance(dispatch_result, dict):
            return {
                str(key): int(value)
                for key, value in dispatch_result.items()
                if isinstance(value, int | float)
            }
        return {}

    @staticmethod
    def _http_status(result: Any) -> int | None:
        status = getattr(result, "status_code", None)
        if isinstance(status, int):
            return status
        redirected = getattr(result, "redirected_status_code", None)
        return redirected if isinstance(redirected, int) else None

    @staticmethod
    def _content_length(result: Any, headers: dict[str, Any]) -> int | None:
        header_length = Crawl4AIParseEngine._header_value(headers, "content-length")
        if header_length and header_length.isdigit():
            return int(header_length)
        html = getattr(result, "html", None)
        if isinstance(html, str):
            return len(html.encode("utf-8"))
        return None

    @staticmethod
    def _artifacts(result: Any) -> ParseArtifacts:
        certificate = getattr(result, "ssl_certificate", None)
        ssl_summary: SslCertificateSummary | None = None
        if certificate is not None:
            ssl_summary = SslCertificateSummary(
                issuer_common_name=Crawl4AIParseEngine._first_value(
                    Crawl4AIParseEngine._nested_value(certificate, "issuer_common_name"),
                    Crawl4AIParseEngine._nested_value(certificate, "issuer", "commonName"),
                    Crawl4AIParseEngine._nested_value(certificate, "issuer", "common_name"),
                ),
                valid_from=Crawl4AIParseEngine._nested_value(certificate, "valid_from"),
                valid_until=Crawl4AIParseEngine._nested_value(certificate, "valid_until"),
                fingerprint=Crawl4AIParseEngine._nested_value(certificate, "fingerprint"),
            )
        return ParseArtifacts(ssl_certificate=ssl_summary)

    @staticmethod
    def _payload_summary(result: Any) -> dict[str, Any]:
        network_requests = getattr(result, "network_requests", None)
        console_messages = getattr(result, "console_messages", None)
        tables = getattr(result, "tables", None)
        return {
            "captured_screenshot": bool(getattr(result, "screenshot", None)),
            "captured_pdf": bool(getattr(result, "pdf", None)),
            "captured_network_requests": len(network_requests)
            if isinstance(network_requests, list)
            else 0,
            "captured_console_messages": len(console_messages)
            if isinstance(console_messages, list)
            else 0,
            "table_count": len(tables) if isinstance(tables, list) else 0,
            "downloaded_files_count": len(getattr(result, "downloaded_files", None) or []),
        }

    @staticmethod
    def _anti_bot_strategy(context: EngineExecutionContext) -> str | None:
        browser_profile = context.request.crawl.browser_profile
        if browser_profile.use_undetected_browser:
            return "undetected_browser"
        if browser_profile.enable_stealth:
            return "stealth"
        return None

    @staticmethod
    def _mapping(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _header_value(headers: dict[str, Any], target_name: str) -> str | None:
        for name, value in headers.items():
            if str(name).lower() == target_name:
                text = Crawl4AIParseEngine._string_value(value)
                if text:
                    return text
        return None

    @staticmethod
    def _nested_value(root: Any, *path: str) -> Any:
        if root is None:
            return None
        current = root
        for key in path:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                current = getattr(current, key, None)
            if current is None:
                return None
        return current

    @staticmethod
    def _string_value(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _first_value(*values: Any) -> Any:
        for value in values:
            if value is not None:
                return value
        return None
