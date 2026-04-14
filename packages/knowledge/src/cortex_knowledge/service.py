"""Knowledge dataset services."""

from __future__ import annotations

from typing import Any

from cortex_common import (
    CortexError,
    NotFoundError,
    ValidationError,
    new_prefixed_id,
    utc_now,
)
from cortex_contracts import (
    AccessLevel as ContractAccessLevel,
)
from cortex_contracts import (
    AccessPolicy,
    AuditFields,
    DatasetCounters,
    DatasetRetentionClass,
    KnowledgeDataset,
    KnowledgeDatasetCreateRequest,
    KnowledgeDatasetStatus,
)
from cortex_db import CortexUnitOfWork
from cortex_domain import AccessLevel, DatasetRecord
from cortex_observability import MetricsFacade
from opentelemetry import trace

from .models import CogneeRuntimeProtocol


class KnowledgeDatasetService:
    """Create and fetch knowledge datasets while keeping Cognee optional."""

    def __init__(self, runtime: CogneeRuntimeProtocol) -> None:
        self._runtime = runtime
        self._tracer = trace.get_tracer("cortex.knowledge")
        self._metrics = MetricsFacade("cortex.knowledge")

    @property
    def runtime(self) -> CogneeRuntimeProtocol:
        return self._runtime

    async def create_dataset(
        self,
        *,
        uow: CortexUnitOfWork,
        caller: Any,
        request: KnowledgeDatasetCreateRequest,
    ) -> KnowledgeDataset:
        with self._tracer.start_as_current_span("knowledge.dataset.create") as span:
            existing = await uow.datasets.get_by_key(caller.tenant_id, request.dataset_key)
            if existing is not None:
                raise CortexError(
                    code="dataset_conflict",
                    detail=f"Dataset key `{request.dataset_key}` already exists.",
                    status_code=409,
                )

            owner_actor_id = caller.actor_id or caller.subject
            access_policy = self._normalize_access_policy(
                request.access_policy,
                owner_actor_id=owner_actor_id,
            )
            record = await uow.datasets.add(
                DatasetRecord(
                    dataset_id=new_prefixed_id("dataset"),
                    tenant_id=caller.tenant_id,
                    dataset_key=request.dataset_key,
                    display_name=request.display_name,
                    description=request.description,
                    retention_class=request.retention_class.value,
                    access_level=self._domain_access_level(access_policy),
                    access_policy=access_policy.model_dump(mode="json"),
                    metadata=dict(request.metadata),
                    tags=list(dict.fromkeys(request.tags)),
                    status=KnowledgeDatasetStatus.ACTIVE.value,
                    created_by=owner_actor_id,
                )
            )
            span.set_attribute("cortex.dataset.id", record.dataset_id)
            span.set_attribute("cortex.knowledge.runtime", self._runtime.descriptor.provider_key)
            self._metrics.counter(
                "cortex.knowledge.datasets.created",
                description="Count of created knowledge datasets.",
            ).add(1)
            return self._to_contract(record)

    async def get_dataset(
        self,
        *,
        uow: CortexUnitOfWork,
        dataset_id: str,
    ) -> KnowledgeDataset:
        with self._tracer.start_as_current_span("knowledge.dataset.get") as span:
            record = await self.get_dataset_record(uow=uow, dataset_id=dataset_id)
            span.set_attribute("cortex.dataset.id", record.dataset_id)
            return self._to_contract(record)

    async def get_dataset_record(
        self,
        *,
        uow: CortexUnitOfWork,
        dataset_id: str,
    ) -> DatasetRecord:
        record = await uow.datasets.get(dataset_id)
        if record is None:
            raise NotFoundError(f"Dataset `{dataset_id}` was not found.")
        return record

    async def resolve_dataset(
        self,
        *,
        uow: CortexUnitOfWork,
        tenant_id: str,
        dataset_id: str | None = None,
        dataset_key: str | None = None,
    ) -> DatasetRecord:
        if dataset_id:
            return await self.get_dataset_record(uow=uow, dataset_id=dataset_id)
        if dataset_key:
            record = await uow.datasets.get_by_key(tenant_id, dataset_key)
            if record is not None:
                return record
            raise NotFoundError(f"Dataset key `{dataset_key}` was not found.")
        raise ValidationError("Either `dataset_id` or `dataset_key` is required.")

    def build_access_context(self, record: DatasetRecord) -> dict[str, Any]:
        policy = self._deserialize_access_policy(record)
        owner_actor_id = policy.owner_actor_id or record.created_by
        return {
            "tenant_id": record.tenant_id,
            "resource_type": "dataset",
            "resource_id": record.dataset_id,
            "access_level": record.access_level,
            "access_policy": {
                "owner_actor_id": owner_actor_id,
                "allowed_role_keys": policy.allowed_role_keys,
                "denied_role_keys": policy.denied_role_keys,
                "classification_labels": policy.classification_labels,
                "purpose_tags": policy.purpose_tags,
                "constraints": policy.constraints,
            },
            "owner_actor_id": owner_actor_id,
            "attributes": {
                "dataset_key": record.dataset_key,
                "retention_class": record.retention_class,
                "status": record.status,
                "tags": list(record.tags),
                "classification_labels": policy.classification_labels,
                "purpose_tags": policy.purpose_tags,
                **policy.constraints,
            },
        }

    def _to_contract(self, record: DatasetRecord) -> KnowledgeDataset:
        access_policy = self._deserialize_access_policy(record)
        created_at = record.created_at or utc_now()
        updated_at = record.updated_at or created_at
        return KnowledgeDataset(
            dataset_id=record.dataset_id,
            dataset_key=record.dataset_key,
            display_name=record.display_name,
            description=record.description,
            status=KnowledgeDatasetStatus(record.status),
            tags=list(record.tags),
            retention_class=DatasetRetentionClass(record.retention_class),
            metadata=dict(record.metadata),
            access_policy=access_policy,
            counters=self._dataset_counters(record),
            audit=AuditFields(
                created_at=created_at,
                updated_at=updated_at,
                created_by=record.created_by,
            ),
        )

    @staticmethod
    def _dataset_counters(record: DatasetRecord) -> DatasetCounters:
        metadata = record.metadata.get("counters")
        if isinstance(metadata, dict):
            try:
                return DatasetCounters.model_validate(metadata)
            except Exception:
                return DatasetCounters()
        return DatasetCounters()

    @staticmethod
    def _normalize_access_policy(
        policy: AccessPolicy | None,
        *,
        owner_actor_id: str,
    ) -> AccessPolicy:
        normalized = policy.model_copy(deep=True) if policy is not None else AccessPolicy()
        if normalized.access_level is None:
            normalized.access_level = ContractAccessLevel.TENANT_PRIVATE
        if not normalized.owner_actor_id:
            normalized.owner_actor_id = owner_actor_id
        return normalized

    @staticmethod
    def _domain_access_level(policy: AccessPolicy) -> AccessLevel:
        if policy.access_level is None:
            return AccessLevel.TENANT_PRIVATE
        return AccessLevel(policy.access_level.value)

    @staticmethod
    def _deserialize_access_policy(record: DatasetRecord) -> AccessPolicy:
        payload = dict(record.access_policy)
        payload.setdefault("access_level", record.access_level.value)
        payload.setdefault("owner_actor_id", record.created_by)
        return AccessPolicy.model_validate(payload)
