"""Repository implementations for core Cortex metadata entities."""

from collections.abc import Sequence
from typing import Any

from cortex_common import PaginationWindow, json_dumps, json_loads
from cortex_domain import (
    AccessLevel,
    ActorRecord,
    AuthorizationDecisionRecord,
    DatasetRecord,
    DecisionEffect,
    DocumentRecord,
    JobRecord,
    JobStatus,
    JobType,
    ObjectRecord,
    SourceType,
    StorageBucketRecord,
    TenantRecord,
)
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    ActorModel,
    AuthorizationDecisionModel,
    DatasetModel,
    DocumentModel,
    JobModel,
    ObjectModel,
    PermissionModel,
    StorageBucketModel,
    TenantModel,
)


def _json_object(value: dict[str, Any] | None) -> str:
    return json_dumps(value or {})


def _json_dict(value: str) -> dict[str, Any]:
    payload = json_loads(value)
    return payload if isinstance(payload, dict) else {}


def _tenant_from_model(model: TenantModel) -> TenantRecord:
    return TenantRecord(
        tenant_id=model.tenant_id,
        tenant_key=model.tenant_key,
        display_name=model.display_name,
        status=model.status,
        metadata=_json_dict(model.metadata_json),
    )


def _actor_from_model(model: ActorModel) -> ActorRecord:
    return ActorRecord(
        actor_id=model.actor_id,
        tenant_id=model.tenant_id,
        actor_type=model.actor_type,
        actor_ref=model.actor_ref,
        display_name=model.display_name,
        metadata=_json_dict(model.metadata_json),
    )


def _bucket_from_model(model: StorageBucketModel) -> StorageBucketRecord:
    return StorageBucketRecord(
        bucket_id=model.bucket_id,
        tenant_id=model.tenant_id,
        bucket_name=model.bucket_name,
        endpoint_url=model.endpoint_url,
        region_name=model.region_name,
        provider_hint=model.provider_hint,
        is_default=model.is_default,
        metadata=_json_dict(model.metadata_json),
    )


def _object_from_model(model: ObjectModel) -> ObjectRecord:
    return ObjectRecord(
        object_id=model.object_id,
        tenant_id=model.tenant_id,
        bucket_id=model.bucket_id,
        object_key=model.object_key,
        filename=model.filename,
        content_type=model.content_type,
        size_bytes=model.size_bytes,
        access_level=AccessLevel(model.access_level),
        access_policy=_json_dict(model.access_policy_json),
        metadata=_json_dict(model.metadata_json),
    )


def _document_from_model(model: DocumentModel) -> DocumentRecord:
    return DocumentRecord(
        document_id=model.document_id,
        tenant_id=model.tenant_id,
        source_type=SourceType(model.source_type),
        source_format=model.source_format,
        title=model.title,
        source_uri=model.source_uri,
        canonical_url=model.canonical_url,
        access_level=AccessLevel(model.access_level),
        access_policy=_json_dict(model.access_policy_json),
        metadata=_json_dict(model.metadata_json),
        audit=_json_dict(model.audit_json),
    )


def _dataset_from_model(model: DatasetModel) -> DatasetRecord:
    return DatasetRecord(
        dataset_id=model.dataset_id,
        tenant_id=model.tenant_id,
        dataset_key=model.dataset_key,
        display_name=model.display_name,
        description=model.description,
        access_level=AccessLevel(model.access_level),
        access_policy=_json_dict(model.access_policy_json),
        metadata=_json_dict(model.metadata_json),
    )


def _job_from_model(model: JobModel) -> JobRecord:
    return JobRecord(
        job_id=model.job_id,
        tenant_id=model.tenant_id,
        job_type=JobType(model.job_type),
        status=JobStatus(model.status),
        operation_name=model.operation_name,
        submitted_at=model.submitted_at,
        started_at=model.started_at,
        finished_at=model.completed_at,
        request_id=model.correlation_id,
        trace_id=model.trace_id,
    )


def _decision_from_model(model: AuthorizationDecisionModel) -> AuthorizationDecisionRecord:
    return AuthorizationDecisionRecord(
        decision_id=model.decision_id,
        tenant_id=model.tenant_id,
        actor_id=model.actor_id,
        permission_key=model.permission_key,
        effect=DecisionEffect(model.effect),
        reason_code=model.reason_code,
        resource_type=model.resource_type,
        resource_id=model.resource_id,
        trace_id=model.trace_id,
        request_id=model.request_id,
    )


class TenantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: TenantRecord) -> TenantRecord:
        model = TenantModel(
            tenant_id=record.tenant_id,
            tenant_key=record.tenant_key,
            display_name=record.display_name,
            status=record.status,
            metadata_json=_json_object(record.metadata),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _tenant_from_model(model)

    async def get(self, tenant_id: str) -> TenantRecord | None:
        model = await self._session.get(TenantModel, tenant_id)
        return None if model is None else _tenant_from_model(model)

    async def get_by_key(self, tenant_key: str) -> TenantRecord | None:
        result = await self._session.execute(
            select(TenantModel).where(TenantModel.tenant_key == tenant_key)
        )
        model = result.scalar_one_or_none()
        return None if model is None else _tenant_from_model(model)


class ActorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: ActorRecord) -> ActorRecord:
        model = ActorModel(
            actor_id=record.actor_id,
            tenant_id=record.tenant_id,
            actor_type=record.actor_type,
            actor_ref=record.actor_ref,
            display_name=record.display_name,
            metadata_json=_json_object(record.metadata),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _actor_from_model(model)

    async def get(self, actor_id: str) -> ActorRecord | None:
        model = await self._session.get(ActorModel, actor_id)
        return None if model is None else _actor_from_model(model)

    async def get_by_ref(
        self,
        tenant_id: str,
        *,
        actor_type: str,
        actor_ref: str,
    ) -> ActorRecord | None:
        result = await self._session.execute(
            select(ActorModel).where(
                ActorModel.tenant_id == tenant_id,
                ActorModel.actor_type == actor_type,
                ActorModel.actor_ref == actor_ref,
            )
        )
        model = result.scalar_one_or_none()
        return None if model is None else _actor_from_model(model)


class PermissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        permission_key: str,
        permission_kind: str,
        resource_type: str,
        action_name: str,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        model = PermissionModel(
            permission_key=permission_key,
            permission_kind=permission_kind,
            resource_type=resource_type,
            action_name=action_name,
            description=description,
            metadata_json=_json_object(metadata),
        )
        self._session.add(model)
        await self._session.flush()
        return model.permission_key


class StorageBucketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: StorageBucketRecord) -> StorageBucketRecord:
        model = StorageBucketModel(
            bucket_id=record.bucket_id,
            tenant_id=record.tenant_id,
            bucket_name=record.bucket_name,
            endpoint_url=record.endpoint_url,
            region_name=record.region_name,
            provider_hint=record.provider_hint,
            is_default=record.is_default,
            metadata_json=_json_object(record.metadata),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _bucket_from_model(model)

    async def get(self, bucket_id: str) -> StorageBucketRecord | None:
        model = await self._session.get(StorageBucketModel, bucket_id)
        return None if model is None else _bucket_from_model(model)

    async def get_default(self, tenant_id: str) -> StorageBucketRecord | None:
        result = await self._session.execute(
            select(StorageBucketModel).where(
                StorageBucketModel.tenant_id == tenant_id,
                StorageBucketModel.is_default.is_(True),
            )
        )
        model = result.scalar_one_or_none()
        return None if model is None else _bucket_from_model(model)


class ObjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: ObjectRecord) -> ObjectRecord:
        model = ObjectModel(
            object_id=record.object_id,
            tenant_id=record.tenant_id,
            bucket_id=record.bucket_id,
            object_key=record.object_key,
            filename=record.filename,
            content_type=record.content_type,
            size_bytes=record.size_bytes,
            access_level=record.access_level.value,
            access_policy_json=_json_object(record.access_policy),
            metadata_json=_json_object(record.metadata),
            status="available",
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _object_from_model(model)

    async def get(self, object_id: str) -> ObjectRecord | None:
        model = await self._session.get(ObjectModel, object_id)
        return None if model is None else _object_from_model(model)

    async def list_for_tenant(
        self,
        tenant_id: str,
        pagination: PaginationWindow | None = None,
    ) -> list[ObjectRecord]:
        window = pagination or PaginationWindow()
        result = await self._session.execute(
            select(ObjectModel)
            .where(ObjectModel.tenant_id == tenant_id)
            .order_by(desc(ObjectModel.created_at))
            .offset(window.offset)
            .limit(window.limit)
        )
        return [_object_from_model(model) for model in result.scalars().all()]


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: DocumentRecord) -> DocumentRecord:
        model = DocumentModel(
            document_id=record.document_id,
            tenant_id=record.tenant_id,
            source_type=record.source_type.value,
            source_uri=record.source_uri,
            canonical_url=record.canonical_url,
            title=record.title,
            source_format=record.source_format,
            access_level=record.access_level.value,
            access_policy_json=_json_object(record.access_policy),
            metadata_json=_json_object(record.metadata),
            audit_json=_json_object(record.audit),
            status="parsed",
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _document_from_model(model)

    async def get(self, document_id: str) -> DocumentRecord | None:
        model = await self._session.get(DocumentModel, document_id)
        return None if model is None else _document_from_model(model)

    async def list_for_tenant(
        self,
        tenant_id: str,
        pagination: PaginationWindow | None = None,
    ) -> Sequence[DocumentRecord]:
        window = pagination or PaginationWindow()
        result = await self._session.execute(
            select(DocumentModel)
            .where(DocumentModel.tenant_id == tenant_id)
            .order_by(desc(DocumentModel.created_at))
            .offset(window.offset)
            .limit(window.limit)
        )
        return [_document_from_model(model) for model in result.scalars().all()]


class DatasetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: DatasetRecord) -> DatasetRecord:
        model = DatasetModel(
            dataset_id=record.dataset_id,
            tenant_id=record.tenant_id,
            dataset_key=record.dataset_key,
            display_name=record.display_name,
            description=record.description,
            access_level=record.access_level.value,
            access_policy_json=_json_object(record.access_policy),
            metadata_json=_json_object(record.metadata),
            status="active",
            retention_class="standard",
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _dataset_from_model(model)

    async def get(self, dataset_id: str) -> DatasetRecord | None:
        model = await self._session.get(DatasetModel, dataset_id)
        return None if model is None else _dataset_from_model(model)

    async def get_by_key(self, tenant_id: str, dataset_key: str) -> DatasetRecord | None:
        result = await self._session.execute(
            select(DatasetModel).where(
                DatasetModel.tenant_id == tenant_id,
                DatasetModel.dataset_key == dataset_key,
            )
        )
        model = result.scalar_one_or_none()
        return None if model is None else _dataset_from_model(model)


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: JobRecord) -> JobRecord:
        model = JobModel(
            job_id=record.job_id,
            tenant_id=record.tenant_id,
            job_type=record.job_type.value,
            status=record.status.value,
            operation_name=record.operation_name,
            submitted_at=record.submitted_at,
            started_at=record.started_at,
            completed_at=record.finished_at,
            correlation_id=record.request_id,
            trace_id=record.trace_id,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _job_from_model(model)

    async def get(self, job_id: str) -> JobRecord | None:
        model = await self._session.get(JobModel, job_id)
        return None if model is None else _job_from_model(model)

    async def get_by_idempotency(
        self,
        tenant_id: str,
        *,
        job_type: JobType,
        idempotency_key: str,
    ) -> JobRecord | None:
        result = await self._session.execute(
            select(JobModel).where(
                JobModel.tenant_id == tenant_id,
                JobModel.job_type == job_type.value,
                JobModel.idempotency_key == idempotency_key,
            )
        )
        model = result.scalar_one_or_none()
        return None if model is None else _job_from_model(model)


class AuthorizationDecisionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: AuthorizationDecisionRecord) -> AuthorizationDecisionRecord:
        model = AuthorizationDecisionModel(
            decision_id=record.decision_id,
            tenant_id=record.tenant_id,
            actor_id=record.actor_id,
            permission_key=record.permission_key,
            resource_type=record.resource_type,
            resource_id=record.resource_id,
            effect=record.effect.value,
            reason_code=record.reason_code,
            trace_id=record.trace_id,
            request_id=record.request_id,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _decision_from_model(model)

    async def get(self, decision_id: str) -> AuthorizationDecisionRecord | None:
        model = await self._session.get(AuthorizationDecisionModel, decision_id)
        return None if model is None else _decision_from_model(model)

    async def list_for_actor(
        self,
        actor_id: str,
        pagination: PaginationWindow | None = None,
    ) -> Sequence[AuthorizationDecisionRecord]:
        window = pagination or PaginationWindow()
        result = await self._session.execute(
            select(AuthorizationDecisionModel)
            .where(AuthorizationDecisionModel.actor_id == actor_id)
            .order_by(desc(AuthorizationDecisionModel.created_at))
            .offset(window.offset)
            .limit(window.limit)
        )
        return [_decision_from_model(model) for model in result.scalars().all()]
