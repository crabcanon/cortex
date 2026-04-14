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
