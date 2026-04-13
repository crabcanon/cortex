"""Core domain entities."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .enums import AccessLevel, DecisionEffect, JobStatus, JobType, SourceType


@dataclass(slots=True)
class TenantRecord:
    tenant_id: str
    tenant_key: str
    display_name: str
    status: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ActorRecord:
    actor_id: str
    tenant_id: str
    actor_type: str
    actor_ref: str
    display_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StorageBucketRecord:
    bucket_id: str
    tenant_id: str
    bucket_name: str
    endpoint_url: str | None = None
    region_name: str | None = None
    provider_hint: str | None = None
    is_default: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ObjectRecord:
    object_id: str
    tenant_id: str
    bucket_id: str
    object_key: str
    filename: str
    content_type: str
    size_bytes: int
    access_level: AccessLevel = AccessLevel.TENANT_PRIVATE
    access_policy: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DocumentRecord:
    document_id: str
    tenant_id: str
    source_type: SourceType
    source_format: str
    title: str | None = None
    source_uri: str | None = None
    canonical_url: str | None = None
    markdown: str | None = None
    access_level: AccessLevel = AccessLevel.TENANT_PRIVATE
    access_policy: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    audit: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DatasetRecord:
    dataset_id: str
    tenant_id: str
    dataset_key: str
    display_name: str
    description: str | None = None
    access_level: AccessLevel = AccessLevel.TENANT_PRIVATE
    access_policy: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class JobRecord:
    job_id: str
    tenant_id: str
    job_type: JobType
    status: JobStatus
    operation_name: str
    submitted_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    request_id: str | None = None
    trace_id: str | None = None


@dataclass(slots=True)
class AuthorizationDecisionRecord:
    decision_id: str
    tenant_id: str
    actor_id: str
    permission_key: str
    effect: DecisionEffect
    reason_code: str
    resource_type: str | None = None
    resource_id: str | None = None
    trace_id: str | None = None
    request_id: str | None = None
