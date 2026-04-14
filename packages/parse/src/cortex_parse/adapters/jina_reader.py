"""Jina Reader HTTP adapter."""

from __future__ import annotations

import hashlib
from urllib.parse import urlparse

import httpx
from cortex_common import ValidationError, utc_now
from cortex_contracts import (
    ParseEngineDeploymentMode,
    ParseEngineDescriptor,
    ParseEngineStatus,
    ParseInputKind,
)

from ..models import EngineExecutionContext, EngineExecutionResult, ParseEngineProtocol


class JinaReaderParseEngine(ParseEngineProtocol):
    """Use Jina Reader's `r.jina.ai` endpoint to convert public URLs to Markdown."""

    def __init__(self) -> None:
        self._descriptor = ParseEngineDescriptor(
            engine_key="jina_reader",
            display_name="Jina Reader",
            engine_family="web_remote",
            deployment_mode=ParseEngineDeploymentMode.REMOTE,
            status=ParseEngineStatus.ACTIVE,
            supported_source_types=[ParseInputKind.URL.value, ParseInputKind.URI.value],
            supported_formats=["text/html", "application/pdf"],
            capabilities=[
                "markdown",
                "remote_fetch",
                "readerlm_v2",
                "css_extract",
                "json_response",
            ],
        )

    @property
    def descriptor(self) -> ParseEngineDescriptor:
        return self._descriptor

    async def execute(self, context: EngineExecutionContext) -> EngineExecutionResult:
        target_url = context.source.url or context.source.uri
        if target_url is None:
            raise ValidationError("Jina Reader requires `source.url` or `source.uri`.")
        if not target_url.startswith(("http://", "https://")):
            raise ValidationError("Jina Reader can only parse publicly reachable HTTP(S) URLs.")

        base_url = str(context.engine_options.get("base_url", "https://r.jina.ai")).rstrip("/")
        reader_url = f"{base_url}/{target_url}"
        headers = self._headers(context)
        timeout_seconds = float(
            context.engine_options.get("timeout_seconds", context.request.timeout_seconds)
        )
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(reader_url, headers=headers)
            response.raise_for_status()

        markdown = response.text.strip()
        title = self._extract_title(markdown, target_url)
        content_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
        return EngineExecutionResult(
            markdown=markdown,
            source_format=context.source.expected_content_type or "text/html",
            detected_mime_type=response.headers.get("content-type"),
            title=title,
            metadata={
                "title": title,
                "reader_url": reader_url,
                "source_host": urlparse(target_url).netloc,
            },
            raw_metadata={"response_headers": dict(response.headers)},
            fetched_at=utc_now(),
            final_url=target_url,
            http_status=response.status_code,
            content_length_bytes=len(response.content),
            parser_version="jina-reader-http",
            content_hash_sha256=content_hash,
            engine_payload_summary={
                "base_url": base_url,
                "used_readerlm_v2": headers.get("x-respond-with") == "readerlm-v2",
            },
        )

    @staticmethod
    def _headers(context: EngineExecutionContext) -> dict[str, str]:
        headers = {"Accept": "text/plain"}
        api_key = context.engine_options.get("api_key")
        if isinstance(api_key, str) and api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        if context.engine_options.get("use_readerlm_v2"):
            headers["x-respond-with"] = "readerlm-v2"
        if context.request.crawl.content_selector:
            headers["x-target-selector"] = context.request.crawl.content_selector
        if context.request.crawl.wait_for:
            headers["x-wait-for-selector"] = context.request.crawl.wait_for
        if context.request.crawl.excluded_selectors:
            headers["x-remove-selector"] = ", ".join(context.request.crawl.excluded_selectors)
        headers.update(
            {
                str(key): str(value)
                for key, value in context.engine_options.get("headers", {}).items()
            }
            if isinstance(context.engine_options.get("headers"), dict)
            else {}
        )
        return headers

    @staticmethod
    def _extract_title(markdown: str, target_url: str) -> str:
        for line in markdown.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                title = stripped.lstrip("#").strip()
                if title:
                    return title
        parsed = urlparse(target_url)
        return parsed.path.rsplit("/", 1)[-1] or parsed.netloc
