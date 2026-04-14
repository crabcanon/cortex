"""Knowledge API contracts."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from .enums import (
    DatasetRetentionClass,
    GraphPromptProfile,
    KnowledgeDatasetStatus,
    KnowledgeInputType,
    MemifyPipeline,
    SearchHitType,
    SearchType,
)
from .jobs import TelemetryContext
from .parse import ChunkingOptions, WebhookConfig
from .resources import AccessPolicy, AuditFields


class DatasetCounters(BaseModel):
    objects: int = Field(default=0, ge=0)
    documents: int = Field(default=0, ge=0)
    chunks: int = Field(default=0, ge=0)
    graph_nodes: int = Field(default=0, ge=0)
    graph_edges: int = Field(default=0, ge=0)


class KnowledgeDatasetCreateRequest(BaseModel):
    dataset_key: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,126}$")
    display_name: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    retention_class: DatasetRetentionClass = DatasetRetentionClass.STANDARD
    metadata: dict[str, Any] = Field(default_factory=dict)
    access_policy: AccessPolicy | None = None


class KnowledgeDataset(BaseModel):
    dataset_id: str
    dataset_key: str
    display_name: str
    status: KnowledgeDatasetStatus
    audit: AuditFields
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    retention_class: DatasetRetentionClass = DatasetRetentionClass.STANDARD
    metadata: dict[str, Any] = Field(default_factory=dict)
    access_policy: AccessPolicy | None = None
    counters: DatasetCounters = Field(default_factory=DatasetCounters)


class KnowledgeInput(BaseModel):
    input_type: KnowledgeInputType
    object_id: str | None = None
    document_id: str | None = None
    text: str | None = None
    uri: str | None = None
    label: str | None = None
    node_set: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_payload(self) -> "KnowledgeInput":
        field_name = self.input_type.value
        if getattr(self, field_name) in {None, ""}:
            raise ValueError(
                f"`{field_name}` is required for input_type `{self.input_type.value}`."
            )
        return self


class AddOptions(BaseModel):
    normalize_text: bool = True
    structured_ingest: bool = True
    incremental: bool = True
    persist_source_copy: bool = True


class AddJobRequest(BaseModel):
    dataset_id: str | None = None
    dataset_key: str | None = None
    inputs: list[KnowledgeInput] = Field(default_factory=list, min_length=1)
    options: AddOptions = Field(default_factory=AddOptions)
    webhook: WebhookConfig | None = None

    @model_validator(mode="after")
    def validate_dataset_ref(self) -> "AddJobRequest":
        if not self.dataset_id and not self.dataset_key:
            raise ValueError("Either `dataset_id` or `dataset_key` is required.")
        return self


class CognifyJobRequest(BaseModel):
    dataset_id: str | None = None
    dataset_key: str | None = None
    incremental_loading: bool = True
    graph_prompt_profile: GraphPromptProfile = GraphPromptProfile.DEFAULT
    chunking: ChunkingOptions = Field(default_factory=ChunkingOptions)
    webhook: WebhookConfig | None = None

    @model_validator(mode="after")
    def validate_dataset_ref(self) -> "CognifyJobRequest":
        if not self.dataset_id and not self.dataset_key:
            raise ValueError("Either `dataset_id` or `dataset_key` is required.")
        return self


class MemifyJobRequest(BaseModel):
    dataset_id: str | None = None
    dataset_key: str | None = None
    pipeline: MemifyPipeline = MemifyPipeline.CODING_RULES
    node_type: str | None = None
    node_names: list[str] = Field(default_factory=list)
    session_ids: list[str] = Field(default_factory=list)
    custom_extraction_profile: str | None = None
    custom_enrichment_profile: str | None = None
    webhook: WebhookConfig | None = None

    @model_validator(mode="after")
    def validate_dataset_ref(self) -> "MemifyJobRequest":
        if not self.dataset_id and not self.dataset_key:
            raise ValueError("Either `dataset_id` or `dataset_key` is required.")
        return self


class SearchFilters(BaseModel):
    document_ids: list[str] = Field(default_factory=list)
    object_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    node_sets: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    query_text: str
    dataset_ids: list[str] = Field(default_factory=list)
    dataset_keys: list[str] = Field(default_factory=list)
    search_type: SearchType = SearchType.GRAPH_COMPLETION
    top_k: int = Field(default=10, ge=1, le=100)
    session_id: str | None = None
    filters: SearchFilters = Field(default_factory=SearchFilters)
    only_context: bool = False
    include_provenance: bool = True
    include_graph_paths: bool = False
    timeout_seconds: int = Field(default=30, ge=1, le=300)


class Citation(BaseModel):
    source_url: str | None = None
    document_id: str | None = None
    chunk_id: str | None = None
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)


class SearchHit(BaseModel):
    rank: int = Field(ge=1)
    hit_type: SearchHitType
    score: float
    source_id: str | None = None
    document_id: str | None = None
    object_id: str | None = None
    title: str | None = None
    snippet: str | None = None
    citation: Citation | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphPath(BaseModel):
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)


class SearchResponse(BaseModel):
    request_id: str
    search_type: SearchType
    context_items: list[SearchHit] = Field(default_factory=list)
    latency_ms: int = Field(default=0, ge=0)
    created_at: datetime
    dataset_scope: list[str] = Field(default_factory=list)
    answer: str | None = None
    graph_paths: list[GraphPath] = Field(default_factory=list)
    telemetry: TelemetryContext | None = None
