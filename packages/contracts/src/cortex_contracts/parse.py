"""Parse API contracts."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

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
from .jobs import TelemetryContext
from .resources import AccessPolicy, AuditFields


class ParseSource(BaseModel):
    input_kind: ParseInputKind
    url: str | None = None
    object_id: str | None = None
    uri: str | None = None
    filename: str | None = None
    canonical_url: str | None = None
    referrer: str | None = None
    expected_content_type: str | None = None


class FallbackPolicy(BaseModel):
    enabled: bool = True
    mode: FallbackMode = FallbackMode.ORDERED
    on_error: FallbackOnError = FallbackOnError.TRY_NEXT
    max_engine_attempts: int = Field(default=3, ge=1, le=10)


class ParserSelection(BaseModel):
    profile_ref: str | None = None
    preferred_engine_key: str | None = None
    allowed_engines: list[str] = Field(default_factory=list)
    engine_template_ref: str | None = None
    engine_options: dict[str, Any] = Field(default_factory=dict)
    fallback_policy: FallbackPolicy = Field(default_factory=FallbackPolicy)


class BrowserProfile(BaseModel):
    browser_type: str = "chromium"
    headless: bool = True
    locale: str | None = None
    timezone_id: str | None = None
    viewport_width: int = Field(default=1280, ge=320)
    viewport_height: int = Field(default=900, ge=200)
    user_agent: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    proxy_ref: str | None = None
    enable_stealth: bool = False
    use_undetected_browser: bool = False
    use_persistent_context: bool = False
    session_id: str | None = None
    storage_state_ref: str | None = None


class CaptureOptions(BaseModel):
    return_markdown: bool = True
    return_clean_html: bool = False
    capture_pdf: bool = False
    capture_screenshot: bool = False
    force_viewport_screenshot: bool = False
    scan_full_page: bool = False
    fetch_ssl_certificate: bool = False
    capture_network_log: bool = False
    capture_console_log: bool = False
    flatten_shadow_dom: bool = False


class RetryPolicy(BaseModel):
    max_attempts: int = Field(default=3, ge=1, le=10)
    initial_backoff_ms: int = Field(default=500, ge=0)
    max_backoff_ms: int = Field(default=5000, ge=0)


class CrawlOptions(BaseModel):
    respect_robots_txt: bool = True
    browser_profile: BrowserProfile = Field(default_factory=BrowserProfile)
    content_selector: str | None = None
    excluded_selectors: list[str] = Field(default_factory=list)
    wait_for: str | None = None
    js_code: list[str] = Field(default_factory=list)
    remove_overlay_elements: bool = True
    cache_mode: str = "bypass"
    timeout_ms: int = Field(default=60_000, ge=1_000, le=600_000)
    capture: CaptureOptions = Field(default_factory=CaptureOptions)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)


class ParseNormalizationOptions(BaseModel):
    schema_version: str = "cortex.parse.v1"
    normalize_markdown: bool = True
    normalize_metadata: bool = True
    metadata_schema_ref: str | None = None
    infer_title: bool = True
    infer_language: bool = True
    include_page_metadata: bool = True
    preserve_source_blocks: bool = False
    deduplicate_whitespace: bool = True


class ChunkingOptions(BaseModel):
    enabled: bool = True
    strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC
    target_tokens: int = Field(default=512, ge=64, le=4096)
    overlap_tokens: int = Field(default=64, ge=0, le=1024)
    max_chunks: int = Field(default=256, ge=1, le=10_000)


class ParseOutputOptions(BaseModel):
    llm_ready_mode: ParseLlmReadyMode = ParseLlmReadyMode.MARKDOWN
    metadata_fields: list[str] = Field(default_factory=list)
    include_links: bool = True
    include_media: bool = True
    classify_tags: bool = True
    return_page_metadata: bool = False
    return_engine_payload_summary: bool = True
    chunking: ChunkingOptions = Field(default_factory=ChunkingOptions)


class ParsePersistenceOptions(BaseModel):
    persist_document: bool = True
    persist_artifacts: bool = True
    storage_policy: ParseStoragePolicy = ParseStoragePolicy.FULL_ARTIFACTS
    dataset_id: str | None = None
    object_prefix: str | None = None
    access_policy: AccessPolicy | None = None


class ParseSyncRequest(BaseModel):
    source: ParseSource
    parser: ParserSelection = Field(default_factory=ParserSelection)
    crawl: CrawlOptions = Field(default_factory=CrawlOptions)
    normalization: ParseNormalizationOptions = Field(default_factory=ParseNormalizationOptions)
    output: ParseOutputOptions = Field(default_factory=ParseOutputOptions)
    persistence: ParsePersistenceOptions = Field(default_factory=ParsePersistenceOptions)
    timeout_seconds: int = Field(default=45, ge=1, le=300)


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


class ParseEngineDescriptor(BaseModel):
    engine_key: str
    display_name: str
    engine_family: str
    deployment_mode: ParseEngineDeploymentMode
    status: ParseEngineStatus
    supported_source_types: list[str] = Field(default_factory=list)
    supported_formats: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)


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
