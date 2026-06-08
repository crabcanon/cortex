"""Repository implementations for core Cortex metadata entities."""

from collections.abc import Sequence
from typing import Any

from cortex_common import PaginationWindow, json_dumps, json_loads, utc_now
from cortex_domain import (
    AccessLevel,
    ActorRecord,
    ActorRoleBindingRecord,
    AuthorizationDecisionRecord,
    AuthorizationPolicyRecord,
    DatasetItemRecord,
    DatasetRecord,
    DecisionEffect,
    DocumentArtifactRecord,
    DocumentChunkRecord,
    DocumentRecord,
    DocumentTagRecord,
    EvalEngineRecord,
    EvalMetricDefinitionRecord,
    EvalRunMetricRecord,
    EvalRunRecord,
    EvalType,
    JobEventRecord,
    JobRecord,
    JobStatus,
    JobType,
    KnowledgeRunRecord,
    ObjectRecord,
    ObjectStatus,
    ObjectVersionRecord,
    ParseAttemptStatus,
    ParseEngineDeploymentMode,
    ParseEngineRecord,
    ParseEngineStatus,
    ParserProfileRecord,
    ParseRunAttemptRecord,
    ParseRunRecord,
    PermissionRecord,
    RolePermissionRecord,
    RoleRecord,
    SearchHitRecord,
    SearchRequestRecord,
    SourceType,
    StorageBucketRecord,
    SynthesisEngineRecord,
    SynthesisRunRecord,
    SynthesisType,
    TenantRecord,
)
from sqlalchemy import desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    ActorModel,
    ActorRoleBindingModel,
    AuthorizationDecisionModel,
    AuthorizationPolicyModel,
    DatasetItemModel,
    DatasetModel,
    DocumentArtifactModel,
    DocumentChunkModel,
    DocumentModel,
    DocumentTagModel,
    EvalEngineModel,
    EvalMetricDefinitionModel,
    EvalRunMetricModel,
    EvalRunModel,
    JobEventModel,
    JobModel,
    KnowledgeRunModel,
    ObjectModel,
    ObjectVersionModel,
    ParserEngineModel,
    ParserProfileModel,
    ParseRunAttemptModel,
    ParseRunModel,
    PermissionModel,
    RoleModel,
    RolePermissionModel,
    SearchHitModel,
    SearchRequestModel,
    StorageBucketModel,
    SynthesisEngineModel,
    SynthesisRunModel,
    TenantModel,
)

_OBJECT_TAGS_KEY = "__tags__"
_OBJECT_UPLOAD_STATE_KEY = "__upload__"
_DATASET_TAGS_KEY = "__tags__"


def _json_object(value: dict[str, Any] | None) -> str:
    return json_dumps(value or {})


def _json_dict(value: str) -> dict[str, Any]:
    payload = json_loads(value)
    return payload if isinstance(payload, dict) else {}


def _json_list(value: str) -> list[Any]:
    payload = json_loads(value)
    return payload if isinstance(payload, list) else []


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


def _permission_from_model(model: PermissionModel) -> PermissionRecord:
    return PermissionRecord(
        permission_key=model.permission_key,
        permission_kind=model.permission_kind,
        resource_type=model.resource_type,
        action_name=model.action_name,
        description=model.description,
        metadata=_json_dict(model.metadata_json),
    )


def _role_from_model(model: RoleModel) -> RoleRecord:
    return RoleRecord(
        role_id=model.role_id,
        tenant_id=model.tenant_id,
        role_key=model.role_key,
        display_name=model.display_name,
        scope_level=model.scope_level,
        is_builtin=model.is_builtin,
        description=model.description,
        metadata=_json_dict(model.metadata_json),
        created_by=model.created_by,
    )


def _role_permission_from_model(model: RolePermissionModel) -> RolePermissionRecord:
    return RolePermissionRecord(
        role_id=model.role_id,
        permission_key=model.permission_key,
        effect=DecisionEffect(model.effect),
    )


def _binding_from_model(model: ActorRoleBindingModel) -> ActorRoleBindingRecord:
    return ActorRoleBindingRecord(
        binding_id=model.binding_id,
        tenant_id=model.tenant_id,
        actor_id=model.actor_id,
        role_id=model.role_id,
        binding_scope=model.binding_scope,
        resource_type=model.resource_type,
        resource_id=model.resource_id,
        expires_at=model.expires_at,
        metadata=_json_dict(model.metadata_json),
        created_by=model.created_by,
    )


def _policy_from_model(model: AuthorizationPolicyModel) -> AuthorizationPolicyRecord:
    return AuthorizationPolicyRecord(
        policy_id=model.policy_id,
        tenant_id=model.tenant_id,
        policy_key=model.policy_key,
        effect=DecisionEffect(model.effect),
        priority=model.priority,
        status=model.status,
        subject_selector=_json_dict(model.subject_selector_json),
        resource_selector=_json_dict(model.resource_selector_json),
        condition=_json_dict(model.condition_json),
        description=model.description,
        metadata=_json_dict(model.metadata_json),
        created_by=model.created_by,
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


def _parse_engine_from_model(model: ParserEngineModel) -> ParseEngineRecord:
    return ParseEngineRecord(
        engine_id=model.engine_id,
        engine_key=model.engine_key,
        display_name=model.display_name,
        engine_family=model.engine_family,
        deployment_mode=ParseEngineDeploymentMode(model.deployment_mode),
        status=ParseEngineStatus(model.status),
        supported_source_types=[
            str(value) for value in _json_list(model.supported_source_types_json)
        ],
        supported_formats=[str(value) for value in _json_list(model.supported_formats_json)],
        capability_flags=[str(value) for value in _json_list(model.capability_flags_json)],
        config_schema=_json_dict(model.config_schema_json),
        metadata=_json_dict(model.metadata_json),
    )


def _parser_profile_from_model(model: ParserProfileModel) -> ParserProfileRecord:
    return ParserProfileRecord(
        profile_id=model.profile_id,
        tenant_id=model.tenant_id,
        profile_key=model.profile_key,
        display_name=model.display_name,
        description=model.description,
        routing_mode=model.routing_mode,
        preferred_engine_id=model.preferred_engine_id,
        allowed_engines=[str(value) for value in _json_list(model.allowed_engines_json)],
        source_constraints=_json_dict(model.source_constraints_json),
        normalization=_json_dict(model.normalization_json),
        fallback_policy=_json_dict(model.fallback_policy_json),
        engine_overrides=_json_dict(model.engine_overrides_json),
        metadata=_json_dict(model.metadata_json),
        created_by=model.created_by,
    )


def _serialize_object_metadata(record: ObjectRecord) -> str:
    payload: dict[str, Any] = dict(record.metadata)
    if record.tags:
        payload[_OBJECT_TAGS_KEY] = list(record.tags)
    if record.upload_state:
        payload[_OBJECT_UPLOAD_STATE_KEY] = dict(record.upload_state)
    return _json_object(payload)


def _deserialize_object_payload(
    model: ObjectModel,
) -> tuple[dict[str, Any], list[str], dict[str, Any]]:
    payload = _json_dict(model.metadata_json)
    raw_tags = payload.pop(_OBJECT_TAGS_KEY, [])
    tags = [str(value) for value in raw_tags] if isinstance(raw_tags, list) else []
    upload_state = payload.pop(_OBJECT_UPLOAD_STATE_KEY, {})
    if not isinstance(upload_state, dict):
        upload_state = {}
    return payload, tags, upload_state


def _object_from_model(model: ObjectModel) -> ObjectRecord:
    metadata, tags, upload_state = _deserialize_object_payload(model)
    return ObjectRecord(
        object_id=model.object_id,
        tenant_id=model.tenant_id,
        bucket_id=model.bucket_id,
        object_key=model.object_key,
        filename=model.filename,
        content_type=model.content_type,
        size_bytes=model.size_bytes,
        checksum_sha256=model.checksum_sha256,
        etag=model.etag,
        storage_class=model.storage_class,
        source_uri=model.source_uri,
        access_level=AccessLevel(model.access_level),
        access_policy=_json_dict(model.access_policy_json),
        status=ObjectStatus(model.status),
        metadata=metadata,
        tags=tags,
        upload_state=upload_state,
        created_by=model.created_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _object_version_from_model(model: ObjectVersionModel) -> ObjectVersionRecord:
    return ObjectVersionRecord(
        object_version_id=model.object_version_id,
        object_id=model.object_id,
        version_no=model.version_no,
        provider_version_ref=model.provider_version_ref,
        size_bytes=model.size_bytes,
        checksum_sha256=model.checksum_sha256,
        etag=model.etag,
        is_latest=model.is_latest,
        created_at=model.created_at,
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
        source_object_id=model.source_object_id,
        language_code=model.language_code,
        detected_mime_type=model.detected_mime_type,
        content_hash_sha256=model.content_hash_sha256,
        access_level=AccessLevel(model.access_level),
        access_policy=_json_dict(model.access_policy_json),
        status=model.status,
        metadata=_json_dict(model.metadata_json),
        audit=_json_dict(model.audit_json),
        published_at=model.published_at,
        created_by=model.created_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _document_artifact_from_model(model: DocumentArtifactModel) -> DocumentArtifactRecord:
    return DocumentArtifactRecord(
        document_id=model.document_id,
        artifact_type=model.artifact_type,
        object_id=model.object_id,
        artifact_ref=model.artifact_ref,
        metadata=_json_dict(model.metadata_json),
        created_at=model.created_at,
    )


def _document_tag_from_model(model: DocumentTagModel) -> DocumentTagRecord:
    return DocumentTagRecord(
        document_id=model.document_id,
        tag=model.tag,
        created_at=model.created_at,
    )


def _document_chunk_from_model(model: DocumentChunkModel) -> DocumentChunkRecord:
    return DocumentChunkRecord(
        chunk_id=model.chunk_id,
        document_id=model.document_id,
        chunk_index=model.chunk_index,
        chunk_text=model.chunk_text,
        heading_path=model.heading_path,
        token_count=model.token_count,
        char_count=model.char_count,
        checksum_sha256=model.checksum_sha256,
        metadata=_json_dict(model.metadata_json),
        created_at=model.created_at,
    )


def _dataset_from_model(model: DatasetModel) -> DatasetRecord:
    payload = _json_dict(model.metadata_json)
    raw_tags = payload.pop(_DATASET_TAGS_KEY, [])
    tags = [str(value) for value in raw_tags] if isinstance(raw_tags, list) else []
    return DatasetRecord(
        dataset_id=model.dataset_id,
        tenant_id=model.tenant_id,
        dataset_key=model.dataset_key,
        display_name=model.display_name,
        description=model.description,
        retention_class=model.retention_class,
        access_level=AccessLevel(model.access_level),
        access_policy=_json_dict(model.access_policy_json),
        metadata=payload,
        tags=tags,
        status=model.status,
        created_by=model.created_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _dataset_item_from_model(model: DatasetItemModel) -> DatasetItemRecord:
    return DatasetItemRecord(
        dataset_id=model.dataset_id,
        item_type=model.item_type,
        item_id=model.item_id,
        source_stage=model.source_stage,
        label=model.label,
        metadata=_json_dict(model.metadata_json),
        created_at=model.created_at,
    )


def _job_from_model(model: JobModel) -> JobRecord:
    return JobRecord(
        job_id=model.job_id,
        tenant_id=model.tenant_id,
        job_type=JobType(model.job_type),
        status=JobStatus(model.status),
        operation_name=model.operation_name,
        submitted_at=model.submitted_at,
        priority=model.priority,
        idempotency_key=model.idempotency_key,
        target_type=model.target_type,
        target_id=model.target_id,
        started_at=model.started_at,
        heartbeat_at=model.heartbeat_at,
        finished_at=model.completed_at,
        request_id=model.correlation_id,
        trace_id=model.trace_id,
        span_id=model.span_id,
        request_payload=_json_dict(model.request_json),
        result_payload=_json_dict(model.result_json),
        telemetry_context=_json_dict(model.telemetry_context_json),
        deployment_context=_json_dict(model.deployment_context_json),
        experiment_context=_json_dict(model.experiment_context_json),
        error_code=model.error_code,
        error_message=model.error_message,
        submitted_by=model.submitted_by,
    )


def _job_event_from_model(model: JobEventModel) -> JobEventRecord:
    return JobEventRecord(
        job_id=model.job_id,
        sequence_no=model.sequence_no,
        level=model.level,
        event_type=model.event_type,
        event_at=model.event_at,
        message=model.message,
        details=_json_dict(model.details_json),
        trace_id=model.trace_id,
        span_id=model.span_id,
    )


def _parse_run_from_model(model: ParseRunModel) -> ParseRunRecord:
    return ParseRunRecord(
        parse_run_id=model.parse_run_id,
        job_id=model.job_id,
        source_kind=SourceType(model.source_kind),
        parser_profile_id=model.parser_profile_id,
        selected_engine_id=model.selected_engine_id,
        trace_id=model.trace_id,
        document_id=model.document_id,
        source_url=model.source_url,
        source_ref=model.source_ref,
        selection_policy=_json_dict(model.selection_policy_json),
        crawl_profile=_json_dict(model.crawl_profile_json),
        normalization=_json_dict(model.normalization_json),
        output_profile=_json_dict(model.output_profile_json),
        fallback_chain=[str(value) for value in _json_list(model.fallback_chain_json)],
        diagnostics=_json_dict(model.diagnostics_json),
        telemetry_context=_json_dict(model.telemetry_context_json),
        deployment_context=_json_dict(model.deployment_context_json),
        experiment_context=_json_dict(model.experiment_context_json),
        created_at=model.created_at,
    )


def _parse_run_attempt_from_model(model: ParseRunAttemptModel) -> ParseRunAttemptRecord:
    return ParseRunAttemptRecord(
        parse_run_id=model.parse_run_id,
        attempt_no=model.attempt_no,
        engine_id=model.engine_id,
        status=ParseAttemptStatus(model.status),
        trace_id=model.trace_id,
        span_id=model.span_id,
        engine_request=_json_dict(model.engine_request_json),
        engine_result=_json_dict(model.engine_result_json),
        diagnostics=_json_dict(model.diagnostics_json),
        started_at=model.started_at,
        completed_at=model.completed_at,
        error_code=model.error_code,
        error_message=model.error_message,
    )


def _knowledge_run_from_model(model: KnowledgeRunModel) -> KnowledgeRunRecord:
    return KnowledgeRunRecord(
        knowledge_run_id=model.knowledge_run_id,
        job_id=model.job_id,
        dataset_id=model.dataset_id,
        operation_name=model.operation_name,
        trace_id=model.trace_id,
        request_payload=_json_dict(model.request_json),
        result_summary=_json_dict(model.result_summary_json),
        telemetry_context=_json_dict(model.telemetry_context_json),
        deployment_context=_json_dict(model.deployment_context_json),
        experiment_context=_json_dict(model.experiment_context_json),
        created_at=model.created_at,
    )


def _eval_engine_from_model(model: EvalEngineModel) -> EvalEngineRecord:
    return EvalEngineRecord(
        engine_id=model.engine_id,
        engine_key=model.engine_key,
        display_name=model.display_name,
        engine_kind=model.engine_kind,
        capability_flags=[str(value) for value in _json_list(model.capability_flags_json)],
        metric_prefixes=[str(value) for value in _json_list(model.metric_prefixes_json)],
        supported_modes=[str(value) for value in _json_list(model.supported_modes_json)],
        runtime_config=_json_dict(model.runtime_config_json),
        status=model.status,
        created_at=model.created_at,
    )


def _eval_metric_definition_from_model(
    model: EvalMetricDefinitionModel,
) -> EvalMetricDefinitionRecord:
    return EvalMetricDefinitionRecord(
        metric_key=model.metric_key,
        display_name=model.display_name,
        category=model.category,
        description=model.description,
        unit=model.unit,
        score_direction=model.score_direction,
        eval_types=[EvalType(str(value)) for value in _json_list(model.eval_types_json)],
        engine_bindings=[
            dict(value)
            for value in _json_list(model.engine_bindings_json)
            if isinstance(value, dict)
        ],
        threshold_hint=float(model.threshold_hint) if model.threshold_hint is not None else None,
        created_at=model.created_at,
    )


def _eval_run_from_model(model: EvalRunModel) -> EvalRunRecord:
    return EvalRunRecord(
        eval_run_id=model.eval_run_id,
        job_id=model.job_id,
        tenant_id=model.tenant_id,
        dataset_id=model.dataset_id,
        eval_type=EvalType(model.eval_type),
        engine_id=model.engine_id,
        profile_key=model.profile_key,
        input_ref=_json_dict(model.input_ref_json),
        target_ref=_json_dict(model.target_ref_json),
        metrics_config=[
            dict(value)
            for value in _json_list(model.metrics_config_json)
            if isinstance(value, dict)
        ],
        summary_results=_json_dict(model.summary_results_json),
        sample_summary=_json_dict(model.sample_summary_json),
        report_object_id=model.report_object_id,
        result_dataset_id=model.result_dataset_id,
        trace_id=model.trace_id,
        span_id=model.span_id,
        created_by=model.created_by,
        created_at=model.created_at,
    )


def _eval_run_metric_from_model(model: EvalRunMetricModel) -> EvalRunMetricRecord:
    return EvalRunMetricRecord(
        eval_run_id=model.eval_run_id,
        metric_index=model.metric_index,
        metric_key=model.metric_key,
        engine_id=model.engine_id,
        native_metric_key=model.native_metric_key,
        status=model.status,
        score=float(model.score) if model.score is not None else None,
        threshold=float(model.threshold) if model.threshold is not None else None,
        unit=model.unit,
        sample_size=model.sample_size,
        details=_json_dict(model.details_json),
    )


def _synthesis_engine_from_model(model: SynthesisEngineModel) -> SynthesisEngineRecord:
    return SynthesisEngineRecord(
        engine_id=model.engine_id,
        engine_key=model.engine_key,
        display_name=model.display_name,
        engine_kind=model.engine_kind,
        capability_flags=[str(value) for value in _json_list(model.capability_flags_json)],
        supported_source_types=[
            str(value) for value in _json_list(model.supported_source_types_json)
        ],
        output_formats=[str(value) for value in _json_list(model.output_formats_json)],
        runtime_config=_json_dict(model.runtime_config_json),
        status=model.status,
        created_at=model.created_at,
    )


def _synthesis_run_from_model(model: SynthesisRunModel) -> SynthesisRunRecord:
    return SynthesisRunRecord(
        synthesis_run_id=model.synthesis_run_id,
        job_id=model.job_id,
        tenant_id=model.tenant_id,
        dataset_id=model.dataset_id,
        synthesis_type=SynthesisType(model.synthesis_type),
        engine_id=model.engine_id,
        profile_key=model.profile_key,
        source_ref=_json_dict(model.source_ref_json),
        config=_json_dict(model.config_json),
        quality_summary=_json_dict(model.quality_summary_json),
        output_summary=_json_dict(model.output_summary_json),
        output_object_id=model.output_object_id,
        output_dataset_id=model.output_dataset_id,
        trace_id=model.trace_id,
        span_id=model.span_id,
        created_by=model.created_by,
        created_at=model.created_at,
    )


def _search_request_from_model(model: SearchRequestModel) -> SearchRequestRecord:
    return SearchRequestRecord(
        request_id=model.request_id,
        tenant_id=model.tenant_id,
        dataset_scope=[str(value) for value in _json_list(model.dataset_scope_json)],
        session_id=model.session_id,
        search_type=model.search_type,
        trace_id=model.trace_id,
        span_id=model.span_id,
        query_text=model.query_text,
        filters=_json_dict(model.filters_json),
        options=_json_dict(model.options_json),
        answer_text=model.answer_text,
        latency_ms=model.latency_ms,
        telemetry_context=_json_dict(model.telemetry_context_json),
        deployment_context=_json_dict(model.deployment_context_json),
        experiment_context=_json_dict(model.experiment_context_json),
        created_by=model.created_by,
        created_at=model.created_at,
    )


def _search_hit_from_model(model: SearchHitModel) -> SearchHitRecord:
    return SearchHitRecord(
        request_id=model.request_id,
        hit_index=model.hit_index,
        hit_type=model.hit_type,
        source_id=model.source_id,
        document_id=model.document_id,
        object_id=model.object_id,
        score=float(model.score) if model.score is not None else None,
        title=model.title,
        snippet=model.snippet,
        citation=_json_dict(model.citation_json),
        metadata=_json_dict(model.metadata_json),
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
        policy_id=model.policy_id,
        trace_id=model.trace_id,
        request_id=model.request_id,
        metadata=_json_dict(model.metadata_json),
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

    async def add(self, record: PermissionRecord) -> PermissionRecord:
        model = PermissionModel(
            permission_key=record.permission_key,
            permission_kind=record.permission_kind,
            resource_type=record.resource_type,
            action_name=record.action_name,
            description=record.description,
            metadata_json=_json_object(record.metadata),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _permission_from_model(model)

    async def get(self, permission_key: str) -> PermissionRecord | None:
        model = await self._session.get(PermissionModel, permission_key)
        return None if model is None else _permission_from_model(model)

    async def list_by_keys(self, permission_keys: Sequence[str]) -> list[PermissionRecord]:
        keys = list(dict.fromkeys(permission_keys))
        if not keys:
            return []
        result = await self._session.execute(
            select(PermissionModel).where(PermissionModel.permission_key.in_(keys))
        )
        return [_permission_from_model(model) for model in result.scalars().all()]


class RoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: RoleRecord) -> RoleRecord:
        model = RoleModel(
            role_id=record.role_id,
            tenant_id=record.tenant_id,
            role_key=record.role_key,
            display_name=record.display_name,
            scope_level=record.scope_level,
            is_builtin=record.is_builtin,
            description=record.description,
            metadata_json=_json_object(record.metadata),
            created_by=record.created_by,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _role_from_model(model)

    async def get(self, role_id: str) -> RoleRecord | None:
        model = await self._session.get(RoleModel, role_id)
        return None if model is None else _role_from_model(model)

    async def list_for_tenant(self, tenant_id: str) -> list[RoleRecord]:
        result = await self._session.execute(
            select(RoleModel)
            .where(RoleModel.tenant_id == tenant_id)
            .order_by(RoleModel.role_key.asc())
        )
        return [_role_from_model(model) for model in result.scalars().all()]


class RolePermissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: RolePermissionRecord) -> RolePermissionRecord:
        model = RolePermissionModel(
            role_id=record.role_id,
            permission_key=record.permission_key,
            effect=record.effect.value,
        )
        self._session.add(model)
        await self._session.flush()
        return _role_permission_from_model(model)

    async def list_for_role_ids(self, role_ids: Sequence[str]) -> list[RolePermissionRecord]:
        ids = list(dict.fromkeys(role_ids))
        if not ids:
            return []
        result = await self._session.execute(
            select(RolePermissionModel).where(RolePermissionModel.role_id.in_(ids))
        )
        return [_role_permission_from_model(model) for model in result.scalars().all()]


class ActorRoleBindingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: ActorRoleBindingRecord) -> ActorRoleBindingRecord:
        model = ActorRoleBindingModel(
            binding_id=record.binding_id,
            tenant_id=record.tenant_id,
            actor_id=record.actor_id,
            role_id=record.role_id,
            binding_scope=record.binding_scope,
            resource_type=record.resource_type,
            resource_id=record.resource_id,
            expires_at=record.expires_at,
            metadata_json=_json_object(record.metadata),
            created_by=record.created_by,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _binding_from_model(model)

    async def list_for_actor(
        self,
        actor_id: str,
        *,
        tenant_id: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        now: Any | None = None,
    ) -> list[ActorRoleBindingRecord]:
        effective_now = now or utc_now()
        query = select(ActorRoleBindingModel).where(
            ActorRoleBindingModel.actor_id == actor_id,
            ActorRoleBindingModel.tenant_id == tenant_id,
            or_(
                ActorRoleBindingModel.expires_at.is_(None),
                ActorRoleBindingModel.expires_at > effective_now,
            ),
        )
        if resource_type is not None:
            query = query.where(
                or_(
                    ActorRoleBindingModel.resource_type.is_(None),
                    ActorRoleBindingModel.resource_type == resource_type,
                )
            )
        if resource_id is not None:
            query = query.where(
                or_(
                    ActorRoleBindingModel.resource_id.is_(None),
                    ActorRoleBindingModel.resource_id == resource_id,
                )
            )
        result = await self._session.execute(query.order_by(ActorRoleBindingModel.created_at.asc()))
        return [_binding_from_model(model) for model in result.scalars().all()]


class AuthorizationPolicyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: AuthorizationPolicyRecord) -> AuthorizationPolicyRecord:
        model = AuthorizationPolicyModel(
            policy_id=record.policy_id,
            tenant_id=record.tenant_id,
            policy_key=record.policy_key,
            effect=record.effect.value,
            priority=record.priority,
            status=record.status,
            subject_selector_json=_json_object(record.subject_selector),
            resource_selector_json=_json_object(record.resource_selector),
            condition_json=_json_object(record.condition),
            description=record.description,
            metadata_json=_json_object(record.metadata),
            created_by=record.created_by,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _policy_from_model(model)

    async def list_for_tenant(
        self,
        tenant_id: str,
        *,
        status: str = "active",
    ) -> list[AuthorizationPolicyRecord]:
        result = await self._session.execute(
            select(AuthorizationPolicyModel)
            .where(
                AuthorizationPolicyModel.tenant_id == tenant_id,
                AuthorizationPolicyModel.status == status,
            )
            .order_by(
                AuthorizationPolicyModel.priority.asc(),
                AuthorizationPolicyModel.created_at.asc(),
            )
        )
        return [_policy_from_model(model) for model in result.scalars().all()]


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

    async def get_by_name(self, tenant_id: str, bucket_name: str) -> StorageBucketRecord | None:
        result = await self._session.execute(
            select(StorageBucketModel).where(
                StorageBucketModel.tenant_id == tenant_id,
                StorageBucketModel.bucket_name == bucket_name,
            )
        )
        model = result.scalar_one_or_none()
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


class ParserEngineRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: ParseEngineRecord) -> ParseEngineRecord:
        model = ParserEngineModel(
            engine_id=record.engine_id,
            engine_key=record.engine_key,
            display_name=record.display_name,
            engine_family=record.engine_family,
            deployment_mode=record.deployment_mode.value,
            status=record.status.value,
            supported_source_types_json=json_dumps(record.supported_source_types),
            supported_formats_json=json_dumps(record.supported_formats),
            capability_flags_json=json_dumps(record.capability_flags),
            config_schema_json=_json_object(record.config_schema),
            metadata_json=_json_object(record.metadata),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _parse_engine_from_model(model)

    async def get(self, engine_id: str) -> ParseEngineRecord | None:
        model = await self._session.get(ParserEngineModel, engine_id)
        return None if model is None else _parse_engine_from_model(model)

    async def get_by_key(self, engine_key: str) -> ParseEngineRecord | None:
        result = await self._session.execute(
            select(ParserEngineModel).where(ParserEngineModel.engine_key == engine_key)
        )
        model = result.scalar_one_or_none()
        return None if model is None else _parse_engine_from_model(model)

    async def list_active(self) -> list[ParseEngineRecord]:
        result = await self._session.execute(
            select(ParserEngineModel)
            .where(ParserEngineModel.status == ParseEngineStatus.ACTIVE.value)
            .order_by(ParserEngineModel.engine_key.asc())
        )
        return [_parse_engine_from_model(model) for model in result.scalars().all()]


class ParserProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: ParserProfileRecord) -> ParserProfileRecord:
        model = ParserProfileModel(
            profile_id=record.profile_id,
            tenant_id=record.tenant_id,
            profile_key=record.profile_key,
            display_name=record.display_name,
            description=record.description,
            routing_mode=record.routing_mode,
            preferred_engine_id=record.preferred_engine_id,
            allowed_engines_json=json_dumps(record.allowed_engines),
            source_constraints_json=_json_object(record.source_constraints),
            normalization_json=_json_object(record.normalization),
            fallback_policy_json=_json_object(record.fallback_policy),
            engine_overrides_json=_json_object(record.engine_overrides),
            metadata_json=_json_object(record.metadata),
            created_by=record.created_by,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _parser_profile_from_model(model)

    async def get(self, profile_id: str) -> ParserProfileRecord | None:
        model = await self._session.get(ParserProfileModel, profile_id)
        return None if model is None else _parser_profile_from_model(model)

    async def get_by_key(self, tenant_id: str, profile_key: str) -> ParserProfileRecord | None:
        result = await self._session.execute(
            select(ParserProfileModel).where(
                ParserProfileModel.tenant_id == tenant_id,
                ParserProfileModel.profile_key == profile_key,
            )
        )
        model = result.scalar_one_or_none()
        return None if model is None else _parser_profile_from_model(model)

    async def list_for_tenant(self, tenant_id: str) -> list[ParserProfileRecord]:
        result = await self._session.execute(
            select(ParserProfileModel)
            .where(ParserProfileModel.tenant_id == tenant_id)
            .order_by(ParserProfileModel.profile_key.asc())
        )
        return [_parser_profile_from_model(model) for model in result.scalars().all()]


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
            checksum_sha256=record.checksum_sha256,
            etag=record.etag,
            storage_class=record.storage_class,
            source_uri=record.source_uri,
            access_level=record.access_level.value,
            access_policy_json=_json_object(record.access_policy),
            metadata_json=_serialize_object_metadata(record),
            status=record.status.value,
            created_by=record.created_by,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _object_from_model(model)

    async def get(self, object_id: str) -> ObjectRecord | None:
        model = await self._session.get(ObjectModel, object_id)
        return None if model is None else _object_from_model(model)

    async def update(self, record: ObjectRecord) -> ObjectRecord | None:
        model = await self._session.get(ObjectModel, record.object_id)
        if model is None:
            return None
        model.bucket_id = record.bucket_id
        model.object_key = record.object_key
        model.filename = record.filename
        model.content_type = record.content_type
        model.size_bytes = record.size_bytes
        model.checksum_sha256 = record.checksum_sha256
        model.etag = record.etag
        model.storage_class = record.storage_class
        model.source_uri = record.source_uri
        model.access_level = record.access_level.value
        model.access_policy_json = _json_object(record.access_policy)
        model.status = record.status.value
        model.metadata_json = _serialize_object_metadata(record)
        model.created_by = record.created_by
        await self._session.flush()
        await self._session.refresh(model)
        return _object_from_model(model)

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


class ObjectVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: ObjectVersionRecord) -> ObjectVersionRecord:
        if record.is_latest:
            await self._session.execute(
                update(ObjectVersionModel)
                .where(ObjectVersionModel.object_id == record.object_id)
                .values(is_latest=False)
            )
        model = ObjectVersionModel(
            object_version_id=record.object_version_id,
            object_id=record.object_id,
            version_no=record.version_no,
            provider_version_ref=record.provider_version_ref,
            size_bytes=record.size_bytes,
            checksum_sha256=record.checksum_sha256,
            etag=record.etag,
            is_latest=record.is_latest,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _object_version_from_model(model)

    async def get_latest(self, object_id: str) -> ObjectVersionRecord | None:
        result = await self._session.execute(
            select(ObjectVersionModel)
            .where(ObjectVersionModel.object_id == object_id)
            .order_by(ObjectVersionModel.version_no.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return None if model is None else _object_version_from_model(model)

    async def list_for_object(self, object_id: str) -> list[ObjectVersionRecord]:
        result = await self._session.execute(
            select(ObjectVersionModel)
            .where(ObjectVersionModel.object_id == object_id)
            .order_by(ObjectVersionModel.version_no.asc())
        )
        return [_object_version_from_model(model) for model in result.scalars().all()]


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
            source_object_id=record.source_object_id,
            title=record.title,
            language_code=record.language_code,
            source_format=record.source_format,
            detected_mime_type=record.detected_mime_type,
            content_hash_sha256=record.content_hash_sha256,
            access_level=record.access_level.value,
            access_policy_json=_json_object(record.access_policy),
            metadata_json=_json_object(record.metadata),
            audit_json=_json_object(record.audit),
            status=record.status,
            published_at=record.published_at,
            created_by=record.created_by,
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


class DocumentArtifactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: DocumentArtifactRecord) -> DocumentArtifactRecord:
        model = DocumentArtifactModel(
            document_id=record.document_id,
            artifact_type=record.artifact_type,
            object_id=record.object_id,
            artifact_ref=record.artifact_ref,
            metadata_json=_json_object(record.metadata),
            created_at=record.created_at or utc_now(),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _document_artifact_from_model(model)

    async def list_for_document(self, document_id: str) -> list[DocumentArtifactRecord]:
        result = await self._session.execute(
            select(DocumentArtifactModel)
            .where(DocumentArtifactModel.document_id == document_id)
            .order_by(DocumentArtifactModel.artifact_type.asc())
        )
        return [_document_artifact_from_model(model) for model in result.scalars().all()]


class DocumentTagRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: DocumentTagRecord) -> DocumentTagRecord:
        model = DocumentTagModel(
            document_id=record.document_id,
            tag=record.tag,
            created_at=record.created_at or utc_now(),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _document_tag_from_model(model)

    async def list_for_document(self, document_id: str) -> list[DocumentTagRecord]:
        result = await self._session.execute(
            select(DocumentTagModel)
            .where(DocumentTagModel.document_id == document_id)
            .order_by(DocumentTagModel.tag.asc())
        )
        return [_document_tag_from_model(model) for model in result.scalars().all()]


class DocumentChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: DocumentChunkRecord) -> DocumentChunkRecord:
        model = DocumentChunkModel(
            chunk_id=record.chunk_id,
            document_id=record.document_id,
            chunk_index=record.chunk_index,
            heading_path=record.heading_path,
            token_count=record.token_count,
            char_count=record.char_count,
            checksum_sha256=record.checksum_sha256,
            chunk_text=record.chunk_text,
            metadata_json=_json_object(record.metadata),
            created_at=record.created_at or utc_now(),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _document_chunk_from_model(model)

    async def list_for_document(self, document_id: str) -> list[DocumentChunkRecord]:
        result = await self._session.execute(
            select(DocumentChunkModel)
            .where(DocumentChunkModel.document_id == document_id)
            .order_by(DocumentChunkModel.chunk_index.asc())
        )
        return [_document_chunk_from_model(model) for model in result.scalars().all()]


class DatasetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: DatasetRecord) -> DatasetRecord:
        payload = dict(record.metadata)
        if record.tags:
            payload[_DATASET_TAGS_KEY] = list(record.tags)
        model = DatasetModel(
            dataset_id=record.dataset_id,
            tenant_id=record.tenant_id,
            dataset_key=record.dataset_key,
            display_name=record.display_name,
            description=record.description,
            retention_class=record.retention_class,
            access_level=record.access_level.value,
            access_policy_json=_json_object(record.access_policy),
            metadata_json=_json_object(payload),
            status=record.status,
            created_by=record.created_by,
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

    async def list_for_tenant(
        self,
        tenant_id: str,
        pagination: PaginationWindow | None = None,
    ) -> Sequence[DatasetRecord]:
        window = pagination or PaginationWindow()
        result = await self._session.execute(
            select(DatasetModel)
            .where(DatasetModel.tenant_id == tenant_id)
            .order_by(desc(DatasetModel.created_at))
            .offset(window.offset)
            .limit(window.limit)
        )
        return [_dataset_from_model(model) for model in result.scalars().all()]

    async def update(self, record: DatasetRecord) -> DatasetRecord | None:
        model = await self._session.get(DatasetModel, record.dataset_id)
        if model is None:
            return None
        payload = dict(record.metadata)
        if record.tags:
            payload[_DATASET_TAGS_KEY] = list(record.tags)
        model.display_name = record.display_name
        model.description = record.description
        model.retention_class = record.retention_class
        model.access_level = record.access_level.value
        model.access_policy_json = _json_object(record.access_policy)
        model.metadata_json = _json_object(payload)
        model.status = record.status
        model.created_by = record.created_by
        await self._session.flush()
        await self._session.refresh(model)
        return _dataset_from_model(model)


class DatasetItemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: DatasetItemRecord) -> DatasetItemRecord:
        model = DatasetItemModel(
            dataset_id=record.dataset_id,
            item_type=record.item_type,
            item_id=record.item_id,
            source_stage=record.source_stage,
            label=record.label,
            metadata_json=_json_object(record.metadata),
            created_at=record.created_at or utc_now(),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _dataset_item_from_model(model)

    async def get(
        self,
        dataset_id: str,
        *,
        item_type: str,
        item_id: str,
    ) -> DatasetItemRecord | None:
        model = await self._session.get(
            DatasetItemModel,
            {
                "dataset_id": dataset_id,
                "item_type": item_type,
                "item_id": item_id,
            },
        )
        return None if model is None else _dataset_item_from_model(model)

    async def list_for_dataset(self, dataset_id: str) -> list[DatasetItemRecord]:
        result = await self._session.execute(
            select(DatasetItemModel)
            .where(DatasetItemModel.dataset_id == dataset_id)
            .order_by(
                DatasetItemModel.created_at.asc(),
                DatasetItemModel.item_type.asc(),
                DatasetItemModel.item_id.asc(),
            )
        )
        return [_dataset_item_from_model(model) for model in result.scalars().all()]


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
            priority=record.priority,
            idempotency_key=record.idempotency_key,
            target_type=record.target_type,
            target_id=record.target_id,
            submitted_at=record.submitted_at,
            started_at=record.started_at,
            heartbeat_at=record.heartbeat_at,
            completed_at=record.finished_at,
            span_id=record.span_id,
            correlation_id=record.request_id,
            trace_id=record.trace_id,
            request_json=_json_object(record.request_payload),
            result_json=_json_object(record.result_payload),
            telemetry_context_json=_json_object(record.telemetry_context),
            deployment_context_json=_json_object(record.deployment_context),
            experiment_context_json=_json_object(record.experiment_context),
            error_code=record.error_code,
            error_message=record.error_message,
            submitted_by=record.submitted_by,
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

    async def list_queued(
        self,
        *,
        job_type: JobType,
        limit: int = 1,
    ) -> list[JobRecord]:
        result = await self._session.execute(
            select(JobModel)
            .where(
                JobModel.job_type == job_type.value,
                JobModel.status == JobStatus.QUEUED.value,
            )
            .order_by(JobModel.priority.desc(), JobModel.submitted_at.asc())
            .limit(limit)
        )
        return [_job_from_model(model) for model in result.scalars().all()]

    async def list_queued_for_types(
        self,
        *,
        job_types: Sequence[JobType],
        limit: int = 1,
    ) -> list[JobRecord]:
        job_type_values = [job_type.value for job_type in job_types]
        if not job_type_values:
            return []
        result = await self._session.execute(
            select(JobModel)
            .where(
                JobModel.job_type.in_(job_type_values),
                JobModel.status == JobStatus.QUEUED.value,
            )
            .order_by(JobModel.priority.desc(), JobModel.submitted_at.asc())
            .limit(limit)
        )
        return [_job_from_model(model) for model in result.scalars().all()]

    async def list_stale_running(
        self,
        *,
        job_type: JobType,
        stale_before: Any,
        limit: int = 100,
    ) -> list[JobRecord]:
        result = await self._session.execute(
            select(JobModel)
            .where(
                JobModel.job_type == job_type.value,
                JobModel.status == JobStatus.RUNNING.value,
                or_(JobModel.heartbeat_at.is_(None), JobModel.heartbeat_at < stale_before),
            )
            .order_by(JobModel.started_at.asc())
            .limit(limit)
        )
        return [_job_from_model(model) for model in result.scalars().all()]

    async def list_stale_running_for_types(
        self,
        *,
        job_types: Sequence[JobType],
        stale_before: Any,
        limit: int = 100,
    ) -> list[JobRecord]:
        job_type_values = [job_type.value for job_type in job_types]
        if not job_type_values:
            return []
        result = await self._session.execute(
            select(JobModel)
            .where(
                JobModel.job_type.in_(job_type_values),
                JobModel.status == JobStatus.RUNNING.value,
                or_(JobModel.heartbeat_at.is_(None), JobModel.heartbeat_at < stale_before),
            )
            .order_by(JobModel.started_at.asc())
            .limit(limit)
        )
        return [_job_from_model(model) for model in result.scalars().all()]

    async def update_status(
        self,
        job_id: str,
        *,
        status: JobStatus,
        started_at: Any | None = None,
        heartbeat_at: Any | None = None,
        finished_at: Any | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        result_payload: dict[str, Any] | None = None,
        deployment_context: dict[str, Any] | None = None,
        telemetry_context: dict[str, Any] | None = None,
        experiment_context: dict[str, Any] | None = None,
    ) -> JobRecord | None:
        model = await self._session.get(JobModel, job_id)
        if model is None:
            return None
        model.status = status.value
        if started_at is not None:
            model.started_at = started_at
        if heartbeat_at is not None:
            model.heartbeat_at = heartbeat_at
        if finished_at is not None:
            model.completed_at = finished_at
        if error_code is not None:
            model.error_code = error_code
        if error_message is not None:
            model.error_message = error_message
        if result_payload is not None:
            model.result_json = _json_object(result_payload)
        if deployment_context is not None:
            model.deployment_context_json = _json_object(deployment_context)
        if telemetry_context is not None:
            model.telemetry_context_json = _json_object(telemetry_context)
        if experiment_context is not None:
            model.experiment_context_json = _json_object(experiment_context)
        await self._session.flush()
        await self._session.refresh(model)
        return _job_from_model(model)


class JobEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: JobEventRecord) -> JobEventRecord:
        model = JobEventModel(
            job_id=record.job_id,
            sequence_no=record.sequence_no,
            level=record.level,
            event_type=record.event_type,
            trace_id=record.trace_id,
            span_id=record.span_id,
            message=record.message,
            details_json=_json_object(record.details),
            event_at=record.event_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _job_event_from_model(model)

    async def list_for_job(
        self,
        job_id: str,
        *,
        limit: int = 100,
    ) -> list[JobEventRecord]:
        result = await self._session.execute(
            select(JobEventModel)
            .where(JobEventModel.job_id == job_id)
            .order_by(JobEventModel.sequence_no.asc())
            .limit(limit)
        )
        return [_job_event_from_model(model) for model in result.scalars().all()]

    async def get_max_sequence_no(self, job_id: str) -> int:
        result = await self._session.execute(
            select(func.coalesce(func.max(JobEventModel.sequence_no), 0)).where(
                JobEventModel.job_id == job_id
            )
        )
        return result.scalar() or 0


class ParseRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: ParseRunRecord) -> ParseRunRecord:
        model = ParseRunModel(
            parse_run_id=record.parse_run_id,
            job_id=record.job_id,
            source_kind=record.source_kind.value,
            parser_profile_id=record.parser_profile_id,
            selected_engine_id=record.selected_engine_id,
            trace_id=record.trace_id,
            document_id=record.document_id,
            source_url=record.source_url,
            source_ref=record.source_ref,
            selection_policy_json=_json_object(record.selection_policy),
            crawl_profile_json=_json_object(record.crawl_profile),
            normalization_json=_json_object(record.normalization),
            output_profile_json=_json_object(record.output_profile),
            fallback_chain_json=json_dumps(record.fallback_chain),
            diagnostics_json=_json_object(record.diagnostics),
            telemetry_context_json=_json_object(record.telemetry_context),
            deployment_context_json=_json_object(record.deployment_context),
            experiment_context_json=_json_object(record.experiment_context),
            created_at=record.created_at or utc_now(),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _parse_run_from_model(model)

    async def get(self, parse_run_id: str) -> ParseRunRecord | None:
        model = await self._session.get(ParseRunModel, parse_run_id)
        return None if model is None else _parse_run_from_model(model)

    async def get_by_job(self, job_id: str) -> ParseRunRecord | None:
        result = await self._session.execute(
            select(ParseRunModel).where(ParseRunModel.job_id == job_id)
        )
        model = result.scalar_one_or_none()
        return None if model is None else _parse_run_from_model(model)


class ParseRunAttemptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: ParseRunAttemptRecord) -> ParseRunAttemptRecord:
        model = ParseRunAttemptModel(
            parse_run_id=record.parse_run_id,
            attempt_no=record.attempt_no,
            engine_id=record.engine_id,
            status=record.status.value,
            trace_id=record.trace_id,
            span_id=record.span_id,
            engine_request_json=_json_object(record.engine_request),
            engine_result_json=_json_object(record.engine_result),
            diagnostics_json=_json_object(record.diagnostics),
            started_at=record.started_at,
            completed_at=record.completed_at,
            error_code=record.error_code,
            error_message=record.error_message,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _parse_run_attempt_from_model(model)

    async def list_for_run(self, parse_run_id: str) -> list[ParseRunAttemptRecord]:
        result = await self._session.execute(
            select(ParseRunAttemptModel)
            .where(ParseRunAttemptModel.parse_run_id == parse_run_id)
            .order_by(ParseRunAttemptModel.attempt_no.asc())
        )
        return [_parse_run_attempt_from_model(model) for model in result.scalars().all()]


class KnowledgeRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: KnowledgeRunRecord) -> KnowledgeRunRecord:
        model = KnowledgeRunModel(
            knowledge_run_id=record.knowledge_run_id,
            job_id=record.job_id,
            dataset_id=record.dataset_id,
            operation_name=record.operation_name,
            trace_id=record.trace_id,
            request_json=_json_object(record.request_payload),
            result_summary_json=_json_object(record.result_summary),
            telemetry_context_json=_json_object(record.telemetry_context),
            deployment_context_json=_json_object(record.deployment_context),
            experiment_context_json=_json_object(record.experiment_context),
            created_at=record.created_at or utc_now(),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _knowledge_run_from_model(model)

    async def get(self, knowledge_run_id: str) -> KnowledgeRunRecord | None:
        model = await self._session.get(KnowledgeRunModel, knowledge_run_id)
        return None if model is None else _knowledge_run_from_model(model)

    async def get_by_job(self, job_id: str) -> KnowledgeRunRecord | None:
        result = await self._session.execute(
            select(KnowledgeRunModel).where(KnowledgeRunModel.job_id == job_id)
        )
        model = result.scalar_one_or_none()
        return None if model is None else _knowledge_run_from_model(model)

    async def update(self, record: KnowledgeRunRecord) -> KnowledgeRunRecord | None:
        model = await self._session.get(KnowledgeRunModel, record.knowledge_run_id)
        if model is None:
            return None
        model.dataset_id = record.dataset_id
        model.operation_name = record.operation_name
        model.trace_id = record.trace_id
        model.request_json = _json_object(record.request_payload)
        model.result_summary_json = _json_object(record.result_summary)
        model.telemetry_context_json = _json_object(record.telemetry_context)
        model.deployment_context_json = _json_object(record.deployment_context)
        model.experiment_context_json = _json_object(record.experiment_context)
        await self._session.flush()
        await self._session.refresh(model)
        return _knowledge_run_from_model(model)

    async def list_for_dataset(self, dataset_id: str) -> list[KnowledgeRunRecord]:
        result = await self._session.execute(
            select(KnowledgeRunModel)
            .where(KnowledgeRunModel.dataset_id == dataset_id)
            .order_by(KnowledgeRunModel.created_at.asc())
        )
        return [_knowledge_run_from_model(model) for model in result.scalars().all()]


class EvalEngineRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: EvalEngineRecord) -> EvalEngineRecord:
        model = EvalEngineModel(
            engine_id=record.engine_id,
            engine_key=record.engine_key,
            display_name=record.display_name,
            engine_kind=record.engine_kind,
            capability_flags_json=json_dumps(record.capability_flags),
            metric_prefixes_json=json_dumps(record.metric_prefixes),
            supported_modes_json=json_dumps(record.supported_modes),
            runtime_config_json=_json_object(record.runtime_config),
            status=record.status,
            created_at=record.created_at or utc_now(),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _eval_engine_from_model(model)

    async def get(self, engine_id: str) -> EvalEngineRecord | None:
        model = await self._session.get(EvalEngineModel, engine_id)
        return None if model is None else _eval_engine_from_model(model)

    async def get_by_key(self, engine_key: str) -> EvalEngineRecord | None:
        result = await self._session.execute(
            select(EvalEngineModel).where(EvalEngineModel.engine_key == engine_key)
        )
        model = result.scalar_one_or_none()
        return None if model is None else _eval_engine_from_model(model)

    async def list_all(self) -> list[EvalEngineRecord]:
        result = await self._session.execute(
            select(EvalEngineModel).order_by(EvalEngineModel.display_name.asc())
        )
        return [_eval_engine_from_model(model) for model in result.scalars().all()]

    async def upsert(self, record: EvalEngineRecord) -> EvalEngineRecord:
        existing = await self.get(record.engine_id)
        if existing is None:
            return await self.add(record)
        model = await self._session.get(EvalEngineModel, record.engine_id)
        if model is None:
            return await self.add(record)
        model.engine_key = record.engine_key
        model.display_name = record.display_name
        model.engine_kind = record.engine_kind
        model.capability_flags_json = json_dumps(record.capability_flags)
        model.metric_prefixes_json = json_dumps(record.metric_prefixes)
        model.supported_modes_json = json_dumps(record.supported_modes)
        model.runtime_config_json = _json_object(record.runtime_config)
        model.status = record.status
        await self._session.flush()
        await self._session.refresh(model)
        return _eval_engine_from_model(model)


class EvalMetricDefinitionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: EvalMetricDefinitionRecord) -> EvalMetricDefinitionRecord:
        model = EvalMetricDefinitionModel(
            metric_key=record.metric_key,
            display_name=record.display_name,
            category=record.category,
            description=record.description,
            unit=record.unit,
            score_direction=record.score_direction,
            eval_types_json=json_dumps([value.value for value in record.eval_types]),
            engine_bindings_json=json_dumps(record.engine_bindings),
            threshold_hint=record.threshold_hint,
            created_at=record.created_at or utc_now(),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _eval_metric_definition_from_model(model)

    async def get(self, metric_key: str) -> EvalMetricDefinitionRecord | None:
        model = await self._session.get(EvalMetricDefinitionModel, metric_key)
        return None if model is None else _eval_metric_definition_from_model(model)

    async def list_all(self) -> list[EvalMetricDefinitionRecord]:
        result = await self._session.execute(
            select(EvalMetricDefinitionModel).order_by(EvalMetricDefinitionModel.metric_key.asc())
        )
        return [_eval_metric_definition_from_model(model) for model in result.scalars().all()]

    async def upsert(self, record: EvalMetricDefinitionRecord) -> EvalMetricDefinitionRecord:
        model = await self._session.get(EvalMetricDefinitionModel, record.metric_key)
        if model is None:
            return await self.add(record)
        model.display_name = record.display_name
        model.category = record.category
        model.description = record.description
        model.unit = record.unit
        model.score_direction = record.score_direction
        model.eval_types_json = json_dumps([value.value for value in record.eval_types])
        model.engine_bindings_json = json_dumps(record.engine_bindings)
        model.threshold_hint = record.threshold_hint
        await self._session.flush()
        await self._session.refresh(model)
        return _eval_metric_definition_from_model(model)


class EvalRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: EvalRunRecord) -> EvalRunRecord:
        model = EvalRunModel(
            eval_run_id=record.eval_run_id,
            job_id=record.job_id,
            tenant_id=record.tenant_id,
            dataset_id=record.dataset_id,
            eval_type=record.eval_type.value,
            engine_id=record.engine_id,
            profile_key=record.profile_key,
            input_ref_json=_json_object(record.input_ref),
            target_ref_json=_json_object(record.target_ref),
            metrics_config_json=json_dumps(record.metrics_config),
            summary_results_json=_json_object(record.summary_results),
            sample_summary_json=_json_object(record.sample_summary),
            report_object_id=record.report_object_id,
            result_dataset_id=record.result_dataset_id,
            trace_id=record.trace_id,
            span_id=record.span_id,
            created_by=record.created_by,
            created_at=record.created_at or utc_now(),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _eval_run_from_model(model)

    async def get(self, eval_run_id: str) -> EvalRunRecord | None:
        model = await self._session.get(EvalRunModel, eval_run_id)
        return None if model is None else _eval_run_from_model(model)

    async def get_by_job(self, job_id: str) -> EvalRunRecord | None:
        result = await self._session.execute(
            select(EvalRunModel).where(EvalRunModel.job_id == job_id)
        )
        model = result.scalar_one_or_none()
        return None if model is None else _eval_run_from_model(model)

    async def update(self, record: EvalRunRecord) -> EvalRunRecord | None:
        model = await self._session.get(EvalRunModel, record.eval_run_id)
        if model is None:
            return None
        model.dataset_id = record.dataset_id
        model.eval_type = record.eval_type.value
        model.engine_id = record.engine_id
        model.profile_key = record.profile_key
        model.input_ref_json = _json_object(record.input_ref)
        model.target_ref_json = _json_object(record.target_ref)
        model.metrics_config_json = json_dumps(record.metrics_config)
        model.summary_results_json = _json_object(record.summary_results)
        model.sample_summary_json = _json_object(record.sample_summary)
        model.report_object_id = record.report_object_id
        model.result_dataset_id = record.result_dataset_id
        model.trace_id = record.trace_id
        model.span_id = record.span_id
        model.created_by = record.created_by
        await self._session.flush()
        await self._session.refresh(model)
        return _eval_run_from_model(model)


class EvalRunMetricRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_for_run(
        self,
        eval_run_id: str,
        metrics: Sequence[EvalRunMetricRecord],
    ) -> list[EvalRunMetricRecord]:
        result = await self._session.execute(
            select(EvalRunMetricModel).where(EvalRunMetricModel.eval_run_id == eval_run_id)
        )
        for model in result.scalars().all():
            await self._session.delete(model)
        created: list[EvalRunMetricRecord] = []
        for record in metrics:
            model = EvalRunMetricModel(
                eval_run_id=record.eval_run_id,
                metric_index=record.metric_index,
                metric_key=record.metric_key,
                engine_id=record.engine_id,
                native_metric_key=record.native_metric_key,
                status=record.status,
                score=record.score,
                threshold=record.threshold,
                unit=record.unit,
                sample_size=record.sample_size,
                details_json=_json_object(record.details),
            )
            self._session.add(model)
            created.append(record)
        await self._session.flush()
        return created

    async def list_for_run(self, eval_run_id: str) -> list[EvalRunMetricRecord]:
        result = await self._session.execute(
            select(EvalRunMetricModel)
            .where(EvalRunMetricModel.eval_run_id == eval_run_id)
            .order_by(EvalRunMetricModel.metric_index.asc())
        )
        return [_eval_run_metric_from_model(model) for model in result.scalars().all()]


class SynthesisEngineRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: SynthesisEngineRecord) -> SynthesisEngineRecord:
        model = SynthesisEngineModel(
            engine_id=record.engine_id,
            engine_key=record.engine_key,
            display_name=record.display_name,
            engine_kind=record.engine_kind,
            capability_flags_json=json_dumps(record.capability_flags),
            supported_source_types_json=json_dumps(record.supported_source_types),
            output_formats_json=json_dumps(record.output_formats),
            runtime_config_json=_json_object(record.runtime_config),
            status=record.status,
            created_at=record.created_at or utc_now(),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _synthesis_engine_from_model(model)

    async def get(self, engine_id: str) -> SynthesisEngineRecord | None:
        model = await self._session.get(SynthesisEngineModel, engine_id)
        return None if model is None else _synthesis_engine_from_model(model)

    async def get_by_key(self, engine_key: str) -> SynthesisEngineRecord | None:
        result = await self._session.execute(
            select(SynthesisEngineModel).where(SynthesisEngineModel.engine_key == engine_key)
        )
        model = result.scalar_one_or_none()
        return None if model is None else _synthesis_engine_from_model(model)

    async def list_all(self) -> list[SynthesisEngineRecord]:
        result = await self._session.execute(
            select(SynthesisEngineModel).order_by(SynthesisEngineModel.display_name.asc())
        )
        return [_synthesis_engine_from_model(model) for model in result.scalars().all()]

    async def upsert(self, record: SynthesisEngineRecord) -> SynthesisEngineRecord:
        model = await self._session.get(SynthesisEngineModel, record.engine_id)
        if model is None:
            return await self.add(record)
        model.engine_key = record.engine_key
        model.display_name = record.display_name
        model.engine_kind = record.engine_kind
        model.capability_flags_json = json_dumps(record.capability_flags)
        model.supported_source_types_json = json_dumps(record.supported_source_types)
        model.output_formats_json = json_dumps(record.output_formats)
        model.runtime_config_json = _json_object(record.runtime_config)
        model.status = record.status
        await self._session.flush()
        await self._session.refresh(model)
        return _synthesis_engine_from_model(model)


class SynthesisRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: SynthesisRunRecord) -> SynthesisRunRecord:
        model = SynthesisRunModel(
            synthesis_run_id=record.synthesis_run_id,
            job_id=record.job_id,
            tenant_id=record.tenant_id,
            dataset_id=record.dataset_id,
            synthesis_type=record.synthesis_type.value,
            engine_id=record.engine_id,
            profile_key=record.profile_key,
            source_ref_json=_json_object(record.source_ref),
            config_json=_json_object(record.config),
            quality_summary_json=_json_object(record.quality_summary),
            output_summary_json=_json_object(record.output_summary),
            output_object_id=record.output_object_id,
            output_dataset_id=record.output_dataset_id,
            trace_id=record.trace_id,
            span_id=record.span_id,
            created_by=record.created_by,
            created_at=record.created_at or utc_now(),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _synthesis_run_from_model(model)

    async def get(self, synthesis_run_id: str) -> SynthesisRunRecord | None:
        model = await self._session.get(SynthesisRunModel, synthesis_run_id)
        return None if model is None else _synthesis_run_from_model(model)

    async def get_by_job(self, job_id: str) -> SynthesisRunRecord | None:
        result = await self._session.execute(
            select(SynthesisRunModel).where(SynthesisRunModel.job_id == job_id)
        )
        model = result.scalar_one_or_none()
        return None if model is None else _synthesis_run_from_model(model)

    async def update(self, record: SynthesisRunRecord) -> SynthesisRunRecord | None:
        model = await self._session.get(SynthesisRunModel, record.synthesis_run_id)
        if model is None:
            return None
        model.dataset_id = record.dataset_id
        model.synthesis_type = record.synthesis_type.value
        model.engine_id = record.engine_id
        model.profile_key = record.profile_key
        model.source_ref_json = _json_object(record.source_ref)
        model.config_json = _json_object(record.config)
        model.quality_summary_json = _json_object(record.quality_summary)
        model.output_summary_json = _json_object(record.output_summary)
        model.output_object_id = record.output_object_id
        model.output_dataset_id = record.output_dataset_id
        model.trace_id = record.trace_id
        model.span_id = record.span_id
        model.created_by = record.created_by
        await self._session.flush()
        await self._session.refresh(model)
        return _synthesis_run_from_model(model)


class SearchRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: SearchRequestRecord) -> SearchRequestRecord:
        model = SearchRequestModel(
            request_id=record.request_id,
            tenant_id=record.tenant_id,
            dataset_scope_json=json_dumps(record.dataset_scope),
            session_id=record.session_id,
            search_type=record.search_type,
            trace_id=record.trace_id,
            span_id=record.span_id,
            query_text=record.query_text,
            filters_json=_json_object(record.filters),
            options_json=_json_object(record.options),
            answer_text=record.answer_text,
            latency_ms=record.latency_ms,
            telemetry_context_json=_json_object(record.telemetry_context),
            deployment_context_json=_json_object(record.deployment_context),
            experiment_context_json=_json_object(record.experiment_context),
            created_by=record.created_by,
            created_at=record.created_at or utc_now(),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _search_request_from_model(model)

    async def get(self, request_id: str) -> SearchRequestRecord | None:
        model = await self._session.get(SearchRequestModel, request_id)
        return None if model is None else _search_request_from_model(model)


class SearchHitRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: SearchHitRecord) -> SearchHitRecord:
        model = SearchHitModel(
            request_id=record.request_id,
            hit_index=record.hit_index,
            hit_type=record.hit_type,
            source_id=record.source_id,
            document_id=record.document_id,
            object_id=record.object_id,
            score=record.score,
            title=record.title,
            snippet=record.snippet,
            citation_json=_json_object(record.citation),
            metadata_json=_json_object(record.metadata),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _search_hit_from_model(model)

    async def list_for_request(self, request_id: str) -> list[SearchHitRecord]:
        result = await self._session.execute(
            select(SearchHitModel)
            .where(SearchHitModel.request_id == request_id)
            .order_by(SearchHitModel.hit_index.asc())
        )
        return [_search_hit_from_model(model) for model in result.scalars().all()]


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
            policy_id=record.policy_id,
            metadata_json=_json_object(record.metadata),
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
