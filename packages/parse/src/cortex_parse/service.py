"""Parse orchestration and persistence services."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from cortex_common import CortexError, new_prefixed_id, utc_now
from cortex_contracts import (
    AccessPolicy,
    FallbackOnError,
    ParseAttemptStatus,
    ParseEngineAttempt,
    ParseResult,
    ParseStoragePolicy,
    ParseSyncRequest,
)
from cortex_db import CortexUnitOfWork
from cortex_domain import (
    AccessLevel as DomainAccessLevel,
)
from cortex_domain import (
    DocumentArtifactRecord,
    DocumentChunkRecord,
    DocumentRecord,
    DocumentTagRecord,
    JobRecord,
    JobStatus,
    JobType,
    ParseEngineRecord,
    ParseEngineStatus,
    ParserProfileRecord,
    ParseRunAttemptRecord,
    ParseRunRecord,
    SourceType,
)
from cortex_domain import (
    ParseAttemptStatus as DomainParseAttemptStatus,
)
from cortex_domain import (
    ParseEngineDeploymentMode as DomainParseEngineDeploymentMode,
)
from cortex_observability import MetricsFacade, get_trace_context
from opentelemetry import trace

from .models import EngineExecutionContext, EngineExecutionResult, RouterSelection
from .normalization.pipeline import NormalizationResult, ParseNormalizationPipeline
from .profile_loader import ParseProfileLoader
from .registry import ParseEngineRegistry
from .router import ParseRouter


@dataclass(slots=True)
class AttemptSnapshot:
    attempt: ParseEngineAttempt
    engine_options: dict[str, Any] = field(default_factory=dict)
    engine_result: dict[str, Any] = field(default_factory=dict)


class ParsePersistenceService:
    """Persist parse catalog, document graph, and run records."""

    async def persist(
        self,
        *,
        uow: CortexUnitOfWork,
        caller: Any,
        request: ParseSyncRequest,
        job: JobRecord,
        selection: RouterSelection,
        normalization: NormalizationResult,
        attempt_snapshots: list[AttemptSnapshot],
    ) -> ParseResult:
        engine_records = await self._ensure_engine_catalog(uow, selection)
        profile_record = await self._ensure_profile_catalog(
            uow=uow,
            tenant_id=caller.tenant_id,
            selection=selection,
            engine_records=engine_records,
            created_by=caller.actor_id or caller.subject,
        )

        document_id: str | None = None
        if request.persistence.persist_document:
            document_id = await self._persist_document_graph(
                uow=uow,
                caller=caller,
                request=request,
                normalization=normalization,
            )
        parse_run = await uow.parse_runs.add(
            ParseRunRecord(
                parse_run_id=new_prefixed_id("prun"),
                job_id=job.job_id,
                source_kind=SourceType(request.source.input_kind.value),
                parser_profile_id=profile_record.profile_id if profile_record else None,
                selected_engine_id=self._selected_engine_id(
                    engine_records,
                    normalization.result.diagnostics.selected_engine_key,
                ),
                trace_id=job.trace_id,
                document_id=document_id,
                source_url=request.source.url,
                source_ref=request.source.object_id or request.source.uri,
                selection_policy={
                    "profile_ref": request.parser.profile_ref,
                    "preferred_engine_key": request.parser.preferred_engine_key,
                    "allowed_engines": request.parser.allowed_engines,
                    "fallback_policy": request.parser.fallback_policy.model_dump(mode="json"),
                },
                crawl_profile=request.crawl.model_dump(mode="json"),
                normalization=request.normalization.model_dump(mode="json"),
                output_profile=request.output.model_dump(mode="json"),
                fallback_chain=[snapshot.attempt.engine_key for snapshot in attempt_snapshots],
                diagnostics=normalization.result.diagnostics.model_dump(mode="json"),
                telemetry_context=normalization.result.telemetry.model_dump(mode="json")
                if normalization.result.telemetry
                else {},
                deployment_context={},
                experiment_context={},
            )
        )
        for snapshot in attempt_snapshots:
            engine_record = engine_records[snapshot.attempt.engine_key]
            await uow.parse_run_attempts.add(
                ParseRunAttemptRecord(
                    parse_run_id=parse_run.parse_run_id,
                    attempt_no=snapshot.attempt.attempt_no,
                    engine_id=engine_record.engine_id,
                    status=DomainParseAttemptStatus(snapshot.attempt.status.value),
                    trace_id=job.trace_id,
                    span_id=normalization.result.telemetry.span_id
                    if normalization.result.telemetry
                    else None,
                    engine_request={
                        "source": request.source.model_dump(mode="json"),
                        "engine_options": snapshot.engine_options,
                    },
                    engine_result=snapshot.engine_result,
                    diagnostics=snapshot.attempt.diagnostics,
                    started_at=snapshot.attempt.started_at,
                    completed_at=snapshot.attempt.completed_at,
                    error_code=snapshot.attempt.error_code,
                    error_message=snapshot.attempt.warning,
                )
            )

        normalization.result.job_id = job.job_id
        return normalization.result

    async def _ensure_engine_catalog(
        self,
        uow: CortexUnitOfWork,
        selection: RouterSelection,
    ) -> dict[str, ParseEngineRecord]:
        records: dict[str, ParseEngineRecord] = {}
        for routed in selection.engines:
            existing = await uow.parser_engines.get_by_key(routed.descriptor.engine_key)
            if existing is None:
                existing = await uow.parser_engines.add(
                    ParseEngineRecord(
                        engine_id=new_prefixed_id("pengine"),
                        engine_key=routed.descriptor.engine_key,
                        display_name=routed.descriptor.display_name,
                        engine_family=routed.descriptor.engine_family,
                        deployment_mode=DomainParseEngineDeploymentMode(
                            routed.descriptor.deployment_mode.value
                        ),
                        status=ParseEngineStatus(routed.descriptor.status.value),
                        supported_source_types=list(routed.descriptor.supported_source_types),
                        supported_formats=list(routed.descriptor.supported_formats),
                        capability_flags=list(routed.descriptor.capabilities),
                    )
                )
            records[routed.descriptor.engine_key] = existing
        return records

    async def _ensure_profile_catalog(
        self,
        *,
        uow: CortexUnitOfWork,
        tenant_id: str,
        selection: RouterSelection,
        engine_records: dict[str, ParseEngineRecord],
        created_by: str | None,
    ) -> ParserProfileRecord | None:
        if selection.profile is None:
            return None
        profile_ref = selection.profile.descriptor.profile_ref
        existing = await uow.parser_profiles.get_by_key(tenant_id, profile_ref)
        if existing is not None:
            return existing
        preferred_engine_key = selection.profile.descriptor.preferred_engine_key
        preferred_engine_id = (
            engine_records[preferred_engine_key].engine_id
            if preferred_engine_key and preferred_engine_key in engine_records
            else None
        )
        return await uow.parser_profiles.add(
            ParserProfileRecord(
                profile_id=new_prefixed_id("pprofile"),
                tenant_id=tenant_id,
                profile_key=profile_ref,
                display_name=selection.profile.descriptor.display_name,
                description=selection.profile.descriptor.description,
                routing_mode=selection.profile.descriptor.routing_mode or "ordered_fallback",
                preferred_engine_id=preferred_engine_id,
                allowed_engines=list(selection.profile.descriptor.allowed_engines),
                normalization=selection.profile.descriptor.normalization_defaults.model_dump(
                    mode="json"
                ),
                fallback_policy=selection.profile.descriptor.fallback_policy.model_dump(
                    mode="json"
                ),
                engine_overrides=dict(selection.profile.engine_overrides),
                source_constraints=dict(selection.profile.source_constraints),
                created_by=created_by,
            )
        )

    async def _persist_document_graph(
        self,
        *,
        uow: CortexUnitOfWork,
        caller: Any,
        request: ParseSyncRequest,
        normalization: NormalizationResult,
    ) -> str:
        result = normalization.result
        document = result.document
        access_policy = self._access_policy(
            document.access_policy or request.persistence.access_policy
        )
        created = await uow.documents.add(
            DocumentRecord(
                document_id=document.document_id,
                tenant_id=caller.tenant_id,
                source_type=SourceType(document.source_type.value),
                source_format=document.source_format,
                title=document.title,
                source_uri=document.source_uri,
                canonical_url=document.canonical_url,
                source_object_id=document.source_object_id,
                language_code=document.language_code,
                detected_mime_type=document.detected_mime_type,
                content_hash_sha256=document.provenance.content_hash_sha256,
                access_level=self._domain_access_level(access_policy),
                access_policy=access_policy.model_dump(mode="json"),
                metadata=document.metadata,
                audit={
                    **document.audit.model_dump(mode="json"),
                    "normalized_metadata": document.normalized_metadata.model_dump(mode="json"),
                    "parser": document.parser.model_dump(mode="json"),
                    "provenance": document.provenance.model_dump(mode="json"),
                },
                published_at=document.normalized_metadata.publish_date,
                created_by=caller.actor_id or caller.subject,
            )
        )
        for tag in list(dict.fromkeys([*document.category_tags, *document.labels])):
            await uow.document_tags.add(DocumentTagRecord(document_id=created.document_id, tag=tag))
        for chunk in normalization.chunks:
            checksum = hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()
            await uow.document_chunks.add(
                DocumentChunkRecord(
                    chunk_id=new_prefixed_id("chunk"),
                    document_id=created.document_id,
                    chunk_index=chunk.chunk_index,
                    chunk_text=chunk.text,
                    heading_path=chunk.heading_path,
                    token_count=chunk.token_count,
                    char_count=chunk.char_count,
                    checksum_sha256=checksum,
                    metadata=chunk.metadata,
                )
            )
        if request.persistence.persist_artifacts and result.artifacts is not None:
            for artifact_type, object_id, artifact_ref, metadata in self._artifact_records(result):
                if (
                    request.persistence.storage_policy is ParseStoragePolicy.METADATA_ONLY
                    and object_id
                ):
                    continue
                await uow.document_artifacts.add(
                    DocumentArtifactRecord(
                        document_id=created.document_id,
                        artifact_type=artifact_type,
                        object_id=object_id,
                        artifact_ref=artifact_ref,
                        metadata=metadata,
                    )
                )
        return created.document_id

    @staticmethod
    def _artifact_records(result: ParseResult):
        artifacts = result.artifacts
        if artifacts is None:
            return []
        rows: list[tuple[str, str | None, str | None, dict[str, Any]]] = []
        for artifact_type, ref in {
            "markdown": artifacts.markdown_object,
            "raw_html": artifacts.raw_html_object,
            "screenshot": artifacts.screenshot_object,
            "pdf": artifacts.pdf_object,
        }.items():
            if ref is None:
                continue
            rows.append(
                (
                    artifact_type,
                    ref.object_id,
                    ref.object_key,
                    ref.model_dump(mode="json"),
                )
            )
        if artifacts.ssl_certificate is not None:
            certificate = artifacts.ssl_certificate
            rows.append(
                (
                    "ssl_certificate",
                    None,
                    certificate.fingerprint or certificate.issuer_common_name,
                    certificate.model_dump(mode="json"),
                )
            )
        return rows

    @staticmethod
    def _access_policy(policy: AccessPolicy | None) -> AccessPolicy:
        return policy or AccessPolicy()

    @staticmethod
    def _selected_engine_id(
        engine_records: dict[str, ParseEngineRecord],
        selected_engine_key: str | None,
    ) -> str | None:
        if selected_engine_key is None:
            return None
        record = engine_records.get(selected_engine_key)
        return record.engine_id if record is not None else None

    @staticmethod
    def _domain_access_level(access_policy: AccessPolicy) -> DomainAccessLevel:
        if access_policy.access_level is None:
            return DomainAccessLevel.TENANT_PRIVATE
        return DomainAccessLevel(access_policy.access_level.value)


class ParseService:
    """Execute parse requests against registered engines and persist the result graph."""

    def __init__(
        self,
        *,
        registry: ParseEngineRegistry,
        profile_loader: ParseProfileLoader,
        default_profile_ref: str,
        normalization_pipeline: ParseNormalizationPipeline | None = None,
        persistence_service: ParsePersistenceService | None = None,
    ) -> None:
        self._registry = registry
        self._profile_loader = profile_loader
        self._router = ParseRouter(
            registry,
            profile_loader,
            default_profile_ref=default_profile_ref,
        )
        self._normalization = normalization_pipeline or ParseNormalizationPipeline()
        self._persistence = persistence_service or ParsePersistenceService()
        self._tracer = trace.get_tracer("cortex.parse")
        self._metrics = MetricsFacade("cortex.parse")

    def list_engines(self):
        return self._router.list_engines()

    def list_profiles(self):
        return self._router.list_profiles()

    async def parse(
        self,
        *,
        uow: CortexUnitOfWork,
        caller: Any,
        request: ParseSyncRequest,
    ) -> ParseResult:
        started_at = utc_now()
        trace_context = get_trace_context()
        job = await uow.jobs.add(
            JobRecord(
                job_id=new_prefixed_id("job"),
                tenant_id=caller.tenant_id,
                job_type=JobType.PARSE,
                status=JobStatus.RUNNING,
                operation_name="parse.document",
                submitted_at=started_at,
                started_at=started_at,
                trace_id=trace_context.get("trace_id"),
                span_id=trace_context.get("span_id"),
                request_payload=request.model_dump(mode="json"),
                submitted_by=caller.actor_id or caller.subject,
            )
        )
        return await self._execute_job(
            uow=uow,
            caller=caller,
            job=job,
            request=request,
            started_at=started_at,
        )

    async def execute_existing_job(
        self,
        *,
        uow: CortexUnitOfWork,
        caller: Any,
        job: JobRecord,
        request: ParseSyncRequest,
    ) -> ParseResult:
        started_at = utc_now()
        running_job = await uow.jobs.update_status(
            job.job_id,
            status=JobStatus.RUNNING,
            started_at=started_at,
            heartbeat_at=started_at,
        )
        if running_job is None:
            raise CortexError(
                code="job_not_found",
                detail=f"Parse job `{job.job_id}` disappeared before execution.",
                status_code=404,
            )
        return await self._execute_job(
            uow=uow,
            caller=caller,
            job=running_job,
            request=request,
            started_at=started_at,
        )

    async def _execute_job(
        self,
        *,
        uow: CortexUnitOfWork,
        caller: Any,
        job: JobRecord,
        request: ParseSyncRequest,
        started_at: Any,
    ) -> ParseResult:
        with self._tracer.start_as_current_span("parse.engine.execute") as span:
            selection = self._router.resolve(request)
            attempt_snapshots: list[AttemptSnapshot] = []
            execution: EngineExecutionResult | None = None
            selected_descriptor = None
            for attempt_no, routed in enumerate(selection.engines, start=1):
                attempt_started = utc_now()
                try:
                    execution = await routed.engine.execute(
                        EngineExecutionContext(
                            request=request,
                            source=request.source,
                            profile=selection.profile,
                            engine_options=routed.engine_options,
                        )
                    )
                except Exception as exc:
                    error_code = (
                        exc.code if isinstance(exc, CortexError) else "engine_execution_failed"
                    )
                    attempt = ParseEngineAttempt(
                        attempt_no=attempt_no,
                        engine_key=routed.descriptor.engine_key,
                        status=ParseAttemptStatus.FAILED,
                        started_at=attempt_started,
                        completed_at=utc_now(),
                        error_code=error_code,
                        warning=str(exc),
                        diagnostics={"engine_options": routed.engine_options},
                    )
                    attempt_snapshots.append(
                        AttemptSnapshot(
                            attempt=attempt,
                            engine_options=routed.engine_options,
                        )
                    )
                    if selection.fallback_policy.on_error is FallbackOnError.FAIL_FAST:
                        break
                    continue

                attempt = ParseEngineAttempt(
                    attempt_no=attempt_no,
                    engine_key=routed.descriptor.engine_key,
                    status=ParseAttemptStatus.SUCCEEDED,
                    started_at=attempt_started,
                    completed_at=utc_now(),
                    diagnostics={"engine_options": routed.engine_options},
                )
                attempt_snapshots.append(
                    AttemptSnapshot(
                        attempt=attempt,
                        engine_options=routed.engine_options,
                        engine_result=execution.engine_payload_summary,
                    )
                )
                selected_descriptor = routed.descriptor
                break

            if execution is None or selected_descriptor is None:
                failure_detail = self._failure_detail(attempt_snapshots)
                await uow.jobs.update_status(
                    job.job_id,
                    status=JobStatus.FAILED,
                    finished_at=utc_now(),
                    error_code="parse_failed",
                    error_message=failure_detail,
                )
                self._metrics.counter(
                    "cortex.parse.failures",
                    description="Count of failed parse requests.",
                ).add(1)
                raise CortexError(
                    code="parse_failed",
                    detail=failure_detail,
                    status_code=502,
                )

            normalization = self._normalization.normalize(
                request=request,
                execution=execution,
                selected_engine=selected_descriptor,
                profile=selection.profile,
                attempts=[snapshot.attempt for snapshot in attempt_snapshots],
                fallback_used=len(attempt_snapshots) > 1,
                started_at=started_at,
                created_by=caller.actor_id or caller.subject,
            )
            result = await self._persistence.persist(
                uow=uow,
                caller=caller,
                request=request,
                job=job,
                selection=selection,
                normalization=normalization,
                attempt_snapshots=attempt_snapshots,
            )
            await uow.jobs.update_status(
                job.job_id,
                status=JobStatus.SUCCEEDED,
                finished_at=utc_now(),
                result_payload={
                    "document_id": result.document.document_id,
                    "selected_engine_key": result.diagnostics.selected_engine_key,
                    "parse_result": result.model_dump(mode="json"),
                },
            )
            span.set_attribute("cortex.parse.engine", selected_descriptor.engine_key)
            span.set_attribute("cortex.parse.job_id", job.job_id)
            return result

    @staticmethod
    def _failure_detail(attempt_snapshots: list[AttemptSnapshot]) -> str:
        if not attempt_snapshots:
            return "No parse engine produced a successful result."
        attempts: list[str] = []
        for snapshot in attempt_snapshots:
            warning = (snapshot.attempt.warning or "").replace("\n", " ").strip()
            if len(warning) > 240:
                warning = f"{warning[:237]}..."
            detail = (
                f"{snapshot.attempt.engine_key}:{snapshot.attempt.error_code or 'unknown_error'}"
            )
            if warning:
                detail = f"{detail} ({warning})"
            attempts.append(detail)
        return "No parse engine produced a successful result. Attempts: " + "; ".join(attempts)
