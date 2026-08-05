from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cortex_client import CortexApiError, CortexClient, write_json
from finance_urls import FINANCE_URLS
from knowledge_graph_visualization import (
    KnowledgeGraphVisualizationError,
    visualize_knowledge_graph_from_container,
)
from models import (
    ContextGroup,
    EvaluationCase,
    EvaluationOptions,
    ExperimentReport,
    ExperimentRequest,
    KnowledgeOptions,
    MetricConfig,
    ParseArtifact,
    ParseOptions,
    TensorZeroInferenceRecord,
    TensorZeroOptions,
)
from scoring import score_answer, score_context, score_markdown
from settings import ARTIFACTS_DIR, Settings
from tensorzero_client import TensorZeroClient


class ExperimentPipeline:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.cortex = CortexClient(
            base_url=settings.cortex_base_url,
            tenant_id=settings.cortex_tenant_id,
            actor_id=settings.cortex_actor_id,
            bearer_token=settings.cortex_bearer_token,
            timeout_seconds=settings.request_timeout_seconds,
        )
        self.tensorzero = TensorZeroClient(
            gateway_url=settings.tensorzero_gateway_url,
            timeout_seconds=settings.request_timeout_seconds,
        )

    def close(self) -> None:
        self.cortex.close()
        self.tensorzero.close()

    def run(self, request: ExperimentRequest) -> ExperimentReport:
        run_id = f"tzcx_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        run_dir = ARTIFACTS_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        parse_options = _resolve_parse_options(request, self.settings)
        knowledge_options = _resolve_knowledge_options(request, self.settings)
        tensorzero_options = _resolve_tensorzero_options(request, self.settings)
        evaluation_options = _resolve_evaluation_options(request, self.settings)
        query = request.query or self.settings.default_query
        max_urls = parse_options.max_urls or self.settings.max_urls
        parse_engines = parse_options.engines or list(self.settings.parse_engines)
        parse_mode = (parse_options.mode or self.settings.parse_mode).lower()
        if parse_mode not in {"sync", "async"}:
            raise ValueError("parse_mode must be `sync` or `async`.")
        cortex_eval_mode = (evaluation_options.mode or self.settings.cortex_eval_mode).lower()
        if cortex_eval_mode not in {"sync", "async"}:
            raise ValueError("cortex_eval_mode must be `sync` or `async`.")
        submit_cortex_eval = bool(evaluation_options.enabled)
        source_urls = FINANCE_URLS[:max_urls]
        dataset_key = f"tensorzero_cortex_{run_id}"

        self.tensorzero.status(timeout_seconds=self.settings.tensorzero_ready_timeout_seconds)
        self.cortex.ensure_token()

        parse_artifacts = self._parse_and_store(
            run_dir=run_dir,
            urls=source_urls,
            engines=parse_engines,
            mode=parse_mode,
            engine_modes=parse_options.engine_modes,
            scene=parse_options.scene,
            timeout_seconds=parse_options.timeout_seconds,
        )
        object_ids = [artifact.object_id for artifact in parse_artifacts if artifact.object_id]
        knowledge_artifacts = [
            artifact
            for artifact in parse_artifacts
            if not artifact.error and artifact.context_excerpt
        ]

        knowledge_events: dict[str, Any] = {
            "enabled": knowledge_options.enabled,
            "status": "skipped",
        }
        if knowledge_options.enabled and knowledge_artifacts:
            try:
                knowledge_events = self._build_knowledge(
                    dataset_key=dataset_key,
                    parse_artifacts=knowledge_artifacts,
                    timeout_seconds=knowledge_options.build_timeout_seconds,
                )
                knowledge_events["enabled"] = True
                knowledge_events["status"] = "built"
                if knowledge_options.visualize_graph:
                    try:
                        graph_path = visualize_knowledge_graph_from_container(
                            run_id=run_id,
                            container_name=self.settings.knowledge_worker_container,
                            dataset_key=dataset_key,
                        )
                        knowledge_events["graph_visualization_path"] = str(graph_path)
                    except KnowledgeGraphVisualizationError as exc:
                        knowledge_events["graph_visualization_error"] = str(exc)
            except (CortexApiError, RuntimeError) as exc:
                knowledge_events = {
                    "enabled": True,
                    "status": "failed",
                    "error": str(exc),
                    "fallback": "parse_artifacts",
                }
        elif knowledge_options.enabled:
            knowledge_events["reason"] = "no_parse_text"

        search_result = self._search_or_fallback(
            dataset_key=dataset_key,
            query=query,
            parse_artifacts=parse_artifacts,
            knowledge_events=knowledge_events,
            search_type=knowledge_options.search_type or self.settings.knowledge_search_type,
            top_k=knowledge_options.top_k,
            fallback_to_parse_artifacts=knowledge_options.fallback_to_parse_artifacts,
        )
        context_source = str(search_result.get("source") or "knowledge")
        expected_keywords = _expected_keywords(source_urls)
        context_groups, context_texts = _context_groups(
            search_result=search_result,
            parse_artifacts=parse_artifacts,
            grouping=tensorzero_options.context_grouping,
            max_chars=tensorzero_options.max_context_chars_per_group,
            expected_keywords=expected_keywords,
        )

        if context_source != "knowledge":
            knowledge_events.setdefault("fallback", context_source)
            knowledge_events.setdefault(
                "fallback_reason",
                search_result.get("reason") or search_result.get("error"),
            )

        parse_score = _average(
            [artifact.parse_score for artifact in parse_artifacts if not artifact.error]
        )
        tensorzero_records = self._run_tensorzero_matrix(
            run_id=run_id,
            dataset_key=dataset_key,
            query=query,
            parse_engines=parse_engines,
            parse_mode=parse_mode,
            object_ids=object_ids,
            context_groups=context_groups,
            context_texts=context_texts,
            expected_keywords=expected_keywords,
            parse_score=parse_score,
            options=tensorzero_options,
        )

        eval_cases = _evaluation_cases(
            query=query,
            expected_keywords=expected_keywords,
            records=tensorzero_records,
            context_texts=context_texts,
            run_id=run_id,
            dataset_key=dataset_key,
            cortex_eval_mode=cortex_eval_mode,
            knowledge_events=knowledge_events,
            max_cases=evaluation_options.max_cases,
            max_context_chars_per_case=evaluation_options.max_context_chars_per_case,
        )
        eval_dataset_path = run_dir / "tensorzero_eval_dataset.jsonl"
        eval_dataset_path.write_text(
            "\n".join(json.dumps(case.model_dump(), ensure_ascii=False) for case in eval_cases)
            + ("\n" if eval_cases else ""),
            encoding="utf-8",
        )

        cortex_eval_result = None
        if submit_cortex_eval and eval_cases:
            cortex_eval_result = self._submit_cortex_eval(
                run_id=run_id,
                eval_cases=eval_cases,
                mode=cortex_eval_mode,
                options=evaluation_options,
            )
            write_json(run_dir / "cortex_eval_result.json", cortex_eval_result)

        answer_scores = [
            float(record.scores["llm_answer_quality"])
            for record in tensorzero_records
            if "llm_answer_quality" in record.scores and not record.error
        ]
        context_scores = [group.context_score for group in context_groups]
        e2e_values = [
            bool(record.scores["rag_end_to_end_pass"])
            for record in tensorzero_records
            if "rag_end_to_end_pass" in record.scores and not record.error
        ]
        scorecard = {
            "parse_markdown_quality": parse_score,
            "rag_context_quality": _average(context_scores),
            "llm_answer_quality": _average(answer_scores),
            "rag_end_to_end_pass_rate": _bool_rate(e2e_values),
            "rag_end_to_end_pass": bool(e2e_values) and all(e2e_values),
            "tensorzero_strategy": tensorzero_options.strategy,
            "tensorzero_variants_requested": tensorzero_options.variants,
            "tensorzero_variant_counts": _variant_counts(tensorzero_records),
            "tensorzero_inference_count": len(
                [record for record in tensorzero_records if record.inference_id]
            ),
            "tensorzero_error_count": len(
                [record for record in tensorzero_records if record.error]
            ),
            "parse_success_count": len([item for item in parse_artifacts if not item.error]),
            "parse_failure_count": len([item for item in parse_artifacts if item.error]),
            "parse_by_engine": _parse_summary_by_engine(parse_artifacts),
            "context_group_count": len(context_groups),
            "context_source": context_source,
            "knowledge_status": knowledge_events.get("status"),
            "cortex_eval_mode": cortex_eval_mode if submit_cortex_eval else "disabled",
            "cortex_eval_types": evaluation_options.eval_types if submit_cortex_eval else [],
        }

        report_json_path = run_dir / "report.json"
        report_markdown_path = run_dir / "report.md"
        report = ExperimentReport(
            run_id=run_id,
            dataset_key=dataset_key,
            tensorzero_gateway_url=self.settings.tensorzero_gateway_url,
            tensorzero_ui_url=self.settings.tensorzero_ui_url,
            parse_artifacts=parse_artifacts,
            context_groups=context_groups,
            tensorzero_inferences=tensorzero_records,
            evaluation_cases=eval_cases,
            scorecard=scorecard,
            report_json_path=str(report_json_path),
            report_markdown_path=str(report_markdown_path),
            eval_dataset_jsonl_path=str(eval_dataset_path),
            knowledge_graph_html_path=knowledge_events.get("graph_visualization_path"),
            cortex_eval_result=cortex_eval_result,
        )
        write_json(report_json_path, report.model_dump())
        report_markdown_path.write_text(_render_markdown_report(report), encoding="utf-8")
        write_json(run_dir / "raw_search_result.json", search_result)
        write_json(
            run_dir / "raw_tensorzero_result.json",
            [record.model_dump() for record in tensorzero_records],
        )
        return report

    def _parse_and_store(
        self,
        *,
        run_dir: Path,
        urls: list[dict[str, object]],
        engines: list[str],
        mode: str,
        engine_modes: dict[str, str],
        scene: str | None,
        timeout_seconds: int,
    ) -> list[ParseArtifact]:
        artifacts: list[ParseArtifact] = []
        for source in urls:
            url = str(source["url"])
            expected_keywords = [str(item) for item in source.get("expected_keywords", [])]  # type: ignore
            for engine_id in engines:
                engine_mode = _mode_for_engine(
                    engine_id,
                    default_mode=mode,
                    engine_modes=engine_modes,
                )
                artifact = ParseArtifact(
                    url=url,
                    url_name=str(source["name"]),
                    engine_id=engine_id,
                    parse_mode=engine_mode,
                    metadata={"format_hint": source.get("format_hint")},
                )
                try:
                    if engine_mode == "async":
                        parsed = self.cortex.parse_async(
                            sources=[url],
                            engine_id=engine_id,
                            scene=scene,
                            timeout_seconds=timeout_seconds,
                        )
                    else:
                        parsed = self.cortex.parse_sync(
                            sources=[url],
                            engine_id=engine_id,
                            scene=scene,
                        )
                    result = (parsed.get("results") or [{}])[0]
                    document = result.get("document") or {}
                    markdown = str(document.get("markdown") or "")
                    artifact.context_excerpt = _context_excerpt(markdown)
                    artifact.job_id = result.get("job_id") or _first_job_id(parsed)
                    document_id = document.get("document_id")
                    artifact.document_id = str(document_id) if document_id else None
                    artifact.markdown_chars = len(markdown)
                    artifact.parse_score = score_markdown(markdown, expected_keywords)
                    artifact.metadata.update(
                        {
                            "parser": document.get("parser"),
                            "source_format": document.get("source_format"),
                            "title": document.get("title"),
                            "markdown_sha256": document.get("markdown_sha256"),
                        }
                    )
                    stored = self.cortex.upload_markdown(
                        filename=_safe_filename(f"{source['name']}-{engine_id}.md"),
                        markdown=_markdown_with_metadata(source, engine_id, document, markdown),
                        metadata={
                            "run": "tensorzero-cortex",
                            "source_url": url,
                            "source_name": source["name"],
                            "engine_id": engine_id,
                            "parse_mode": engine_mode,
                            "job_id": artifact.job_id,
                            "parse_score": artifact.parse_score,
                        },
                        tags=["tensorzero", "finance", "parsed-markdown", engine_id],
                    )
                    artifact.object_id = stored.get("object_id") or stored.get("upload_id")
                    write_json(
                        run_dir
                        / "parse"
                        / f"{_safe_filename(str(source['name']))}-{engine_id}.json",
                        {"parse": parsed, "storage": stored},
                    )
                except Exception as exc:  # noqa: BLE001 - examples should keep running across flaky URLs.
                    artifact.error = str(exc)
                artifacts.append(artifact)
        return artifacts

    def _build_knowledge(
        self,
        *,
        dataset_key: str,
        parse_artifacts: list[ParseArtifact],
        timeout_seconds: int,
    ) -> dict[str, Any]:
        dataset = self.cortex.create_dataset(
            dataset_key=dataset_key,
            display_name=f"TensorZero Cortex {dataset_key}",
            description=(
                "Parsed financial and macroeconomic Markdown for TensorZero adaptive A/B testing."
            ),
        )
        documents = [
            {
                "text": _knowledge_ingest_text(artifact),
                "label": f"{artifact.url_name} via {artifact.engine_id}",
                "metadata": {
                    "source_url": artifact.url,
                    "source_name": artifact.url_name,
                    "engine_id": artifact.engine_id,
                    "parse_mode": artifact.parse_mode,
                    "object_id": artifact.object_id,
                    "document_id": artifact.document_id,
                    "markdown_chars": artifact.markdown_chars,
                    "parse_score": artifact.parse_score,
                },
            }
            for artifact in parse_artifacts
            if artifact.context_excerpt
        ]
        add_job = self.cortex.add_texts_to_knowledge(
            dataset_key=dataset_key,
            documents=documents,
        )
        self.cortex.wait_job(add_job["job_id"], timeout_seconds=timeout_seconds)
        cognify_job = self.cortex.cognify(dataset_key=dataset_key)
        self.cortex.wait_job(cognify_job["job_id"], timeout_seconds=timeout_seconds)
        return {
            "dataset": dataset,
            "add_job": add_job,
            "cognify_job": cognify_job,
            "input_type": "text",
            "input_count": len(documents),
        }

    def _search_or_fallback(
        self,
        *,
        dataset_key: str,
        query: str,
        parse_artifacts: list[ParseArtifact],
        knowledge_events: dict[str, Any],
        search_type: str,
        top_k: int,
        fallback_to_parse_artifacts: bool,
    ) -> dict[str, Any]:
        if knowledge_events.get("status") == "built":
            try:
                search_result = self.cortex.search_knowledge(
                    dataset_key=dataset_key,
                    query=query,
                    search_type=search_type,
                    top_k=top_k,
                )
                search_result.setdefault("source", "knowledge")
                return search_result
            except CortexApiError as exc:
                if not fallback_to_parse_artifacts:
                    raise
                return _fallback_search_result(
                    parse_artifacts=parse_artifacts,
                    reason="knowledge_search_failed",
                    error=str(exc),
                )

        if not fallback_to_parse_artifacts:
            return {
                "source": "empty",
                "reason": str(knowledge_events.get("status") or "knowledge_disabled"),
                "error": knowledge_events.get("error"),
                "results": [],
            }
        return _fallback_search_result(
            parse_artifacts=parse_artifacts,
            reason=str(knowledge_events.get("status") or "knowledge_disabled"),
            error=knowledge_events.get("error"),
        )

    def _run_tensorzero_matrix(
        self,
        *,
        run_id: str,
        dataset_key: str,
        query: str,
        parse_engines: list[str],
        parse_mode: str,
        object_ids: list[str],
        context_groups: list[ContextGroup],
        context_texts: dict[str, str],
        expected_keywords: list[str],
        parse_score: float,
        options: TensorZeroOptions,
    ) -> list[TensorZeroInferenceRecord]:
        records: list[TensorZeroInferenceRecord] = []
        variants = _variant_sequence(options)
        for group in context_groups:
            context = context_texts.get(group.context_id, "")
            for variant_name in variants:
                requested_variant = variant_name if variant_name != "__adaptive__" else None
                record = TensorZeroInferenceRecord(
                    context_id=group.context_id,
                    context_source=group.source,
                    parse_engine_id=group.parse_engine_id,
                    variant_name=requested_variant,
                    metadata={
                        "requested_variant": requested_variant,
                        "strategy": options.strategy,
                    },
                )
                try:
                    result = self.tensorzero.inference(
                        question=query,
                        context=context,
                        variant_name=requested_variant,
                        include_raw_response=options.include_raw_response,
                        metadata={
                            "run_id": run_id,
                            "dataset_key": dataset_key,
                            "parse_engines": parse_engines,
                            "parse_mode": parse_mode,
                            "object_ids": object_ids,
                            "context_id": group.context_id,
                            "context_source": group.source,
                            "parse_engine_id": group.parse_engine_id,
                            "tensorzero_strategy": options.strategy,
                            "requested_variant": requested_variant,
                        },
                    )
                    output = result["output"]
                    answer_text = _answer_text(output)
                    answer_score = score_answer(output, expected_keywords)
                    e2e_pass = (
                        parse_score >= 0.45 and group.context_score >= 0.35 and answer_score >= 0.45
                    )
                    record.inference_id = result.get("inference_id")
                    record.episode_id = result.get("episode_id")
                    record.variant_name = result.get("variant_name") or requested_variant
                    record.output = output
                    record.answer_text = answer_text
                    record.usage = dict(result.get("usage") or {})
                    record.finish_reason = result.get("finish_reason")
                    record.scores = {
                        "parse_markdown_quality": parse_score,
                        "rag_context_quality": group.context_score,
                        "llm_answer_quality": answer_score,
                        "rag_end_to_end_pass": e2e_pass,
                    }
                    if options.feedback_enabled:
                        record.feedback_errors = self._send_tensorzero_feedback(
                            record=record,
                            run_id=run_id,
                            dataset_key=dataset_key,
                        )
                except Exception as exc:  # noqa: BLE001 - matrix runs should isolate failures.
                    record.error = str(exc)
                records.append(record)
        return records

    def _send_tensorzero_feedback(
        self,
        *,
        record: TensorZeroInferenceRecord,
        run_id: str,
        dataset_key: str,
    ) -> list[str]:
        tags = {
            "run_id": run_id,
            "dataset_key": dataset_key,
            "context_id": record.context_id,
            "context_source": record.context_source,
            "parse_engine_id": record.parse_engine_id or "mixed",
            "variant_name": record.variant_name or "adaptive",
        }
        errors: list[str] = []
        for metric_name, value in record.scores.items():
            try:
                self.tensorzero.feedback(
                    metric_name=metric_name,
                    value=value,
                    inference_id=record.inference_id,
                    tags=tags,
                )
            except Exception as exc:  # noqa: BLE001 - record feedback failures, keep report useful.
                errors.append(f"{metric_name}: {exc}")
        return errors

    def _submit_cortex_eval(
        self,
        *,
        run_id: str,
        eval_cases: list[EvaluationCase],
        mode: str,
        options: EvaluationOptions,
    ) -> dict[str, Any]:
        test_cases = [
            {
                "user_input": case.query,
                "actual_output": case.actual_output,
                "expected_output": ", ".join(case.expected_keywords),
                "retrieval_contexts": case.retrieval_contexts,
                "metadata": case.metadata,
            }
            for case in eval_cases
        ]
        results: dict[str, Any] = {"mode": mode, "engine_id": options.engine_id, "runs": {}}
        for eval_type in options.eval_types:
            metrics = _metrics_for_eval_type(eval_type, options)
            kwargs = {
                "name": f"TensorZero Cortex {eval_type.upper()} Eval {run_id}",
                "test_cases": test_cases,
                "eval_type": eval_type,
                "engine_id": options.engine_id,
                "metrics": metrics,
                "persist_report_object": options.persist_report_object,
            }
            try:
                if mode == "async":
                    results["runs"][eval_type] = self.cortex.run_eval_async(
                        **kwargs,
                        timeout_seconds=options.async_timeout_seconds or 3600,
                    )
                else:
                    results["runs"][eval_type] = self.cortex.run_eval_sync(**kwargs)
            except Exception as exc:  # noqa: BLE001 - one eval profile should not hide the rest.
                results["runs"][eval_type] = {"status": "failed", "error": str(exc)}
        return results


def _markdown_with_metadata(
    source: dict[str, object],
    engine_id: str,
    document: dict[str, Any],
    markdown: str,
) -> str:
    metadata = {
        "source_name": source["name"],
        "source_url": source["url"],
        "format_hint": source.get("format_hint"),
        "engine_id": engine_id,
        "document_id": document.get("document_id"),
        "title": document.get("title"),
    }
    return "---\n" + json.dumps(metadata, ensure_ascii=False, indent=2) + "\n---\n\n" + markdown


def _search_context(search_result: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("results", "items", "chunks", "contexts"):
        values = search_result.get(key)
        if isinstance(values, list):
            for item in values:
                if isinstance(item, dict):
                    text = (
                        item.get("text")
                        or item.get("content")
                        or item.get("chunk_text")
                        or item.get("markdown")
                        or json.dumps(item, ensure_ascii=False)
                    )
                    parts.append(str(text))
                else:
                    parts.append(str(item))
    if not parts:
        parts.append(json.dumps(search_result, ensure_ascii=False))
    return "\n\n---\n\n".join(parts)[:24000]


def _context_groups(
    *,
    search_result: dict[str, Any],
    parse_artifacts: list[ParseArtifact],
    grouping: str,
    max_chars: int,
    expected_keywords: list[str],
) -> tuple[list[ContextGroup], dict[str, str]]:
    normalized = grouping.strip().lower()
    if normalized not in {"combined", "by_parse_engine", "knowledge_or_parse"}:
        raise ValueError(
            "tensorzero.context_grouping must be combined, by_parse_engine, or knowledge_or_parse."
        )

    groups: list[ContextGroup] = []
    texts: dict[str, str] = {}

    search_source = str(search_result.get("source") or "knowledge")
    if normalized == "combined" or (
        normalized == "knowledge_or_parse" and search_source == "knowledge"
    ):
        text = _search_context(search_result)[:max_chars]
        group = ContextGroup(
            context_id="knowledge:combined" if search_source == "knowledge" else "parse:combined",
            source=search_source,
            context_chars=len(text),
            context_score=score_context(text, expected_keywords),
            text_preview=text[:1000],
            metadata={"grouping": normalized},
        )
        groups.append(group)
        texts[group.context_id] = text
        return groups, texts

    by_engine: dict[str, list[ParseArtifact]] = {}
    for artifact in parse_artifacts:
        if artifact.error or not artifact.context_excerpt:
            continue
        by_engine.setdefault(artifact.engine_id, []).append(artifact)

    if normalized == "combined" and by_engine:
        all_artifacts = [artifact for artifacts in by_engine.values() for artifact in artifacts]
        text = _format_artifact_context(all_artifacts, max_chars=max_chars)
        group = ContextGroup(
            context_id="parse:combined",
            source="parse_artifact",
            object_ids=[artifact.object_id for artifact in all_artifacts if artifact.object_id],
            document_ids=[
                artifact.document_id for artifact in all_artifacts if artifact.document_id
            ],
            context_chars=len(text),
            context_score=score_context(text, expected_keywords),
            text_preview=text[:1000],
            metadata={"grouping": normalized},
        )
        groups.append(group)
        texts[group.context_id] = text
        return groups, texts

    for engine_id, artifacts in sorted(by_engine.items()):
        text = _format_artifact_context(artifacts, max_chars=max_chars)
        group = ContextGroup(
            context_id=f"parse_engine:{engine_id}",
            source="parse_artifact",
            parse_engine_id=engine_id,
            object_ids=[artifact.object_id for artifact in artifacts if artifact.object_id],
            document_ids=[artifact.document_id for artifact in artifacts if artifact.document_id],
            context_chars=len(text),
            context_score=score_context(text, expected_keywords),
            text_preview=text[:1000],
            metadata={"artifact_count": len(artifacts), "grouping": normalized},
        )
        groups.append(group)
        texts[group.context_id] = text

    if not groups:
        text = _search_context(search_result)[:max_chars]
        group = ContextGroup(
            context_id="empty:fallback",
            source=search_source,
            context_chars=len(text),
            context_score=score_context(text, expected_keywords),
            text_preview=text[:1000],
            metadata={"grouping": normalized, "fallback": True},
        )
        groups.append(group)
        texts[group.context_id] = text
    return groups, texts


def _format_artifact_context(artifacts: list[ParseArtifact], *, max_chars: int) -> str:
    parts: list[str] = []
    remaining = max_chars
    for artifact in artifacts:
        if remaining <= 0:
            break
        header = (
            f"Source: {artifact.url_name}\n"
            f"URL: {artifact.url}\n"
            f"Parse engine: {artifact.engine_id}\n"
            f"Object ID: {artifact.object_id or ''}\n\n"
        )
        excerpt = artifact.context_excerpt or ""
        chunk = (header + excerpt).strip()
        if not chunk:
            continue
        chunk = chunk[:remaining]
        parts.append(chunk)
        remaining -= len(chunk)
    return "\n\n---\n\n".join(parts)[:max_chars]


def _context_excerpt(markdown: str, *, max_chars: int = 6000) -> str | None:
    cleaned = markdown.strip()
    if not cleaned:
        return None
    return cleaned[:max_chars]


def _knowledge_ingest_text(artifact: ParseArtifact) -> str:
    metadata = {
        "source_name": artifact.url_name,
        "source_url": artifact.url,
        "parse_engine": artifact.engine_id,
        "parse_mode": artifact.parse_mode,
        "object_id": artifact.object_id,
        "document_id": artifact.document_id,
        "markdown_chars": artifact.markdown_chars,
    }
    header = "---\n" + json.dumps(metadata, ensure_ascii=False, indent=2) + "\n---\n\n"
    return header + (artifact.context_excerpt or "")


def _fallback_search_result(
    *,
    parse_artifacts: list[ParseArtifact],
    reason: str,
    error: object | None = None,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for artifact in parse_artifacts:
        if artifact.error or not artifact.context_excerpt:
            continue
        results.append(
            {
                "text": artifact.context_excerpt,
                "source_url": artifact.url,
                "source_name": artifact.url_name,
                "engine_id": artifact.engine_id,
                "object_id": artifact.object_id,
                "document_id": artifact.document_id,
            }
        )
    return {
        "source": "parse_artifact_fallback",
        "reason": reason,
        "error": str(error) if error else None,
        "results": results,
    }


def _resolve_parse_options(request: ExperimentRequest, settings: Settings) -> ParseOptions:
    if request.parse is None:
        options = ParseOptions(
            max_urls=request.max_urls or settings.max_urls,
            engines=request.parse_engines or list(settings.parse_engines),
            mode=request.parse_mode or settings.parse_mode,
        )
    else:
        options = request.parse.model_copy(
            update={
                "max_urls": request.parse.max_urls or request.max_urls or settings.max_urls,
                "engines": request.parse.engines
                or request.parse_engines
                or list(settings.parse_engines),
                "mode": request.parse.mode or request.parse_mode or settings.parse_mode,
            }
        )
    engine_modes = {"docling": "async", **dict(options.engine_modes or {})}
    return options.model_copy(update={"engine_modes": engine_modes})


def _resolve_knowledge_options(
    request: ExperimentRequest,
    settings: Settings,
) -> KnowledgeOptions:
    if request.knowledge is None:
        return KnowledgeOptions(
            enabled=request.run_knowledge_jobs,
            search_type=settings.knowledge_search_type,
            visualize_graph=settings.knowledge_graph_visualization,
        )
    enabled = request.knowledge.enabled
    if enabled is None:
        enabled = request.run_knowledge_jobs
    return request.knowledge.model_copy(
        update={
            "enabled": enabled,
            "search_type": request.knowledge.search_type or settings.knowledge_search_type,
            "visualize_graph": (
                request.knowledge.visualize_graph
                if request.knowledge.visualize_graph is not None
                else settings.knowledge_graph_visualization
            ),
        }
    )


def _resolve_tensorzero_options(
    request: ExperimentRequest,
    settings: Settings,
) -> TensorZeroOptions:
    if request.tensorzero is None:
        return TensorZeroOptions(
            strategy=settings.tensorzero_strategy,
            variants=list(settings.tensorzero_variants),
            context_grouping=settings.tensorzero_context_grouping,
            max_context_chars_per_group=settings.tensorzero_max_context_chars_per_group,
        )
    return request.tensorzero


def _resolve_evaluation_options(
    request: ExperimentRequest,
    settings: Settings,
) -> EvaluationOptions:
    enabled = (
        settings.submit_cortex_eval
        if request.submit_cortex_eval is None
        else request.submit_cortex_eval
    )
    if request.evaluation is None:
        return EvaluationOptions(
            enabled=enabled,
            mode=request.cortex_eval_mode or settings.cortex_eval_mode,
            eval_types=list(settings.cortex_eval_types),
            metric_profile=settings.cortex_eval_metric_profile,
        )
    update: dict[str, Any] = {
        "enabled": (
            request.evaluation.enabled if request.evaluation.enabled is not None else enabled
        ),
        "mode": request.evaluation.mode or request.cortex_eval_mode or settings.cortex_eval_mode,
    }
    if not request.evaluation.eval_types:
        update["eval_types"] = list(settings.cortex_eval_types)
    if not request.evaluation.metric_profile:
        update["metric_profile"] = settings.cortex_eval_metric_profile
    return request.evaluation.model_copy(update=update)


def _mode_for_engine(
    engine_id: str,
    *,
    default_mode: str,
    engine_modes: dict[str, str],
) -> str:
    mode = engine_modes.get(engine_id, default_mode).strip().lower()
    if mode not in {"sync", "async"}:
        raise ValueError(f"Parse mode `{mode}` for engine `{engine_id}` must be sync or async.")
    return mode


def _variant_sequence(options: TensorZeroOptions) -> list[str]:
    strategy = options.strategy.strip().lower()
    if strategy not in {"adaptive", "exhaustive", "selected"}:
        raise ValueError("tensorzero.strategy must be adaptive, exhaustive, or selected.")
    variants = [variant.strip() for variant in options.variants if variant.strip()]
    if strategy == "adaptive":
        return ["__adaptive__"]
    if not variants:
        raise ValueError("tensorzero.variants must contain at least one variant for pinned runs.")
    if strategy == "selected":
        return [variants[0]]
    return variants


def _evaluation_cases(
    *,
    query: str,
    expected_keywords: list[str],
    records: list[TensorZeroInferenceRecord],
    context_texts: dict[str, str],
    run_id: str,
    dataset_key: str,
    cortex_eval_mode: str,
    knowledge_events: dict[str, Any],
    max_cases: int | None = None,
    max_context_chars_per_case: int | None = None,
) -> list[EvaluationCase]:
    cases: list[EvaluationCase] = []
    for record in records:
        if record.error or not record.answer_text.strip():
            continue
        context = context_texts.get(record.context_id, "")
        if max_context_chars_per_case:
            context = context[:max_context_chars_per_case]
        cases.append(
            EvaluationCase(
                query=query,
                actual_output=record.answer_text,
                expected_keywords=expected_keywords,
                retrieval_contexts=[context],
                metadata={
                    "run_id": run_id,
                    "dataset_key": dataset_key,
                    "context_id": record.context_id,
                    "context_source": record.context_source,
                    "parse_engine_id": record.parse_engine_id,
                    "tensorzero_inference_id": record.inference_id,
                    "tensorzero_episode_id": record.episode_id,
                    "tensorzero_variant": record.variant_name,
                    "tensorzero_usage": record.usage,
                    "tensorzero_finish_reason": record.finish_reason,
                    "scores": record.scores,
                    "cortex_eval_mode": cortex_eval_mode,
                    "knowledge_events": knowledge_events,
                },
            )
        )
        if max_cases and len(cases) >= max_cases:
            break
    return cases


def _answer_text(output: Any) -> str:
    if isinstance(output, str):
        return output
    if isinstance(output, dict):
        if "answer" in output:
            return str(output["answer"])
        if "raw" in output and isinstance(output["raw"], str):
            return output["raw"]
    return json.dumps(output, ensure_ascii=False)


def _metrics_for_eval_type(
    eval_type: str,
    options: EvaluationOptions,
) -> list[dict[str, Any]]:
    if options.metrics_by_type and eval_type in options.metrics_by_type:
        return [_metric_to_payload(metric) for metric in options.metrics_by_type[eval_type]]

    profile = options.metric_profile.strip().lower()
    if profile == "deepeval_local_smoke":
        if eval_type == "custom":
            metrics = [
                MetricConfig(metric_key="custom.g_eval", threshold=0.6, weight=1.0),
            ]
        else:
            metrics = [
                MetricConfig(metric_key="rag.answer_relevance", threshold=0.6, weight=1.0),
            ]
    elif profile == "deepeval_quality_core" or eval_type == "custom":
        metrics = [
            MetricConfig(metric_key="quality.correctness", threshold=0.65, weight=0.35),
            MetricConfig(metric_key="quality.completeness", threshold=0.65, weight=0.25),
            MetricConfig(metric_key="quality.relevance", threshold=0.65, weight=0.25),
            MetricConfig(metric_key="custom.g_eval", threshold=0.65, weight=0.15),
        ]
    elif profile == "deepeval_agentic_core" or eval_type == "agentic":
        metrics = [
            MetricConfig(metric_key="agent.task_completion", threshold=0.7, weight=0.45),
            MetricConfig(metric_key="agent.goal_success", threshold=0.7, weight=0.35),
            MetricConfig(metric_key="agent.reasoning_quality", threshold=0.65, weight=0.2),
        ]
    elif eval_type == "multi_turn":
        metrics = [
            MetricConfig(
                metric_key="dialog.conversation_relevancy",
                threshold=0.7,
                weight=0.5,
            ),
            MetricConfig(
                metric_key="dialog.conversation_completeness",
                threshold=0.7,
                weight=0.5,
            ),
        ]
    else:
        metrics = [
            MetricConfig(metric_key="rag.answer_relevance", threshold=0.65, weight=0.25),
            MetricConfig(metric_key="rag.faithfulness", threshold=0.65, weight=0.25),
            MetricConfig(metric_key="rag.contextual_precision", threshold=0.6, weight=0.2),
            MetricConfig(metric_key="rag.contextual_recall", threshold=0.6, weight=0.2),
            MetricConfig(metric_key="rag.contextual_relevance", threshold=0.6, weight=0.1),
        ]
    return [_metric_to_payload(metric) for metric in metrics]


def _metric_to_payload(metric: MetricConfig) -> dict[str, Any]:
    return metric.model_dump(exclude_none=True)


def _expected_keywords(urls: list[dict[str, object]]) -> list[str]:
    keywords: list[str] = []
    for source in urls:
        keywords.extend(str(item) for item in source.get("expected_keywords", []))  # type: ignore
    deduped = list(dict.fromkeys(keyword.lower() for keyword in keywords))
    return deduped[:30]


def _first_job_id(parsed: dict[str, Any]) -> str | None:
    jobs = parsed.get("jobs") or []
    if jobs and isinstance(jobs[0], dict):
        job_id = jobs[0].get("job_id")
        return str(job_id) if job_id else None
    job_statuses = parsed.get("job_statuses") or []
    if job_statuses and isinstance(job_statuses[0], dict):
        job_id = job_statuses[0].get("job_id")
        return str(job_id) if job_id else None
    return None


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)


def _bool_rate(values: list[bool]) -> float:
    if not values:
        return 0.0
    return round(sum(1 for value in values if value) / len(values), 4)


def _variant_counts(records: list[TensorZeroInferenceRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        variant = record.variant_name or "unknown"
        counts[variant] = counts.get(variant, 0) + 1
    return counts


def _parse_summary_by_engine(artifacts: list[ParseArtifact]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for artifact in artifacts:
        bucket = summary.setdefault(
            artifact.engine_id,
            {"success": 0, "failure": 0, "avg_score": 0.0, "markdown_chars": 0},
        )
        if artifact.error:
            bucket["failure"] += 1
        else:
            bucket["success"] += 1
            bucket["markdown_chars"] += artifact.markdown_chars
    for engine_id, bucket in summary.items():
        scores = [
            artifact.parse_score
            for artifact in artifacts
            if artifact.engine_id == engine_id and not artifact.error
        ]
        bucket["avg_score"] = _average(scores)
    return summary


def _safe_filename(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")
    return (name or "artifact")[:120]


def _render_markdown_report(report: ExperimentReport) -> str:
    rows = "\n".join(
        f"| {item.url_name} | `{item.engine_id}` | `{item.parse_mode}` | "
        f"{item.markdown_chars} | {item.parse_score:.3f} | {item.object_id or ''} | "
        f"{_one_line(item.error or '')} |"
        for item in report.parse_artifacts
    )
    context_rows = "\n".join(
        f"| `{group.context_id}` | {group.source} | `{group.parse_engine_id or ''}` | "
        f"{group.context_chars} | {group.context_score:.3f} |"
        for group in report.context_groups
    )
    inference_rows = "\n".join(
        f"| `{item.variant_name or ''}` | `{item.context_id}` | `{item.parse_engine_id or ''}` | "
        f"{item.scores.get('llm_answer_quality', '')} | "
        f"{item.scores.get('rag_end_to_end_pass', '')} | "
        f"`{item.inference_id or ''}` | {_one_line(item.error or '')} |"
        for item in report.tensorzero_inferences
    )
    cases = "\n".join(
        f"- `{case.metadata.get('tensorzero_variant')}` on "
        f"`{case.metadata.get('context_id')}`: {case.query}"
        for case in report.evaluation_cases
    )
    scorecard = "\n".join(f"- `{key}`: {value}" for key, value in report.scorecard.items())
    return f"""# TensorZero Cortex Experiment Report

- Run ID: `{report.run_id}`
- Dataset: `{report.dataset_key}`
- TensorZero Gateway: {report.tensorzero_gateway_url}
- TensorZero UI: {report.tensorzero_ui_url}

## Scorecard

{scorecard}

## Parse Artifacts

| URL | Engine | Mode | Markdown chars | Parse score | Object ID | Error |
| --- | --- | --- | ---: | ---: | --- | --- |
{rows}

## Context Groups

| Context | Source | Parse Engine | Chars | Context score |
| --- | --- | --- | ---: | ---: |
{context_rows}

## TensorZero Inferences

| Variant | Context | Parse Engine | Answer score | E2E pass | Inference ID | Error |
| --- | --- | --- | ---: | --- | --- | --- |
{inference_rows}

## Evaluation Cases

{cases}

## Artifacts

- Eval dataset JSONL: `{report.eval_dataset_jsonl_path}`
- Knowledge graph HTML: `{report.knowledge_graph_html_path or "not generated"}`
- JSON report: `{report.report_json_path}`
"""


def _one_line(value: str, *, max_chars: int = 180) -> str:
    return value.replace("\r", " ").replace("\n", " ")[:max_chars]
