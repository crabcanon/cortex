from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .cortex_client import CortexApiError, CortexClient, write_json
from .finance_urls import FINANCE_URLS
from .models import EvaluationCase, ExperimentReport, ExperimentRequest, ParseArtifact
from .scoring import score_answer, score_context, score_markdown
from .settings import ARTIFACTS_DIR, Settings
from .tensorzero_client import TensorZeroClient


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

        query = request.query or self.settings.default_query
        max_urls = request.max_urls or self.settings.max_urls
        parse_engines = request.parse_engines or list(self.settings.parse_engines)
        parse_mode = (request.parse_mode or self.settings.parse_mode).lower()
        if parse_mode not in {"sync", "async"}:
            raise ValueError("parse_mode must be `sync` or `async`.")
        cortex_eval_mode = (request.cortex_eval_mode or self.settings.cortex_eval_mode).lower()
        if cortex_eval_mode not in {"sync", "async"}:
            raise ValueError("cortex_eval_mode must be `sync` or `async`.")
        submit_cortex_eval = (
            self.settings.submit_cortex_eval
            if request.submit_cortex_eval is None
            else request.submit_cortex_eval
        )
        source_urls = FINANCE_URLS[:max_urls]
        dataset_key = f"tensorzero_cortex_{run_id}"

        self.tensorzero.status(timeout_seconds=self.settings.tensorzero_ready_timeout_seconds)
        self.cortex.ensure_token()

        parse_artifacts = self._parse_and_store(
            run_dir=run_dir,
            urls=source_urls,
            engines=parse_engines,
            mode=parse_mode,
        )
        object_ids = [artifact.object_id for artifact in parse_artifacts if artifact.object_id]

        knowledge_events: dict[str, Any] = {
            "enabled": request.run_knowledge_jobs,
            "status": "skipped",
        }
        if request.run_knowledge_jobs and object_ids:
            try:
                knowledge_events = self._build_knowledge(
                    dataset_key=dataset_key,
                    object_ids=object_ids,
                )
                knowledge_events["enabled"] = True
                knowledge_events["status"] = "built"
            except (CortexApiError, RuntimeError) as exc:
                knowledge_events = {
                    "enabled": True,
                    "status": "failed",
                    "error": str(exc),
                    "fallback": "parse_artifacts",
                }
        elif request.run_knowledge_jobs:
            knowledge_events["reason"] = "no_storage_objects"

        search_result = self._search_or_fallback(
            dataset_key=dataset_key,
            query=query,
            parse_artifacts=parse_artifacts,
            knowledge_events=knowledge_events,
        )
        context = _search_context(search_result)
        context_source = str(search_result.get("source") or "knowledge")
        expected_keywords = _expected_keywords(source_urls)

        if context_source != "knowledge":
            knowledge_events.setdefault("fallback", context_source)
            knowledge_events.setdefault(
                "fallback_reason",
                search_result.get("reason") or search_result.get("error"),
            )

        tensorzero_result = self.tensorzero.inference(
            question=query,
            context=context,
            metadata={
                "run_id": run_id,
                "dataset_key": dataset_key,
                "parse_engines": parse_engines,
                "parse_mode": parse_mode,
                "object_ids": object_ids,
                "context_source": context_source,
            },
        )
        answer = tensorzero_result["output"]

        parse_score = _average(
            [artifact.parse_score for artifact in parse_artifacts if not artifact.error]
        )
        context_score = score_context(context, expected_keywords)
        answer_score = score_answer(answer, expected_keywords)
        e2e_pass = parse_score >= 0.45 and context_score >= 0.35 and answer_score >= 0.45

        inference_id = tensorzero_result.get("inference_id")
        self.tensorzero.feedback(
            metric_name="parse_markdown_quality",
            value=parse_score,
            inference_id=inference_id,
        )
        self.tensorzero.feedback(
            metric_name="rag_context_quality",
            value=context_score,
            inference_id=inference_id,
        )
        self.tensorzero.feedback(
            metric_name="llm_answer_quality",
            value=answer_score,
            inference_id=inference_id,
        )
        self.tensorzero.feedback(
            metric_name="rag_end_to_end_pass",
            value=e2e_pass,
            inference_id=inference_id,
        )

        eval_case = EvaluationCase(
            query=query,
            actual_output=json.dumps(answer, ensure_ascii=False)
            if not isinstance(answer, str)
            else answer,
            expected_keywords=expected_keywords,
            retrieval_contexts=[context],
            metadata={
                "run_id": run_id,
                "dataset_key": dataset_key,
                "tensorzero_inference_id": inference_id,
                "tensorzero_episode_id": tensorzero_result.get("episode_id"),
                "tensorzero_variant": tensorzero_result.get("variant_name"),
                "cortex_eval_mode": cortex_eval_mode,
                "knowledge_events": knowledge_events,
            },
        )

        eval_dataset_path = run_dir / "tensorzero_eval_dataset.jsonl"
        eval_dataset_path.write_text(
            json.dumps(eval_case.model_dump(), ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        cortex_eval_result = None
        if submit_cortex_eval:
            cortex_eval_result = self._submit_cortex_eval(
                run_id=run_id,
                eval_case=eval_case,
                mode=cortex_eval_mode,
            )
            write_json(run_dir / "cortex_eval_result.json", cortex_eval_result)

        scorecard = {
            "parse_markdown_quality": parse_score,
            "rag_context_quality": context_score,
            "llm_answer_quality": answer_score,
            "rag_end_to_end_pass": e2e_pass,
            "tensorzero_inference_id": inference_id,
            "tensorzero_episode_id": tensorzero_result.get("episode_id"),
            "tensorzero_variant": tensorzero_result.get("variant_name"),
            "parse_success_count": len([item for item in parse_artifacts if not item.error]),
            "parse_failure_count": len([item for item in parse_artifacts if item.error]),
            "context_source": context_source,
            "knowledge_status": knowledge_events.get("status"),
            "cortex_eval_mode": cortex_eval_mode if submit_cortex_eval else "disabled",
        }

        report_json_path = run_dir / "report.json"
        report_markdown_path = run_dir / "report.md"
        report = ExperimentReport(
            run_id=run_id,
            dataset_key=dataset_key,
            tensorzero_gateway_url=self.settings.tensorzero_gateway_url,
            tensorzero_ui_url=self.settings.tensorzero_ui_url,
            parse_artifacts=parse_artifacts,
            evaluation_cases=[eval_case],
            scorecard=scorecard,
            report_json_path=str(report_json_path),
            report_markdown_path=str(report_markdown_path),
            eval_dataset_jsonl_path=str(eval_dataset_path),
            cortex_eval_result=cortex_eval_result,
        )
        write_json(report_json_path, report.model_dump())
        report_markdown_path.write_text(_render_markdown_report(report), encoding="utf-8")
        write_json(run_dir / "raw_search_result.json", search_result)
        write_json(run_dir / "raw_tensorzero_result.json", tensorzero_result)
        return report

    def _parse_and_store(
        self,
        *,
        run_dir: Path,
        urls: list[dict[str, object]],
        engines: list[str],
        mode: str,
    ) -> list[ParseArtifact]:
        artifacts: list[ParseArtifact] = []
        for source in urls:
            url = str(source["url"])
            expected_keywords = [str(item) for item in source.get("expected_keywords", [])]
            for engine_id in engines:
                artifact = ParseArtifact(
                    url=url,
                    url_name=str(source["name"]),
                    engine_id=engine_id,
                    parse_mode=mode,
                    metadata={"format_hint": source.get("format_hint")},
                )
                try:
                    if mode == "async":
                        parsed = self.cortex.parse_async(sources=[url], engine_id=engine_id)
                    else:
                        parsed = self.cortex.parse_sync(sources=[url], engine_id=engine_id)
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
                            "parse_mode": mode,
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

    def _build_knowledge(self, *, dataset_key: str, object_ids: list[str]) -> dict[str, Any]:
        dataset = self.cortex.create_dataset(
            dataset_key=dataset_key,
            display_name=f"TensorZero Cortex {dataset_key}",
            description=(
                "Parsed financial and macroeconomic Markdown for TensorZero "
                "adaptive A/B testing."
            ),
        )
        add_job = self.cortex.add_objects_to_knowledge(
            dataset_key=dataset_key,
            object_ids=object_ids,
        )
        self.cortex.wait_job(add_job["job_id"], timeout_seconds=900)
        cognify_job = self.cortex.cognify(dataset_key=dataset_key)
        self.cortex.wait_job(cognify_job["job_id"], timeout_seconds=1200)
        return {"dataset": dataset, "add_job": add_job, "cognify_job": cognify_job}

    def _search_or_fallback(
        self,
        *,
        dataset_key: str,
        query: str,
        parse_artifacts: list[ParseArtifact],
        knowledge_events: dict[str, Any],
    ) -> dict[str, Any]:
        if knowledge_events.get("status") == "built":
            try:
                search_result = self.cortex.search_knowledge(
                    dataset_key=dataset_key,
                    query=query,
                    search_type=self.settings.knowledge_search_type,
                    top_k=8,
                )
                search_result.setdefault("source", "knowledge")
                return search_result
            except CortexApiError as exc:
                return _fallback_search_result(
                    parse_artifacts=parse_artifacts,
                    reason="knowledge_search_failed",
                    error=str(exc),
                )

        return _fallback_search_result(
            parse_artifacts=parse_artifacts,
            reason=str(knowledge_events.get("status") or "knowledge_disabled"),
            error=knowledge_events.get("error"),
        )

    def _submit_cortex_eval(
        self,
        *,
        run_id: str,
        eval_case: EvaluationCase,
        mode: str,
    ) -> dict[str, Any]:
        kwargs = {
            "name": f"TensorZero Cortex RAG Eval {run_id}",
            "test_cases": [
                {
                    "user_input": eval_case.query,
                    "actual_output": eval_case.actual_output,
                    "expected_output": ", ".join(eval_case.expected_keywords),
                    "retrieval_contexts": eval_case.retrieval_contexts,
                    "metadata": eval_case.metadata,
                }
            ],
        }
        if mode == "async":
            return self.cortex.run_eval_async(**kwargs)
        return self.cortex.run_eval_sync(**kwargs)


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


def _context_excerpt(markdown: str, *, max_chars: int = 6000) -> str | None:
    cleaned = markdown.strip()
    if not cleaned:
        return None
    return cleaned[:max_chars]


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


def _expected_keywords(urls: list[dict[str, object]]) -> list[str]:
    keywords: list[str] = []
    for source in urls:
        keywords.extend(str(item) for item in source.get("expected_keywords", []))
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


def _safe_filename(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")
    return (name or "artifact")[:120]


def _render_markdown_report(report: ExperimentReport) -> str:
    rows = "\n".join(
        f"| {item.url_name} | `{item.engine_id}` | {item.markdown_chars} | "
        f"{item.parse_score:.3f} | {item.object_id or ''} | {item.error or ''} |"
        for item in report.parse_artifacts
    )
    cases = "\n".join(
        f"- Query: {case.query}\n  - Expected keywords: {', '.join(case.expected_keywords[:12])}"
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

| URL | Engine | Markdown chars | Parse score | Object ID | Error |
| --- | --- | ---: | ---: | --- | --- |
{rows}

## Evaluation Cases

{cases}

## Artifacts

- Eval dataset JSONL: `{report.eval_dataset_jsonl_path}`
- JSON report: `{report.report_json_path}`
"""
