"""Core domain enums."""

from enum import StrEnum


class AccessLevel(StrEnum):
    TENANT_PRIVATE = "tenant_private"
    TENANT_SHARED = "tenant_shared"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"


class ObjectStatus(StrEnum):
    PENDING_UPLOAD = "pending_upload"
    AVAILABLE = "available"
    ARCHIVED = "archived"
    DELETED = "deleted"


class UploadMode(StrEnum):
    SINGLE_PART = "single_part"
    MULTIPART = "multipart"


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


class SourceType(StrEnum):
    URL = "url"
    OBJECT = "object"
    TEXT = "text"
    URI = "uri"


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


class DecisionEffect(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
