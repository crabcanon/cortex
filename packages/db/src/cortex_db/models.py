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
