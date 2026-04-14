"""Core ORM models for the Cortex control plane."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import (
    Base,
    created_at_column,
    json_text_column,
    nullable_timestamp_column,
    updated_at_column,
)


class TenantModel(Base):
    __tablename__ = "tenants"

    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[str] = json_text_column()
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class ActorModel(Base):
    __tablename__ = "actors"
    __table_args__ = (
        UniqueConstraint("tenant_id", "actor_type", "actor_ref"),
        Index("idx_actors_tenant_ref", "tenant_id", "actor_ref"),
    )

    actor_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[str] = json_text_column()
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class PermissionModel(Base):
    __tablename__ = "permissions"

    permission_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    permission_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    action_name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str] = json_text_column()
    created_at: Mapped[datetime] = created_at_column()


class RoleModel(Base):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("tenant_id", "role_key"),)

    role_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    role_key: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    scope_level: Mapped[str] = mapped_column(String(32), nullable=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str] = json_text_column()
    created_by: Mapped[str | None] = mapped_column(ForeignKey("actors.actor_id"), nullable=True)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class RolePermissionModel(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[str] = mapped_column(
        ForeignKey("roles.role_id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_key: Mapped[str] = mapped_column(
        ForeignKey("permissions.permission_key"),
        primary_key=True,
    )
    effect: Mapped[str] = mapped_column(String(16), nullable=False, default="allow")


class ActorRoleBindingModel(Base):
    __tablename__ = "actor_role_bindings"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "actor_id",
            "role_id",
            "binding_scope",
            "resource_type",
            "resource_id",
        ),
        Index(
            "idx_actor_role_bindings_actor_tenant",
            "actor_id",
            "tenant_id",
            "binding_scope",
        ),
    )

    binding_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    actor_id: Mapped[str] = mapped_column(ForeignKey("actors.actor_id"), nullable=False)
    role_id: Mapped[str] = mapped_column(
        ForeignKey("roles.role_id", ondelete="CASCADE"),
        nullable=False,
    )
    binding_scope: Mapped[str] = mapped_column(String(32), nullable=False, default="tenant")
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime | None] = nullable_timestamp_column()
    metadata_json: Mapped[str] = json_text_column()
    created_by: Mapped[str | None] = mapped_column(ForeignKey("actors.actor_id"), nullable=True)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class AuthorizationPolicyModel(Base):
    __tablename__ = "authorization_policies"
    __table_args__ = (
        UniqueConstraint("tenant_id", "policy_key"),
        Index("idx_authorization_policies_tenant_status", "tenant_id", "status", "priority"),
    )

    policy_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    policy_key: Mapped[str] = mapped_column(String(128), nullable=False)
    effect: Mapped[str] = mapped_column(String(16), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_selector_json: Mapped[str] = json_text_column()
    resource_selector_json: Mapped[str] = json_text_column()
    condition_json: Mapped[str] = json_text_column()
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str] = json_text_column()
    created_by: Mapped[str | None] = mapped_column(ForeignKey("actors.actor_id"), nullable=True)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class StorageBucketModel(Base):
    __tablename__ = "storage_buckets"
    __table_args__ = (UniqueConstraint("tenant_id", "bucket_name"),)

    bucket_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    bucket_name: Mapped[str] = mapped_column(String(255), nullable=False)
    endpoint_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    region_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_hint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metadata_json: Mapped[str] = json_text_column()
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class ObjectModel(Base):
    __tablename__ = "objects"
    __table_args__ = (
        UniqueConstraint("bucket_id", "object_key"),
        Index("idx_objects_tenant_created_at", "tenant_id", "created_at"),
        Index("idx_objects_checksum", "checksum_sha256"),
        Index("idx_objects_tenant_access_level", "tenant_id", "access_level", "created_at"),
    )

    object_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    bucket_id: Mapped[str] = mapped_column(ForeignKey("storage_buckets.bucket_id"), nullable=False)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_uri: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    access_level: Mapped[str] = mapped_column(String(32), nullable=False, default="tenant_private")
    access_policy_json: Mapped[str] = json_text_column()
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="available")
    metadata_json: Mapped[str] = json_text_column()
    created_by: Mapped[str | None] = mapped_column(ForeignKey("actors.actor_id"), nullable=True)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class ObjectVersionModel(Base):
    __tablename__ = "object_versions"
    __table_args__ = (
        UniqueConstraint("object_id", "version_no"),
        Index("idx_object_versions_latest", "object_id", "is_latest", "version_no"),
    )

    object_version_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    object_id: Mapped[str] = mapped_column(
        ForeignKey("objects.object_id", ondelete="CASCADE"),
        nullable=False,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_version_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_latest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = created_at_column()


class DocumentModel(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("idx_documents_tenant_status", "tenant_id", "status"),
        Index("idx_documents_source_uri", "source_uri"),
        Index("idx_documents_tenant_access_level", "tenant_id", "access_level", "created_at"),
    )

    document_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_object_id: Mapped[str | None] = mapped_column(
        ForeignKey("objects.object_id"),
        nullable=True,
    )
    title: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_format: Mapped[str] = mapped_column(String(128), nullable=False)
    detected_mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_hash_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    access_level: Mapped[str] = mapped_column(String(32), nullable=False, default="tenant_private")
    access_policy_json: Mapped[str] = json_text_column()
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="parsed")
    metadata_json: Mapped[str] = json_text_column()
    audit_json: Mapped[str] = json_text_column()
    published_at: Mapped[datetime | None] = nullable_timestamp_column()
    created_by: Mapped[str | None] = mapped_column(ForeignKey("actors.actor_id"), nullable=True)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class DatasetModel(Base):
    __tablename__ = "datasets"
    __table_args__ = (
        UniqueConstraint("tenant_id", "dataset_key"),
        Index("idx_datasets_tenant_access_level", "tenant_id", "access_level", "created_at"),
    )

    dataset_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    dataset_key: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    retention_class: Mapped[str] = mapped_column(String(64), nullable=False, default="standard")
    access_level: Mapped[str] = mapped_column(String(32), nullable=False, default="tenant_private")
    access_policy_json: Mapped[str] = json_text_column()
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    metadata_json: Mapped[str] = json_text_column()
    created_by: Mapped[str | None] = mapped_column(ForeignKey("actors.actor_id"), nullable=True)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class JobModel(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "job_type", "idempotency_key"),
        Index("idx_jobs_tenant_status", "tenant_id", "status", "submitted_at"),
        Index("idx_jobs_target", "target_type", "target_id"),
        Index("idx_jobs_trace_id", "trace_id"),
    )

    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    operation_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    span_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    request_json: Mapped[str] = json_text_column()
    result_json: Mapped[str] = json_text_column()
    telemetry_context_json: Mapped[str] = json_text_column()
    deployment_context_json: Mapped[str] = json_text_column()
    experiment_context_json: Mapped[str] = json_text_column()
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_by: Mapped[str | None] = mapped_column(ForeignKey("actors.actor_id"), nullable=True)
    submitted_at: Mapped[datetime] = created_at_column()
    started_at: Mapped[datetime | None] = nullable_timestamp_column()
    heartbeat_at: Mapped[datetime | None] = nullable_timestamp_column()
    completed_at: Mapped[datetime | None] = nullable_timestamp_column()


class JobEventModel(Base):
    __tablename__ = "job_events"
    __table_args__ = (Index("idx_job_events_job_event_at", "job_id", "event_at"),)

    job_id: Mapped[str] = mapped_column(
        ForeignKey("jobs.job_id", ondelete="CASCADE"),
        primary_key=True,
    )
    sequence_no: Mapped[int] = mapped_column(Integer, primary_key=True)
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    span_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    details_json: Mapped[str] = json_text_column()
    event_at: Mapped[datetime] = created_at_column()


class AuthorizationDecisionModel(Base):
    __tablename__ = "authorization_decisions"
    __table_args__ = (
        Index("idx_authorization_decisions_trace_id", "trace_id", "created_at"),
        Index("idx_authorization_decisions_actor_created_at", "actor_id", "created_at"),
    )

    decision_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.tenant_id"), nullable=False)
    actor_id: Mapped[str] = mapped_column(ForeignKey("actors.actor_id"), nullable=False)
    permission_key: Mapped[str] = mapped_column(
        ForeignKey("permissions.permission_key"),
        nullable=False,
    )
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    effect: Mapped[str] = mapped_column(String(16), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    policy_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[str] = json_text_column()
    created_at: Mapped[datetime] = created_at_column()
