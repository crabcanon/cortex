"""Knowledge execution and search services."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from cortex_common import CortexError, json_dumps, new_prefixed_id, utc_now
from cortex_contracts import (
    AddJobRequest,
    CognifyJobRequest,
    DatasetCounters,
    GraphPath,
    KnowledgeInput,
    MemifyJobRequest,
    SearchHit,
    SearchRequest,
    SearchResponse,
    TelemetryContext,
)
from cortex_db import CortexUnitOfWork
from cortex_domain import (
    DatasetItemRecord,
    DatasetRecord,
    JobRecord,
    JobType,
    KnowledgeRunRecord,
    SearchHitRecord,
    SearchRequestRecord,
)
from cortex_observability import MetricsFacade, get_trace_context
from opentelemetry import trace

from .models import CogneeRuntimeProtocol
from .service import KnowledgeDatasetService


@dataclass(slots=True)
class KnowledgeExecutionResult:
    dataset_id: str
    knowledge_run_id: str
    operation_name: str
    result_summary: dict[str, Any]


class KnowledgeOperationService:
    """Execute Add, Cognify, and Memify jobs against the configured runtime."""

    def __init__(
        self,
        runtime: CogneeRuntimeProtocol,
        dataset_service: KnowledgeDatasetService,
    ) -> None:
        self._runtime = runtime
        self._dataset_service = dataset_service
        self._tracer = trace.get_tracer("cortex.knowledge")
        self._metrics = MetricsFacade("cortex.knowledge")

    async def execute_job(
        self,
        *,
        uow: CortexUnitOfWork,
        job: JobRecord,
    ) -> KnowledgeExecutionResult:
        run = await self._require_run(uow=uow, job_id=job.job_id)
        dataset = await self._dataset_service.get_dataset_record(uow=uow, dataset_id=run.dataset_id)
        if job.job_type is JobType.KNOWLEDGE_ADD:
            request = AddJobRequest.model_validate(job.request_payload)
            return await self._execute_add(uow=uow, dataset=dataset, run=run, request=request)
        if job.job_type is JobType.KNOWLEDGE_COGNIFY:
            request = CognifyJobRequest.model_validate(job.request_payload)
            return await self._execute_cognify(uow=uow, dataset=dataset, run=run, request=request)
        if job.job_type is JobType.KNOWLEDGE_MEMIFY:
            request = MemifyJobRequest.model_validate(job.request_payload)
            return await self._execute_memify(uow=uow, dataset=dataset, run=run, request=request)
        raise CortexError(
            code="knowledge_job_unsupported",
            detail=f"Unsupported knowledge job type `{job.job_type.value}`.",
            status_code=400,
        )

    async def _execute_add(
        self,
        *,
        uow: CortexUnitOfWork,
        dataset: DatasetRecord,
        run: KnowledgeRunRecord,
        request: AddJobRequest,
    ) -> KnowledgeExecutionResult:
        with self._tracer.start_as_current_span("knowledge.add") as span:
            runtime_result = await self._runtime.add(
                dataset=dataset.dataset_key,
                payload=request.model_dump(mode="json"),
            )
            added_items = await self._persist_add_inputs(
                uow=uow,
                dataset=dataset,
                inputs=request.inputs,
            )
            counter_delta = {
                "objects": sum(1 for item in added_items if item.item_type == "object"),
                "documents": sum(1 for item in added_items if item.item_type == "document"),
            }
            dataset = await self._update_dataset_counters(
                uow=uow,
                dataset=dataset,
                counter_delta=counter_delta,
            )
            result_summary = {
                "status": "succeeded",
                "dataset_id": dataset.dataset_id,
                "dataset_key": dataset.dataset_key,
                "items_added": len(added_items),
                "item_types": self._item_type_counts(added_items),
                "runtime": self._normalize_runtime_result(runtime_result),
            }
            await self._persist_run_summary(uow=uow, run=run, result_summary=result_summary)
            span.set_attribute("cortex.dataset.id", dataset.dataset_id)
            self._metrics.counter(
                "cortex.knowledge.add.requests",
                description="Count of knowledge add executions.",
            ).add(1)
            return KnowledgeExecutionResult(
                dataset_id=dataset.dataset_id,
                knowledge_run_id=run.knowledge_run_id,
                operation_name=run.operation_name,
                result_summary=result_summary,
            )

    async def _execute_cognify(
        self,
        *,
        uow: CortexUnitOfWork,
        dataset: DatasetRecord,
        run: KnowledgeRunRecord,
        request: CognifyJobRequest,
    ) -> KnowledgeExecutionResult:
        with self._tracer.start_as_current_span("knowledge.cognify") as span:
            runtime_result = await self._runtime.cognify(
                dataset=dataset.dataset_key,
                payload=request.model_dump(mode="json"),
            )
            counter_delta = self._extract_counter_delta(runtime_result)
            dataset = await self._update_dataset_counters(
                uow=uow,
                dataset=dataset,
                counter_delta=counter_delta,
            )
            result_summary = {
                "status": "succeeded",
                "dataset_id": dataset.dataset_id,
                "dataset_key": dataset.dataset_key,
                "counter_delta": counter_delta,
                "runtime": self._normalize_runtime_result(runtime_result),
            }
            await self._persist_run_summary(uow=uow, run=run, result_summary=result_summary)
            span.set_attribute("cortex.dataset.id", dataset.dataset_id)
            self._metrics.counter(
                "cortex.knowledge.cognify.requests",
                description="Count of knowledge cognify executions.",
            ).add(1)
            return KnowledgeExecutionResult(
                dataset_id=dataset.dataset_id,
                knowledge_run_id=run.knowledge_run_id,
                operation_name=run.operation_name,
                result_summary=result_summary,
            )

    async def _execute_memify(
        self,
        *,
        uow: CortexUnitOfWork,
        dataset: DatasetRecord,
        run: KnowledgeRunRecord,
        request: MemifyJobRequest,
    ) -> KnowledgeExecutionResult:
        with self._tracer.start_as_current_span("knowledge.memify") as span:
            runtime_result = await self._runtime.memify(
                dataset=dataset.dataset_key,
                payload=request.model_dump(mode="json"),
            )
            counter_delta = self._extract_counter_delta(runtime_result)
            dataset = await self._update_dataset_counters(
                uow=uow,
                dataset=dataset,
                counter_delta=counter_delta,
            )
            result_summary = {
                "status": "succeeded",
                "dataset_id": dataset.dataset_id,
                "dataset_key": dataset.dataset_key,
                "pipeline": request.pipeline.value,
                "counter_delta": counter_delta,
                "runtime": self._normalize_runtime_result(runtime_result),
            }
            await self._persist_run_summary(uow=uow, run=run, result_summary=result_summary)
            span.set_attribute("cortex.dataset.id", dataset.dataset_id)
            self._metrics.counter(
                "cortex.knowledge.memify.requests",
                description="Count of knowledge memify executions.",
            ).add(1)
            return KnowledgeExecutionResult(
                dataset_id=dataset.dataset_id,
                knowledge_run_id=run.knowledge_run_id,
                operation_name=run.operation_name,
                result_summary=result_summary,
            )

    async def _persist_add_inputs(
        self,
        *,
        uow: CortexUnitOfWork,
        dataset: DatasetRecord,
        inputs: list[KnowledgeInput],
    ) -> list[DatasetItemRecord]:
        added: list[DatasetItemRecord] = []
        for item in inputs:
            item_type = self._dataset_item_type(item)
            item_id = self._dataset_item_id(item)
            existing = await uow.dataset_items.get(
                dataset.dataset_id,
                item_type=item_type,
                item_id=item_id,
            )
            if existing is not None:
                continue
            record = await uow.dataset_items.add(
                DatasetItemRecord(
                    dataset_id=dataset.dataset_id,
                    item_type=item_type,
                    item_id=item_id,
                    source_stage="add",
                    label=item.label,
                    metadata=self._dataset_item_metadata(item),
                )
            )
            added.append(record)
        return added

    async def _update_dataset_counters(
        self,
        *,
        uow: CortexUnitOfWork,
        dataset: DatasetRecord,
        counter_delta: dict[str, int],
    ) -> DatasetRecord:
        if not any(value for value in counter_delta.values()):
            return dataset
        counters = self._dataset_counters(dataset)
        for key, value in counter_delta.items():
            current = getattr(counters, key, 0)
            setattr(counters, key, max(0, current + int(value)))
        metadata = dict(dataset.metadata)
        metadata["counters"] = counters.model_dump(mode="json")
        dataset.metadata = metadata
        updated = await uow.datasets.update(dataset)
        return updated or dataset

    async def _persist_run_summary(
        self,
        *,
        uow: CortexUnitOfWork,
        run: KnowledgeRunRecord,
        result_summary: dict[str, Any],
    ) -> KnowledgeRunRecord:
        run.result_summary = dict(result_summary)
        return await uow.knowledge_runs.update(run) or run

    async def _require_run(
        self,
        *,
        uow: CortexUnitOfWork,
        job_id: str,
    ) -> KnowledgeRunRecord:
        run = await uow.knowledge_runs.get_by_job(job_id)
        if run is None:
            raise CortexError(
                code="knowledge_run_not_found",
                detail=f"Knowledge run for job `{job_id}` was not found.",
                status_code=404,
            )
        return run

    @staticmethod
    def _dataset_counters(dataset: DatasetRecord) -> DatasetCounters:
        payload = dataset.metadata.get("counters")
        if isinstance(payload, dict):
            try:
                return DatasetCounters.model_validate(payload)
            except Exception:
                return DatasetCounters()
        return DatasetCounters()

    @staticmethod
    def _item_type_counts(items: list[DatasetItemRecord]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in items:
            counts[item.item_type] = counts.get(item.item_type, 0) + 1
        return counts

    @staticmethod
    def _dataset_item_type(item: KnowledgeInput) -> str:
        return {
            "object_id": "object",
            "document_id": "document",
            "text": "text",
            "uri": "uri",
        }[item.input_type.value]

    @staticmethod
    def _dataset_item_id(item: KnowledgeInput) -> str:
        if item.input_type.value == "object_id" and item.object_id is not None:
            return item.object_id
        if item.input_type.value == "document_id" and item.document_id is not None:
            return item.document_id
        digest = hashlib.sha256(
            json_dumps(item.model_dump(mode="json")).encode("utf-8")
        ).hexdigest()[:30]
        return f"ditem_{digest}"

    @staticmethod
    def _dataset_item_metadata(item: KnowledgeInput) -> dict[str, Any]:
        metadata = dict(item.metadata)
        if item.object_id:
            metadata["object_id"] = item.object_id
        if item.document_id:
            metadata["document_id"] = item.document_id
        if item.uri:
            metadata["uri"] = item.uri
        if item.text:
            metadata["text_sha256"] = hashlib.sha256(item.text.encode("utf-8")).hexdigest()
            metadata["char_length"] = len(item.text)
        if item.node_set:
            metadata["node_set"] = list(item.node_set)
        return metadata

    @staticmethod
    def _normalize_runtime_result(result: Any) -> dict[str, Any]:
        if isinstance(result, dict):
            return dict(result)
        return {"result": result}

    @staticmethod
    def _extract_counter_delta(result: dict[str, Any]) -> dict[str, int]:
        payload = result.get("counters") if isinstance(result.get("counters"), dict) else result
        counter_delta: dict[str, int] = {}
        for key in ("objects", "documents", "chunks", "graph_nodes", "graph_edges"):
            value = payload.get(key) if isinstance(payload, dict) else None
            if isinstance(value, int | float):
                counter_delta[key] = int(value)
        return counter_delta


class KnowledgeSearchService:
    """Run synchronous Knowledge search and persist search audit trails."""

    def __init__(self, runtime: CogneeRuntimeProtocol) -> None:
        self._runtime = runtime
        self._tracer = trace.get_tracer("cortex.knowledge")
        self._metrics = MetricsFacade("cortex.knowledge")

    async def search(
        self,
        *,
        uow: CortexUnitOfWork,
        caller: Any,
        request: SearchRequest,
        datasets: list[DatasetRecord],
    ) -> SearchResponse:
        started = perf_counter()
        trace_context = get_trace_context()
        dataset_ids = [dataset.dataset_id for dataset in datasets]
        dataset_keys = [dataset.dataset_key for dataset in datasets]

        with self._tracer.start_as_current_span("knowledge.search") as span:
            runtime_result: dict[str, Any]
            if dataset_ids:
                runtime_result = await self._runtime.search(
                    payload={
                        **request.model_dump(mode="json"),
                        "datasets": dataset_keys,
                        "dataset_ids": dataset_ids,
                    }
                )
            else:
                runtime_result = {"answer": None, "context_items": [], "graph_paths": []}
            latency_ms = int((perf_counter() - started) * 1000)
            response = self._normalize_search_response(
                request=request,
                runtime_result=runtime_result,
                dataset_ids=dataset_ids,
                latency_ms=latency_ms,
                trace_context=trace_context,
            )
            await uow.search_requests.add(
                SearchRequestRecord(
                    request_id=response.request_id,
                    tenant_id=caller.tenant_id,
                    dataset_scope=list(dataset_ids),
                    session_id=request.session_id,
                    search_type=request.search_type.value,
                    trace_id=trace_context.get("trace_id"),
                    span_id=trace_context.get("span_id"),
                    query_text=request.query_text,
                    filters=request.filters.model_dump(mode="json"),
                    options={
                        "top_k": request.top_k,
                        "only_context": request.only_context,
                        "include_provenance": request.include_provenance,
                        "include_graph_paths": request.include_graph_paths,
                        "timeout_seconds": request.timeout_seconds,
                    },
                    answer_text=response.answer,
                    latency_ms=latency_ms,
                    telemetry_context=response.telemetry.model_dump(mode="json")
                    if response.telemetry
                    else {},
                    deployment_context={},
                    experiment_context={},
                    created_by=caller.actor_id or caller.subject,
                    created_at=response.created_at,
                )
            )
            for hit in response.context_items:
                await uow.search_hits.add(
                    SearchHitRecord(
                        request_id=response.request_id,
                        hit_index=hit.rank,
                        hit_type=hit.hit_type.value,
                        source_id=(hit.source_id or "")[:36] or None,
                        document_id=hit.document_id,
                        object_id=hit.object_id,
                        score=hit.score,
                        title=hit.title,
                        snippet=hit.snippet,
                        citation=hit.citation.model_dump(mode="json") if hit.citation else {},
                        metadata=hit.metadata,
                    )
                )
            span.set_attribute("cortex.knowledge.search_type", request.search_type.value)
            span.set_attribute("cortex.dataset.count", len(dataset_ids))
            self._metrics.histogram(
                "cortex.search.request.duration",
                unit="ms",
                description="Latency for knowledge search requests.",
            ).record(latency_ms)
            return response

    @staticmethod
    def _normalize_search_response(
        *,
        request: SearchRequest,
        runtime_result: dict[str, Any],
        dataset_ids: list[str],
        latency_ms: int,
        trace_context: dict[str, Any],
    ) -> SearchResponse:
        request_id = new_prefixed_id("sreq")
        raw_hits = runtime_result.get("context_items")
        if raw_hits is None:
            raw_hits = runtime_result.get("hits")
        if raw_hits is None and isinstance(runtime_result.get("result"), list):
            raw_hits = runtime_result.get("result")
        context_items = KnowledgeSearchService._normalize_hits(raw_hits or [])
        graph_paths = KnowledgeSearchService._normalize_graph_paths(
            runtime_result.get("graph_paths") or []
        )
        return SearchResponse(
            request_id=request_id,
            dataset_scope=list(dataset_ids),
            search_type=request.search_type,
            answer=KnowledgeSearchService._normalize_answer(runtime_result),
            context_items=context_items,
            graph_paths=graph_paths,
            latency_ms=latency_ms,
            created_at=utc_now(),
            telemetry=TelemetryContext(
                trace_id=trace_context.get("trace_id"),
                span_id=trace_context.get("span_id"),
                request_id=trace_context.get("request_id"),
            ),
        )

    @staticmethod
    def _normalize_answer(runtime_result: dict[str, Any]) -> str | None:
        answer = runtime_result.get("answer")
        if isinstance(answer, str):
            return answer
        result = runtime_result.get("result")
        return result if isinstance(result, str) else None

    @staticmethod
    def _normalize_hits(raw_hits: list[Any]) -> list[SearchHit]:
        hits: list[SearchHit] = []
        for index, raw_hit in enumerate(raw_hits, start=1):
            payload = KnowledgeSearchService._to_mapping(raw_hit)
            payload.setdefault("rank", index)
            payload.setdefault("hit_type", "chunk")
            payload.setdefault("score", 0.0)
            if "citation" in payload and not isinstance(payload["citation"], dict):
                payload["citation"] = {}
            hits.append(SearchHit.model_validate(payload))
        return hits

    @staticmethod
    def _normalize_graph_paths(raw_paths: list[Any]) -> list[GraphPath]:
        paths: list[GraphPath] = []
        for raw_path in raw_paths:
            paths.append(GraphPath.model_validate(KnowledgeSearchService._to_mapping(raw_path)))
        return paths

    @staticmethod
    def _to_mapping(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)
        if hasattr(value, "model_dump"):
            dumped = value.model_dump(mode="json")
            return dumped if isinstance(dumped, dict) else {}
        if hasattr(value, "__dict__"):
            return {
                key: val
                for key, val in vars(value).items()
                if not key.startswith("_")
            }
        return {}
