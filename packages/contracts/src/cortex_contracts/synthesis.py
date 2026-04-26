"""Synthesis API contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .enums import JobType, SynthesisType
from .evaluation import StoredArtifactRef
from .jobs import JobAccepted, TelemetryContext
from .parse import WebhookConfig


class SynthesisEngineDescriptor(BaseModel):
    engine_id: str
    display_name: str
    availability_status: str = Field(pattern="^(available|degraded|disabled)$")
    provider: str | None = None
    supported_synthesis_types: list[SynthesisType] = Field(default_factory=list)
    supported_source_types: list[str] = Field(default_factory=list)
    output_formats: list[str] = Field(default_factory=list)
    default_profiles: list[str] = Field(default_factory=list)
    notes: str | None = None


class SynthesisEngineList(BaseModel):
    generated_at: datetime | None = None
    engines: list[SynthesisEngineDescriptor]


class SynthesisSource(BaseModel):
    type: str
    dataset_id: str | None = None
    object_id: str | None = None
    object_ids: list[str] = Field(default_factory=list)
    metadata_object_id: str | None = None
    inline_records: list[dict[str, Any]] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)
    field_mapping: dict[str, str] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)


class SynthesisQualityGate(BaseModel):
    metric_key: str
    threshold: float | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class SynthesisConfig(BaseModel):
    sample_count: int | None = Field(default=None, ge=1)
    anonymize_pii: bool = False
    include_expected_output: bool | None = None
    max_contexts_per_case: int | None = Field(default=None, ge=1)
    quality_gates: list[SynthesisQualityGate] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)


class SynthesisOutputOptions(BaseModel):
    output_format: str | None = None
    persist_object_filename: str | None = None
    persist_dataset_key: str | None = None
    include_preview: bool = True


class SynthesisSyncRequest(BaseModel):
    synthesis_type: SynthesisType
    source: SynthesisSource
    name: str | None = None
    engine_id: str = "auto"
    profile_key: str | None = None
    config: SynthesisConfig = Field(default_factory=SynthesisConfig)
    output: SynthesisOutputOptions = Field(default_factory=SynthesisOutputOptions)
    webhook: WebhookConfig | None = None


class SynthesisJobSubmitRequest(SynthesisSyncRequest):
    pass


class SynthesisSummary(BaseModel):
    requested_sample_count: int | None = Field(default=None, ge=0)
    output_sample_count: int | None = Field(default=None, ge=0)
    quality_score: float | None = None
    privacy_score: float | None = None
    notes: list[str] = Field(default_factory=list)


class SynthesisQualityResult(BaseModel):
    metric_key: str
    status: str = Field(pattern="^(passed|failed|warn|info)$")
    threshold: float | None = None
    score: float | None = None
    unit: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class SynthesisJobAccepted(JobAccepted):
    job_type: JobType
    synthesis_type: SynthesisType | None = None
    engine_id: str | None = None


class SynthesisRunResult(BaseModel):
    synthesis_type: SynthesisType
    engine_id: str
    status: str = Field(pattern="^(succeeded|failed|partial)$")
    synthesis_run_id: str | None = None
    job_id: str | None = None
    name: str | None = None
    profile_key: str | None = None
    source_summary: dict[str, Any] = Field(default_factory=dict)
    summary: SynthesisSummary = Field(default_factory=SynthesisSummary)
    quality_gates: list[SynthesisQualityResult] = Field(default_factory=list)
    outputs: list[StoredArtifactRef] = Field(default_factory=list)
    output_dataset_id: str | None = None
    telemetry: TelemetryContext | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
