"""Parse API contracts."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from .enums import (
    ChunkingStrategy,
    FallbackMode,
    FallbackOnError,
    ParseAttemptStatus,
    ParseEngineDeploymentMode,
    ParseEngineStatus,
    ParseInputKind,
    ParseLlmReadyMode,
    ParseStoragePolicy,
)
from .jobs import JobAccepted, TelemetryContext
from .resources import AccessPolicy, AuditFields


class ParseSource(BaseModel):
    input_kind: ParseInputKind = Field(
        description=(
            "Required source kind. Use `url` for web fetches, `object` for previously uploaded "
            "objects, or `uri` for externally addressable files."
        ),
        examples=["url"],
    )
    url: str | None = Field(
        default=None,
        description=(
            "Source URL to fetch when `input_kind=url`. Best default: omit unless the request "
            "is URL-based."
        ),
        examples=["https://docs.cognee.ai/core-concepts/overview"],
    )
    object_id: str | None = Field(
        default=None,
        description=(
            "Uploaded storage object ID when `input_kind=object`. Best default: omit unless "
            "parsing a previously uploaded file."
        ),
        examples=["obj_3f6c1d5e9b1646b5a4eabdbf8b417bd3"],
    )
    uri: str | None = Field(
        default=None,
        description=(
            "External URI when `input_kind=uri`, for example `s3://bucket/key` or another "
            "connector-backed location. Best default: omit."
        ),
        examples=["s3://demo-bucket/manuals/architecture.pdf"],
    )
    filename: str | None = Field(
        default=None,
        description=(
            "Optional filename hint used for parser selection and metadata. "
            "Best default: omit to infer from URL or object metadata."
        ),
        examples=["architecture-overview.pdf"],
    )
    canonical_url: str | None = Field(
        default=None,
        description=(
            "Optional canonical URL stored as document provenance. "
            "Best default: omit to use the resolved final URL."
        ),
        examples=["https://docs.cognee.ai/core-concepts/overview"],
    )
    referrer: str | None = Field(
        default=None,
        description=(
            "Optional referrer header value for websites that gate content by referrer. "
            "Best default: omit."
        ),
        examples=["https://docs.cognee.ai/"],
    )
    expected_content_type: str | None = Field(
        default=None,
        description=(
            "Optional expected MIME type used for validation and engine routing. "
            "Best default: omit to let Cortex detect it."
        ),
        examples=["text/html"],
    )


class ParseSourceInput(BaseModel):
    uri: str | None = Field(
        default=None,
        description=(
            "Unified source locator for URL or external URI inputs. Best default: provide `uri` "
            "for public web pages or externally addressable files."
        ),
        examples=["https://docs.cognee.ai/core-concepts/overview"],
    )
    object_id: str | None = Field(
        default=None,
        description=(
            "Previously uploaded Cortex object identifier. Best default: omit unless parsing a "
            "stored object."
        ),
        examples=["obj_3f6c1d5e9b1646b5a4eabdbf8b417bd3"],
    )
    kind: ParseInputKind | None = Field(
        default=None,
        description=(
            "Optional explicit source-kind hint. Best default: omit and let Cortex infer from "
            "`uri` or `object_id`."
        ),
        examples=["url"],
    )
    filename: str | None = Field(
        default=None,
        description=(
            "Optional filename hint used for MIME/profile inference. Best default: omit to infer "
            "from the source."
        ),
        examples=["architecture-overview.pdf"],
    )
    mime_type: str | None = Field(
        default=None,
        description=(
            "Optional MIME hint used for engine-scene compilation. Best default: omit to let "
            "Cortex detect or infer it."
        ),
        examples=["application/pdf"],
    )
    canonical_url: str | None = Field(
        default=None,
        description=(
            "Optional canonical URL saved into document provenance. Best default: omit to use the "
            "resolved final URL."
        ),
        examples=["https://docs.cognee.ai/core-concepts/overview"],
    )

    @model_validator(mode="after")
    def _validate_locator(self) -> "ParseSourceInput":
        if not self.uri and not self.object_id:
            raise ValueError("Provide either `source.uri` or `source.object_id`.")
        if self.uri and self.object_id:
            raise ValueError("`source.uri` and `source.object_id` cannot be set together.")
        if self.kind is ParseInputKind.OBJECT and not self.object_id:
            raise ValueError("`source.kind=object` requires `source.object_id`.")
        if self.kind in {ParseInputKind.URL, ParseInputKind.URI} and not self.uri:
            raise ValueError("`source.kind=url|uri` requires `source.uri`.")
        if self.kind is ParseInputKind.URL and self.uri and not self.uri.startswith(
            ("http://", "https://")
        ):
            raise ValueError("`source.kind=url` requires an HTTP(S) `source.uri`.")
        return self


class FallbackPolicy(BaseModel):
    enabled: bool = Field(
        default=True,
        description="Whether Cortex may try another parser engine after the preferred one.",
    )
    mode: FallbackMode = Field(
        default=FallbackMode.ORDERED,
        description="Fallback strategy. Best default: `ordered` for predictable adapter order.",
    )
    on_error: FallbackOnError = Field(
        default=FallbackOnError.TRY_NEXT,
        description="How to react when an engine fails. Best default: `try_next`.",
    )
    max_engine_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description=(
            "Maximum number of engine attempts before the "
            "parse run fails. Best default: 3."
        ),
        examples=[3],
    )


class ParserSelection(BaseModel):
    profile_ref: str | None = Field(
        default=None,
        description=(
            "Optional parser profile key. Best default: `auto_default` in examples, or omit to "
            "let the service choose its runtime default profile."
        ),
        examples=["auto_default"],
    )
    preferred_engine_key: str | None = Field(
        default=None,
        description=(
            "Optional preferred parser engine key. Best "
            "default: omit unless you need a specific adapter."
        ),
        examples=["crawl4ai"],
    )
    allowed_engines: list[str] = Field(
        default_factory=list,
        description=(
            "Optional allow-list restricting which engines may run. Best default: empty list "
            "to allow profile/router selection."
        ),
        examples=[["crawl4ai", "jina_reader"]],
    )
    engine_template_ref: str | None = Field(
        default=None,
        description=(
            "Optional engine template reference for provider-specific runtime presets. "
            "Best default: omit."
        ),
        examples=["html_deep_crawl"],
    )
    engine_options: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Optional low-level engine overrides. Best "
            "default: empty object unless you know the adapter."
        ),
        examples=[{"extract_main_content": True}],
    )
    fallback_policy: FallbackPolicy = Field(
        default_factory=FallbackPolicy,
        description="Fallback behavior used if the preferred engine cannot finish successfully.",
    )


class BrowserProfile(BaseModel):
    browser_type: str = Field(
        default="chromium",
        description="Browser engine used by crawler-backed adapters. Best default: `chromium`.",
        examples=["chromium"],
    )
    headless: bool = Field(
        default=True,
        description="Run the browser headlessly. Best default: `true` for automation and servers.",
    )
    locale: str | None = Field(
        default=None,
        description="Optional browser locale. Best default: omit to use engine/runtime default.",
        examples=["en-US"],
    )
    timezone_id: str | None = Field(
        default=None,
        description=(
            "Optional browser timezone. Best default: omit "
            "unless rendering depends on timezone."
        ),
        examples=["Asia/Shanghai"],
    )
    viewport_width: int = Field(
        default=1280,
        ge=320,
        description="Viewport width in pixels. Best default: 1280.",
        examples=[1280],
    )
    viewport_height: int = Field(
        default=900,
        ge=200,
        description="Viewport height in pixels. Best default: 900.",
        examples=[900],
    )
    user_agent: str | None = Field(
        default=None,
        description="Optional user-agent override. Best default: omit.",
        examples=["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"],
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Optional browser request headers. Best default: empty object.",
        examples=[{"Accept-Language": "en-US,en;q=0.9"}],
    )
    proxy_ref: str | None = Field(
        default=None,
        description="Optional configured proxy profile reference. Best default: omit.",
        examples=["residential_pool_cn"],
    )
    enable_stealth: bool = Field(
        default=False,
        description="Enable anti-bot stealth measures when supported. Best default: `false`.",
    )
    use_undetected_browser: bool = Field(
        default=False,
        description="Use an undetected browser mode when supported. Best default: `false`.",
    )
    use_persistent_context: bool = Field(
        default=False,
        description="Reuse a persistent browser context across runs. Best default: `false`.",
    )
    session_id: str | None = Field(
        default=None,
        description="Optional session identifier for adapter/browser reuse. Best default: omit.",
        examples=["crawl-session-demo"],
    )
    storage_state_ref: str | None = Field(
        default=None,
        description="Optional reference to saved cookies/local storage state. Best default: omit.",
        examples=["file:runtime-test-data/auth-state.json"],
    )


class CaptureOptions(BaseModel):
    return_markdown: bool = Field(
        default=True,
        description="Return normalized Markdown output. Best default: `true`.",
    )
    return_clean_html: bool = Field(
        default=False,
        description="Also retain cleaned HTML as an artifact. Best default: `false`.",
    )
    capture_pdf: bool = Field(
        default=False,
        description="Capture a rendered PDF artifact when supported. Best default: `false`.",
    )
    capture_screenshot: bool = Field(
        default=False,
        description="Capture a screenshot artifact. Best default: `false`.",
    )
    force_viewport_screenshot: bool = Field(
        default=False,
        description=(
            "Force a viewport-only screenshot instead of a "
            "full-page capture. Best default: `false`."
        ),
    )
    scan_full_page: bool = Field(
        default=False,
        description="Scroll and scan the entire page before extraction. Best default: `false`.",
    )
    fetch_ssl_certificate: bool = Field(
        default=False,
        description="Capture an SSL certificate summary for HTTPS sources. Best default: `false`.",
    )
    capture_network_log: bool = Field(
        default=False,
        description="Persist a summarized network log when supported. Best default: `false`.",
    )
    capture_console_log: bool = Field(
        default=False,
        description="Persist browser console log snippets when supported. Best default: `false`.",
    )
    flatten_shadow_dom: bool = Field(
        default=False,
        description=(
            "Flatten shadow DOM content before extraction "
            "when supported. Best default: `false`."
        ),
    )


class RetryPolicy(BaseModel):
    max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retries for the crawl/fetch step. Best default: 3.",
        examples=[3],
    )
    initial_backoff_ms: int = Field(
        default=500,
        ge=0,
        description="Initial retry backoff in milliseconds. Best default: 500.",
        examples=[500],
    )
    max_backoff_ms: int = Field(
        default=5000,
        ge=0,
        description="Maximum retry backoff in milliseconds. Best default: 5000.",
        examples=[5000],
    )


class CrawlOptions(BaseModel):
    respect_robots_txt: bool = Field(
        default=True,
        description="Respect robots.txt when fetching public websites. Best default: `true`.",
    )
    browser_profile: BrowserProfile = Field(
        default_factory=BrowserProfile,
        description="Browser execution profile used by crawler-backed engines.",
    )
    content_selector: str | None = Field(
        default=None,
        description=(
            "Optional CSS selector used to narrow extraction to the main content region. "
            "Best default: omit."
        ),
        examples=["main"],
    )
    excluded_selectors: list[str] = Field(
        default_factory=list,
        description=(
            "Optional CSS selectors to exclude from the "
            "extracted content. Best default: empty list."
        ),
        examples=[["nav", ".cookie-banner"]],
    )
    wait_for: str | None = Field(
        default=None,
        description=(
            "Optional wait expression such as `css:.loaded` or `js:() => window.ready === true`. "
            "Best default: omit."
        ),
        examples=["css:main"],
    )
    js_code: list[str] = Field(
        default_factory=list,
        description=(
            "Optional JavaScript snippets executed after the page loads. Best default: empty list."
        ),
        examples=[["window.scrollTo(0, document.body.scrollHeight);"]],
    )
    remove_overlay_elements: bool = Field(
        default=True,
        description=(
            "Remove cookie banners and similar overlays when "
            "supported. Best default: `true`."
        ),
    )
    cache_mode: str = Field(
        default="bypass",
        description=(
            "Adapter cache mode. Best default: `bypass` for "
            "fresh fetches in tests and demos."
        ),
        examples=["bypass"],
    )
    timeout_ms: int = Field(
        default=60_000,
        ge=1_000,
        le=600_000,
        description="Fetch/render timeout in milliseconds. Best default: 60000.",
        examples=[60000],
    )
    capture: CaptureOptions = Field(
        default_factory=CaptureOptions,
        description="Artifact capture toggles for HTML, screenshots, PDFs, and diagnostics.",
    )
    retry_policy: RetryPolicy = Field(
        default_factory=RetryPolicy,
        description="Retry policy applied to fetch/crawl failures.",
    )


class ParseNormalizationOptions(BaseModel):
    schema_version: str = Field(
        default="cortex.parse.v1",
        description="Normalization schema version. Best default: `cortex.parse.v1`.",
    )
    normalize_markdown: bool = Field(
        default=True,
        description=(
            "Normalize headings, lists, whitespace, and block "
            "structure. Best default: `true`."
        ),
    )
    normalize_metadata: bool = Field(
        default=True,
        description=(
            "Normalize metadata into Cortex's standard "
            "document metadata shape. Best default: `true`."
        ),
    )
    metadata_schema_ref: str | None = Field(
        default=None,
        description="Optional metadata schema profile reference. Best default: omit.",
        examples=["metadata/default-web-page"],
    )
    infer_title: bool = Field(
        default=True,
        description=(
            "Infer a title when the source does not provide "
            "one cleanly. Best default: `true`."
        ),
    )
    infer_language: bool = Field(
        default=True,
        description="Infer language when it is missing from the source. Best default: `true`.",
    )
    include_page_metadata: bool = Field(
        default=True,
        description=(
            "Include page-level metadata such as URL, status, "
            "and fetch diagnostics. Best default: `true`."
        ),
    )
    preserve_source_blocks: bool = Field(
        default=False,
        description="Preserve raw source fragments in normalized output. Best default: `false`.",
    )
    deduplicate_whitespace: bool = Field(
        default=True,
        description="Collapse redundant whitespace during normalization. Best default: `true`.",
    )


class ChunkingOptions(BaseModel):
    enabled: bool = Field(
        default=True,
        description=(
            "Whether Cortex should emit chunking hints or "
            "stored chunks. Best default: `true`."
        ),
    )
    strategy: ChunkingStrategy = Field(
        default=ChunkingStrategy.SEMANTIC,
        description="Chunking strategy. Best default: `semantic` for LLM-ready content.",
    )
    target_tokens: int = Field(
        default=512,
        ge=64,
        le=4096,
        description="Target token count per chunk. Best default: 512.",
        examples=[512],
    )
    overlap_tokens: int = Field(
        default=64,
        ge=0,
        le=1024,
        description="Token overlap between adjacent chunks. Best default: 64.",
        examples=[64],
    )
    max_chunks: int = Field(
        default=256,
        ge=1,
        le=10_000,
        description="Maximum chunks emitted for one document. Best default: 256.",
        examples=[256],
    )


class ParseOutputOptions(BaseModel):
    llm_ready_mode: ParseLlmReadyMode = Field(
        default=ParseLlmReadyMode.MARKDOWN,
        description="Primary output format. Best default: `markdown`.",
    )
    metadata_fields: list[str] = Field(
        default_factory=list,
        description=(
            "Optional allow-list of metadata fields to emphasize in the result. "
            "Best default: empty list to keep the service default behavior."
        ),
        examples=[["title", "language", "summary"]],
    )
    include_links: bool = Field(
        default=True,
        description="Keep links in normalized output. Best default: `true`.",
    )
    include_media: bool = Field(
        default=True,
        description="Keep media references in normalized output. Best default: `true`.",
    )
    classify_tags: bool = Field(
        default=True,
        description="Ask the normalizer to infer category tags. Best default: `true`.",
    )
    return_page_metadata: bool = Field(
        default=False,
        description="Return expanded page metadata in the API payload. Best default: `false`.",
    )
    return_engine_payload_summary: bool = Field(
        default=True,
        description="Return a summarized engine payload/diagnostic view. Best default: `true`.",
    )
    chunking: ChunkingOptions = Field(
        default_factory=ChunkingOptions,
        description="Chunking preferences for downstream LLM or knowledge ingestion.",
    )


class ParsePersistenceOptions(BaseModel):
    persist_document: bool = Field(
        default=True,
        description=(
            "Persist the normalized document into Cortex "
            "metadata storage. Best default: `true`."
        ),
    )
    persist_artifacts: bool = Field(
        default=True,
        description=(
            "Persist generated artifacts such as markdown/"
            "html/PDF/screenshot refs. Best default: `true`."
        ),
    )
    storage_policy: ParseStoragePolicy = Field(
        default=ParseStoragePolicy.FULL_ARTIFACTS,
        description="How much parse output to persist. Best default: `full_artifacts`.",
    )
    dataset_id: str | None = Field(
        default=None,
        description=(
            "Optional dataset to associate with the persisted "
            "document. Best default: omit."
        ),
        examples=["dset_9558cfc9178444e4a4c60d5658db78f5"],
    )
    object_prefix: str | None = Field(
        default=None,
        description=(
            "Optional object storage prefix for persisted "
            "parse artifacts. Best default: omit."
        ),
        examples=["parsed/demo/"],
    )
    access_policy: AccessPolicy | None = Field(
        default=None,
        description=(
            "Optional access policy applied to persisted "
            "artifacts and documents. Best default: omit."
        ),
    )


class ParseSyncRequest(BaseModel):
    source: ParseSource = Field(description="Required source descriptor for the content to parse.")
    parser: ParserSelection = Field(
        default_factory=ParserSelection,
        description=(
            "Optional parser selection and fallback settings. "
            "Best default: use the built-in defaults."
        ),
    )
    crawl: CrawlOptions = Field(
        default_factory=CrawlOptions,
        description="Optional crawl/browser settings for URL-based parsing.",
    )
    normalization: ParseNormalizationOptions = Field(
        default_factory=ParseNormalizationOptions,
        description="Optional Markdown and metadata normalization controls.",
    )
    output: ParseOutputOptions = Field(
        default_factory=ParseOutputOptions,
        description="Optional output-shaping and chunking controls.",
    )
    persistence: ParsePersistenceOptions = Field(
        default_factory=ParsePersistenceOptions,
        description="Optional persistence controls for documents and artifacts.",
    )
    timeout_seconds: int = Field(
        default=45,
        ge=1,
        le=300,
        description="End-to-end parse timeout in seconds. Best default: 45.",
        examples=[45],
    )


class ParseSubmitRequest(BaseModel):
    sources: list[str] = Field(
        min_length=1,
        description=(
            "Required source locators. Each item may be an HTTP(S) URL, `s3://` URI, `file://` "
            "URI, raw Cortex storage object key such as "
            "`cortex-local/tenant_demo/obj_.../file.pdf`, or "
            "`cortex://objects/{object_id}` reference. For Cortex-managed S3/MinIO keys, Cortex "
            "extracts the `obj_...` segment and resolves a signed download URL automatically."
        ),
        examples=[
            [
                "https://docs.cognee.ai/core-concepts/overview",
                "s3://cortex-local/tenant_demo/obj_a3da967e3ca446cab3631bb7/bofa_note.pdf",
            ]
        ],
    )
    engine_id: str = Field(
        default="auto",
        min_length=1,
        description=(
            "Public parser engine identifier. Use `auto` to let Cortex choose the best active "
            "engine and scene per source; otherwise use `crawl4ai`, `jina_reader`, "
            "`llama_parse`, `markitdown`, or `docling`."
        ),
        examples=["auto"],
    )
    scene: str | None = Field(
        default=None,
        description=(
            "Optional high-level parse scene. Best default: omit to let Cortex select the engine's "
            "default scene. Typical values include `balanced`, `deep_web`, `authenticated_web`, "
            "`fast_extract`, `document_fidelity`, `document_ai`, or `lightweight`."
        ),
        examples=["deep_web"],
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_legacy_source_shapes(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        if "sources" not in normalized and "source" in normalized:
            normalized["sources"] = [normalized.pop("source")]
        elif isinstance(normalized.get("sources"), str):
            normalized["sources"] = [normalized["sources"]]
        raw_sources = normalized.get("sources")
        if isinstance(raw_sources, list):
            normalized["sources"] = [
                cls._normalize_source_locator(item)
                for item in raw_sources
            ]
        return normalized

    @staticmethod
    def _normalize_source_locator(value: Any) -> str:
        if isinstance(value, str):
            text = value.strip()
            if not text:
                raise ValueError("`sources` entries must not be empty.")
            return text
        if isinstance(value, dict):
            object_id = value.get("object_id")
            if isinstance(object_id, str) and object_id.strip():
                return f"cortex://objects/{object_id.strip()}"
            uri = value.get("uri") or value.get("url")
            if isinstance(uri, str) and uri.strip():
                return uri.strip()
        raise ValueError(
            "`sources` entries must be locator strings or legacy source objects with `uri`, `url`, "
            "or `object_id`."
        )


class WebhookConfig(BaseModel):
    url: str = Field(
        description="Required callback URL invoked on job lifecycle events.",
        examples=["https://example.com/hooks/cortex/parse"],
    )
    secret_ref: str | None = Field(
        default=None,
        description=(
            "Optional secret reference used to sign or "
            "authenticate webhook delivery. Best default: omit."
        ),
        examples=["vault:cortex/webhooks/parse"],
    )
    event_types: list[str] = Field(
        default_factory=list,
        description=(
            "Optional event types to send. Best default: "
            "empty list, which means the service default set."
        ),
        examples=[["job.succeeded", "job.failed"]],
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Optional static headers sent with the webhook. Best default: empty object.",
        examples=[{"X-Consumer": "knowledge-pipeline"}],
    )


class ParseJobRequest(ParseSyncRequest):
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Job priority where higher values are more urgent. Best default: 5.",
        examples=[5],
    )
    webhook: WebhookConfig | None = Field(
        default=None,
        description="Optional webhook callback configuration. Best default: omit.",
    )


class ParseJobSubmitRequest(ParseSubmitRequest):
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Job priority where higher values are more urgent. Best default: 5.",
        examples=[5],
    )
    webhook: WebhookConfig | None = Field(
        default=None,
        description="Optional webhook callback configuration. Best default: omit.",
    )


class StandardMetadata(BaseModel):
    title: str | None = None
    author: str | None = None
    publish_date: datetime | None = None
    language: str | None = None
    description: str | None = None
    summary: str | None = None
    keywords: list[str] = Field(default_factory=list)
    category_tags: list[str] = Field(default_factory=list)


class AppliedParseEngine(BaseModel):
    engine_key: str | None = None
    display_name: str | None = None
    engine_family: str | None = None
    engine_version: str | None = None
    profile_ref: str | None = None
    template_ref: str | None = None
    fallback_used: bool = False


class DocumentProvenance(BaseModel):
    input_kind: ParseInputKind | None = None
    fetched_at: datetime | None = None
    final_url: str | None = None
    http_status: int | None = Field(default=None, ge=100, le=599)
    content_length_bytes: int | None = Field(default=None, ge=0)
    parser_version: str | None = None
    content_hash_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class StorageObjectRef(BaseModel):
    object_id: str
    version_id: str | None = None
    bucket: str | None = None
    object_key: str


class SslCertificateSummary(BaseModel):
    issuer_common_name: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    fingerprint: str | None = None


class ParseArtifacts(BaseModel):
    markdown_object: StorageObjectRef | None = None
    raw_html_object: StorageObjectRef | None = None
    screenshot_object: StorageObjectRef | None = None
    pdf_object: StorageObjectRef | None = None
    ssl_certificate: SslCertificateSummary | None = None


class ParseEngineAttempt(BaseModel):
    attempt_no: int = Field(ge=1)
    engine_key: str
    status: ParseAttemptStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_code: str | None = None
    warning: str | None = None
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class ParseTimingSummary(BaseModel):
    fetch: int | None = Field(default=None, ge=0)
    render: int | None = Field(default=None, ge=0)
    normalize: int | None = Field(default=None, ge=0)
    total: int = Field(default=0, ge=0)


class ParseDiagnostics(BaseModel):
    selected_engine_key: str | None = None
    fallback_used: bool = False
    engine_attempts: list[ParseEngineAttempt] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    link_counts: dict[str, int] = Field(default_factory=dict)
    media_counts: dict[str, int] = Field(default_factory=dict)
    anti_bot_strategy: str | None = None
    used_proxy: bool | None = None
    timings_ms: ParseTimingSummary = Field(default_factory=ParseTimingSummary)
    telemetry: TelemetryContext | None = None


class ParsedDocument(BaseModel):
    document_id: str
    source_type: ParseInputKind
    source_format: str
    markdown: str
    audit: AuditFields
    source_url: str | None = None
    source_object_id: str | None = None
    source_uri: str | None = None
    canonical_url: str | None = None
    title: str | None = None
    language_code: str | None = None
    detected_mime_type: str | None = None
    category_tags: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    access_policy: AccessPolicy | None = None
    markdown_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    normalized_metadata: StandardMetadata = Field(default_factory=StandardMetadata)
    metadata: dict[str, Any] = Field(default_factory=dict)
    parser: AppliedParseEngine = Field(default_factory=AppliedParseEngine)
    provenance: DocumentProvenance = Field(default_factory=DocumentProvenance)


class ParseResult(BaseModel):
    job_id: str | None = None
    document: ParsedDocument
    artifacts: ParseArtifacts | None = None
    diagnostics: ParseDiagnostics
    telemetry: TelemetryContext | None = None


class ParseBatchResult(BaseModel):
    requested_sources: list[str] = Field(default_factory=list)
    engine_id: str
    scene: str | None = None
    results: list[ParseResult] = Field(default_factory=list)


class ParseBatchJobAccepted(BaseModel):
    requested_sources: list[str] = Field(default_factory=list)
    engine_id: str
    scene: str | None = None
    jobs: list[JobAccepted] = Field(default_factory=list)


class ParseEngineDescriptor(BaseModel):
    engine_key: str
    display_name: str
    engine_family: str
    deployment_mode: ParseEngineDeploymentMode
    status: ParseEngineStatus
    supported_source_types: list[str] = Field(default_factory=list)
    supported_formats: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    default_scene_id: str | None = None
    supported_scene_ids: list[str] = Field(default_factory=list)
    default_profile_ref: str | None = None


class ParseEngineList(BaseModel):
    engines: list[ParseEngineDescriptor] = Field(default_factory=list)


class ParserProfile(BaseModel):
    profile_ref: str
    display_name: str
    description: str | None = None
    routing_mode: str | None = None
    preferred_engine_key: str | None = None
    allowed_engines: list[str] = Field(default_factory=list)
    normalization_defaults: ParseNormalizationOptions = Field(
        default_factory=ParseNormalizationOptions
    )
    fallback_policy: FallbackPolicy = Field(default_factory=FallbackPolicy)


class ParserProfileList(BaseModel):
    profiles: list[ParserProfile] = Field(default_factory=list)
