"""Core domain entities."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .enums import (
    AccessLevel,
    DecisionEffect,
    JobStatus,
    JobType,
    ObjectStatus,
    SourceType,
)


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
    checksum_sha256: str | None = None
    etag: str | None = None
    storage_class: str | None = None
    source_uri: str | None = None
    access_level: AccessLevel = AccessLevel.TENANT_PRIVATE
    access_policy: dict[str, Any] = field(default_factory=dict)
    status: ObjectStatus = ObjectStatus.AVAILABLE
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    upload_state: dict[str, Any] = field(default_factory=dict)
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class ObjectVersionRecord:
    object_version_id: str
    object_id: str
    version_no: int
    size_bytes: int
    provider_version_ref: str | None = None
    checksum_sha256: str | None = None
    etag: str | None = None
    is_latest: bool = True
    created_at: datetime | None = None


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
    priority: int = 5
    idempotency_key: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    started_at: datetime | None = None
    heartbeat_at: datetime | None = None
    finished_at: datetime | None = None
    request_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    request_payload: dict[str, Any] = field(default_factory=dict)
    result_payload: dict[str, Any] = field(default_factory=dict)
    telemetry_context: dict[str, Any] = field(default_factory=dict)
    deployment_context: dict[str, Any] = field(default_factory=dict)
    experiment_context: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None
    submitted_by: str | None = None


@dataclass(slots=True)
class JobEventRecord:
    job_id: str
    sequence_no: int
    level: str
    event_type: str
    event_at: datetime
    message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    trace_id: str | None = None
    span_id: str | None = None


@dataclass(slots=True)
class PermissionRecord:
    permission_key: str
    permission_kind: str
    resource_type: str
    action_name: str
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RoleRecord:
    role_id: str
    tenant_id: str
    role_key: str
    display_name: str
    scope_level: str
    is_builtin: bool = False
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_by: str | None = None


@dataclass(slots=True)
class RolePermissionRecord:
    role_id: str
    permission_key: str
    effect: DecisionEffect = DecisionEffect.ALLOW


@dataclass(slots=True)
class ActorRoleBindingRecord:
    binding_id: str
    tenant_id: str
    actor_id: str
    role_id: str
    binding_scope: str = "tenant"
    resource_type: str | None = None
    resource_id: str | None = None
    expires_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_by: str | None = None


@dataclass(slots=True)
class AuthorizationPolicyRecord:
    policy_id: str
    tenant_id: str
    policy_key: str
    effect: DecisionEffect
    priority: int = 100
    status: str = "active"
    subject_selector: dict[str, Any] = field(default_factory=dict)
    resource_selector: dict[str, Any] = field(default_factory=dict)
    condition: dict[str, Any] = field(default_factory=dict)
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_by: str | None = None


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
    policy_id: str | None = None
    trace_id: str | None = None
    request_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
