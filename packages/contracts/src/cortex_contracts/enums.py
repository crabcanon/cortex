"""Contract-level enums."""

from enum import StrEnum


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class AccessLevel(StrEnum):
    TENANT_PRIVATE = "tenant_private"
    TENANT_SHARED = "tenant_shared"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"


class UploadMode(StrEnum):
    SINGLE_PART = "single_part"
    MULTIPART = "multipart"


class UploadSessionStatus(StrEnum):
    PENDING_UPLOAD = "pending_upload"


class StorageObjectStatus(StrEnum):
    AVAILABLE = "available"
    ARCHIVED = "archived"
    DELETED = "deleted"


class DownloadDisposition(StrEnum):
    ATTACHMENT = "attachment"
    INLINE = "inline"


class ParseInputKind(StrEnum):
    URL = "url"
    OBJECT = "object"
    URI = "uri"


class ParseEngineDeploymentMode(StrEnum):
    LOCAL = "local"
    REMOTE = "remote"
    HYBRID = "hybrid"


class ParseEngineStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"


class ParseAttemptStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class FallbackMode(StrEnum):
    NONE = "none"
    ORDERED = "ordered"
    CAPABILITY_BASED = "capability_based"
    QUALITY_BASED = "quality_based"


class FallbackOnError(StrEnum):
    TRY_NEXT = "try_next"
    FAIL_FAST = "fail_fast"


class ParseLlmReadyMode(StrEnum):
    MARKDOWN = "markdown"
    FIT_MARKDOWN = "fit_markdown"


class ChunkingStrategy(StrEnum):
    NONE = "none"
    HEADING = "heading"
    SEMANTIC = "semantic"
    FIXED_TOKENS = "fixed_tokens"


class ParseStoragePolicy(StrEnum):
    METADATA_ONLY = "metadata_only"
    MARKDOWN_ONLY = "markdown_only"
    FULL_ARTIFACTS = "full_artifacts"


class JobType(StrEnum):
    PARSE = "parse"
    KNOWLEDGE_ADD = "knowledge_add"
    KNOWLEDGE_COGNIFY = "knowledge_cognify"
    KNOWLEDGE_MEMIFY = "knowledge_memify"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
