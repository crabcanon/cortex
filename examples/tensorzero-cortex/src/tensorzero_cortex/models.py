from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExperimentRequest(BaseModel):
    query: str | None = Field(default=None)
    max_urls: int | None = Field(default=None, ge=1, le=20)
    parse_engines: list[str] | None = None
    parse_mode: str | None = Field(
        default=None,
        description="Parse execution mode: sync for /v1/parse/sync or async for /v1/parse/jobs.",
    )
    submit_cortex_eval: bool | None = None
    cortex_eval_mode: str | None = Field(
        default=None,
        description=(
            "Evaluation execution mode: sync for /v1/eval/sync or async for /v1/eval/jobs."
        ),
    )
    run_knowledge_jobs: bool = True


class ParseArtifact(BaseModel):
    url: str
    url_name: str
    engine_id: str
    parse_mode: str = "sync"
    job_id: str | None = None
    document_id: str | None = None
    object_id: str | None = None
    markdown_chars: int = 0
    context_excerpt: str | None = None
    parse_score: float = 0
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationCase(BaseModel):
    query: str
    actual_output: str
    expected_keywords: list[str]
    retrieval_contexts: list[str]
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentReport(BaseModel):
    run_id: str
    dataset_key: str
    tensorzero_gateway_url: str
    tensorzero_ui_url: str
    parse_artifacts: list[ParseArtifact]
    evaluation_cases: list[EvaluationCase]
    scorecard: dict[str, Any]
    report_json_path: str
    report_markdown_path: str
    eval_dataset_jsonl_path: str
    cortex_eval_result: dict[str, Any] | None = None
