"""Evaluation API contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .enums import EvalType, JobType
from .jobs import JobAccepted, TelemetryContext
from .parse import WebhookConfig


class EngineMetricBinding(BaseModel):
    engine_id: str
    native_key: str | None = None
    notes: str | None = None


class EvalEngineDescriptor(BaseModel):
    engine_id: str
    display_name: str
    availability_status: str = Field(pattern="^(available|degraded|disabled)$")
    provider: str | None = None
    execution_modes: list[str] = Field(default_factory=list)
    supported_eval_types: list[EvalType] = Field(default_factory=list)
    supported_metric_prefixes: list[str] = Field(default_factory=list)
    default_profiles: list[str] = Field(default_factory=list)
    notes: str | None = None


class EvalEngineList(BaseModel):
    generated_at: datetime | None = None
    engines: list[EvalEngineDescriptor]


class EvalMetricDefinition(BaseModel):
    metric_key: str
    display_name: str
    eval_types: list[EvalType] = Field(default_factory=list)
    engine_bindings: list[EngineMetricBinding] = Field(default_factory=list)
    description: str | None = None
    category: str | None = None
    unit: str | None = None
    score_direction: str = "higher_is_better"
    threshold_hint: float | None = None
    required_fields: list[str] = Field(default_factory=list)


class EvalMetricCatalog(BaseModel):
    generated_at: datetime | None = None
    metrics: list[EvalMetricDefinition]


class EvalFieldMapping(BaseModel):
    user_input: str | None = None
    actual_output: str | None = None
    expected_output: str | None = None
    retrieval_contexts: str | None = None
    conversation_turns: str | None = None


class EvalConversationTurn(BaseModel):
    role: str
    content: str


class EvalTestCase(BaseModel):
    user_input: str | None = None
    actual_output: str | None = None
    expected_output: str | None = None
    retrieval_contexts: list[str] = Field(default_factory=list)
    conversation_turns: list[EvalConversationTurn] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvalInput(BaseModel):
    type: str
    dataset_id: str | None = None
    dataset_version: str | None = None
    builtin_dataset_key: str | None = None
    object_id: str | None = None
    object_ids: list[str] = Field(default_factory=list)
    field_mapping: EvalFieldMapping | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    test_cases: list[EvalTestCase] = Field(default_factory=list)
    trace_session_id: str | None = None


class EvalTarget(BaseModel):
    type: str
    protocol: str | None = None
    endpoint_url: str | None = None
    auth_ref: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int | None = Field(default=None, ge=1)
    model_ref: str | None = None
    provider: str | None = None
    request_template: dict[str, Any] = Field(default_factory=dict)


class EvalMetricRequest(BaseModel):
    metric_key: str
    threshold: float | None = None
    weight: float | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class EvalOutputOptions(BaseModel):
    persist_report_object: bool = True
    persist_dataset_key: str | None = None
    include_sample_results: bool = True
    max_failures_reported: int | None = Field(default=None, ge=1)


class EvalSyncRequest(BaseModel):
    eval_type: EvalType
    input: EvalInput
    name: str | None = None
    engine_id: str = "auto"
    profile_key: str | None = None
    target: EvalTarget | None = None
    metrics: list[EvalMetricRequest] = Field(default_factory=list)
    engine_options: dict[str, Any] = Field(default_factory=dict)
    output: EvalOutputOptions = Field(default_factory=EvalOutputOptions)
    webhook: WebhookConfig | None = None


class EvalJobSubmitRequest(EvalSyncRequest):
    pass


class EvalScoreCard(BaseModel):
    overall_passed: bool
    composite_score: float | None = None
    metric_count: int = Field(default=0, ge=0)
    passed_metric_count: int = Field(default=0, ge=0)
    failed_metric_count: int = Field(default=0, ge=0)
    summary_by_namespace: dict[str, float] = Field(default_factory=dict)


class EvalMetricResult(BaseModel):
    metric_key: str
    status: str = Field(pattern="^(passed|failed|warn|info)$")
    display_name: str | None = None
    score: float | None = None
    threshold: float | None = None
    unit: str | None = None
    engine_id: str | None = None
    native_metric_key: str | None = None
    sample_size: int | None = Field(default=None, ge=0)
    details: dict[str, Any] = Field(default_factory=dict)


class EvalSampleCounters(BaseModel):
    total: int | None = Field(default=None, ge=0)
    passed: int | None = Field(default=None, ge=0)
    failed: int | None = Field(default=None, ge=0)
    skipped: int | None = Field(default=None, ge=0)


class StoredArtifactRef(BaseModel):
    object_id: str
    label: str
    content_type: str | None = None
    format: str | None = None
    description: str | None = None


class EvalJobAccepted(JobAccepted):
    job_type: JobType
    eval_type: EvalType | None = None
    engine_id: str | None = None


class EvalRunResult(BaseModel):
    eval_type: EvalType
    engine_id: str
    status: str = Field(pattern="^(succeeded|failed|partial)$")
    summary: EvalScoreCard
    metrics: list[EvalMetricResult]
    eval_run_id: str | None = None
    job_id: str | None = None
    name: str | None = None
    profile_key: str | None = None
    source_summary: dict[str, Any] = Field(default_factory=dict)
    target_summary: dict[str, Any] = Field(default_factory=dict)
    samples: EvalSampleCounters | None = None
    artifacts: list[StoredArtifactRef] = Field(default_factory=list)
    telemetry: TelemetryContext | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
