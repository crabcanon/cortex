from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MetricConfig(BaseModel):
    metric_key: str = Field(
        ...,
        description=(
            "Cortex Evaluation metric key, aligned to the normalized DeepEval/EvalScope "
            "catalog, for example rag.faithfulness or quality.correctness."
        ),
    )
    threshold: float | None = Field(default=0.65, ge=0, le=1)
    weight: float | None = Field(default=1.0, ge=0)
    params: dict[str, Any] = Field(default_factory=dict)


class ParseOptions(BaseModel):
    max_urls: int | None = Field(default=None, ge=1, le=20)
    engines: list[str] | None = Field(
        default=None,
        description="Parse engines to compare against the same URL set.",
    )
    mode: str | None = Field(
        default=None,
        description="Default parse execution mode: sync or async.",
    )
    engine_modes: dict[str, str] = Field(
        default_factory=lambda: {"docling": "async"},
        description=(
            "Per-engine execution override. Worker-only engines such as docling should "
            "use async so jobs are picked up by dedicated runtime workers."
        ),
    )
    scene: str | None = Field(
        default=None,
        description=(
            "Optional Cortex Parse scene/profile selector. Leave empty for engine defaults."
        ),
    )
    timeout_seconds: int = Field(default=900, ge=30, le=3600)


class KnowledgeOptions(BaseModel):
    enabled: bool | None = Field(
        default=None,
        description="Run Cortex Knowledge Add + Cognify + Search. Defaults to run_knowledge_jobs.",
    )
    search_type: str | None = Field(default=None)
    top_k: int = Field(default=8, ge=1, le=50)
    fallback_to_parse_artifacts: bool = True
    build_timeout_seconds: int = Field(default=1200, ge=60, le=7200)
    visualize_graph: bool | None = Field(
        default=None,
        description=(
            "Render Cognee knowledge graph HTML into the run artifact directory after "
            "Knowledge Add/Cognify succeeds."
        ),
    )


class TensorZeroOptions(BaseModel):
    strategy: str = Field(
        default="exhaustive",
        description=(
            "exhaustive pins every configured variant; adaptive lets TensorZero sample one "
            "variant; selected pins only the first configured variant."
        ),
    )
    variants: list[str] = Field(default_factory=lambda: ["openai", "gemini", "kimi"])
    context_grouping: str = Field(
        default="by_parse_engine",
        description="combined, by_parse_engine, or knowledge_or_parse.",
    )
    max_context_chars_per_group: int = Field(default=12000, ge=1000, le=48000)
    feedback_enabled: bool = True
    include_raw_response: bool = False


class EvaluationOptions(BaseModel):
    enabled: bool | None = Field(
        default=None,
        description="Submit generated cases to Cortex Evaluation. Defaults to SUBMIT_CORTEX_EVAL.",
    )
    mode: str | None = Field(default=None, description="sync or async.")
    engine_id: str = "deepeval"
    eval_types: list[str] = Field(default_factory=lambda: ["rag", "custom"])
    metric_profile: str = Field(
        default="deepeval_rag_core",
        description=(
            "deepeval_rag_core, deepeval_quality_core, deepeval_agentic_core, "
            "or custom when metrics_by_type is provided."
        ),
    )
    metrics_by_type: dict[str, list[MetricConfig]] | None = Field(default=None)
    persist_report_object: bool = True


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
    parse: ParseOptions | None = None
    knowledge: KnowledgeOptions | None = None
    tensorzero: TensorZeroOptions | None = None
    evaluation: EvaluationOptions | None = None


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


class ContextGroup(BaseModel):
    context_id: str
    source: str
    parse_engine_id: str | None = None
    object_ids: list[str] = Field(default_factory=list)
    document_ids: list[str] = Field(default_factory=list)
    context_chars: int = 0
    context_score: float = 0
    text_preview: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TensorZeroInferenceRecord(BaseModel):
    context_id: str
    context_source: str
    parse_engine_id: str | None = None
    variant_name: str | None = None
    inference_id: str | None = None
    episode_id: str | None = None
    answer_text: str = ""
    output: Any = None
    usage: dict[str, Any] = Field(default_factory=dict)
    finish_reason: str | None = None
    scores: dict[str, float | bool] = Field(default_factory=dict)
    feedback_errors: list[str] = Field(default_factory=list)
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
    context_groups: list[ContextGroup] = Field(default_factory=list)
    tensorzero_inferences: list[TensorZeroInferenceRecord] = Field(default_factory=list)
    evaluation_cases: list[EvaluationCase]
    scorecard: dict[str, Any]
    report_json_path: str
    report_markdown_path: str
    eval_dataset_jsonl_path: str
    knowledge_graph_html_path: str | None = None
    cortex_eval_result: dict[str, Any] | None = None
