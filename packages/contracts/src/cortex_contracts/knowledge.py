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
    dataset_key: str = Field(
        pattern=r"^[a-z0-9][a-z0-9_-]{1,126}$",
        description=(
            "Required stable dataset key. Use lowercase letters, digits, underscores, or hyphens."
        ),
        examples=["product_docs"],
    )
    display_name: str = Field(
        description="Required human-friendly dataset name.",
        examples=["Product Docs"],
    )
    description: str | None = Field(
        default=None,
        description="Optional dataset description. Best default: omit.",
        examples=["Primary product knowledge base for demos and regression tests."],
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Optional dataset tags. Best default: empty list.",
        examples=[["docs", "product"]],
    )
    retention_class: DatasetRetentionClass = Field(
        default=DatasetRetentionClass.STANDARD,
        description="Retention profile. Best default: `standard`.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional dataset metadata. Best default: empty object.",
        examples=[{"domain": "product", "owner_team": "platform"}],
    )
    access_policy: AccessPolicy | None = Field(
        default=None,
        description="Optional access policy attached to the dataset. Best default: omit.",
    )


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
    input_type: KnowledgeInputType = Field(
        description=(
            "Required input type. It determines which of "
            "`object_id`, `document_id`, `text`, or `uri` "
            "must be set."
        ),
        examples=["document_id"],
    )
    object_id: str | None = Field(
        default=None,
        description="Storage object ID when `input_type=object_id`. Best default: omit.",
        examples=["obj_3f6c1d5e9b1646b5a4eabdbf8b417bd3"],
    )
    document_id: str | None = Field(
        default=None,
        description="Parsed document ID when `input_type=document_id`. Best default: omit.",
        examples=["doc_71fe50adf1cb4981bb322f0d74f32598"],
    )
    text: str | None = Field(
        default=None,
        description="Inline text when `input_type=text`. Best default: omit.",
        examples=["# Cortex Notes\n\nCortex supports Parse, Storage, and Knowledge APIs."],
    )
    uri: str | None = Field(
        default=None,
        description="External URI when `input_type=uri`. Best default: omit.",
        examples=["https://example.com/knowledge-source.md"],
    )
    label: str | None = Field(
        default=None,
        description="Optional label for operators and observability. Best default: omit.",
        examples=["Normalized parsed document"],
    )
    node_set: list[str] = Field(
        default_factory=list,
        description="Optional node-set grouping tags. Best default: empty list.",
        examples=[["docs", "parsed"]],
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Optional input metadata copied into downstream processing. Best default: empty object."
        ),
        examples=[{"source": "parse"}],
    )

    @model_validator(mode="after")
    def validate_payload(self) -> "KnowledgeInput":
        field_name = self.input_type.value
        if getattr(self, field_name) in {None, ""}:
            raise ValueError(
                f"`{field_name}` is required for input_type `{self.input_type.value}`."
            )
        return self


class AddOptions(BaseModel):
    normalize_text: bool = Field(
        default=True,
        description="Normalize raw text before ingestion. Best default: `true`.",
    )
    structured_ingest: bool = Field(
        default=True,
        description="Enable structured ingestion and field extraction. Best default: `true`.",
    )
    incremental: bool = Field(
        default=True,
        description="Avoid reprocessing unchanged content when possible. Best default: `true`.",
    )
    persist_source_copy: bool = Field(
        default=True,
        description="Persist a copy of the source payload when supported. Best default: `true`.",
    )


class AddJobRequest(BaseModel):
    dataset_id: str | None = Field(
        default=None,
        description="Optional dataset ID. Provide either `dataset_id` or `dataset_key`.",
        examples=["dset_9558cfc9178444e4a4c60d5658db78f5"],
    )
    dataset_key: str | None = Field(
        default=None,
        description=(
            "Optional dataset key. Recommended for human-authored "
            "requests when stable keys are known."
        ),
        examples=["product_docs"],
    )
    inputs: list[KnowledgeInput] = Field(
        min_length=1,
        description="Required ingest inputs. At least one input is required.",
    )
    options: AddOptions = Field(
        default_factory=AddOptions,
        description="Optional ingest behavior flags. Best default: use the built-in defaults.",
    )
    webhook: WebhookConfig | None = Field(
        default=None,
        description="Optional webhook callback for job lifecycle events. Best default: omit.",
    )

    @model_validator(mode="after")
    def validate_dataset_ref(self) -> "AddJobRequest":
        if not self.dataset_id and not self.dataset_key:
            raise ValueError("Either `dataset_id` or `dataset_key` is required.")
        return self


class CognifyJobRequest(BaseModel):
    dataset_id: str | None = Field(
        default=None,
        description="Optional dataset ID. Provide either `dataset_id` or `dataset_key`.",
        examples=["dset_9558cfc9178444e4a4c60d5658db78f5"],
    )
    dataset_key: str | None = Field(
        default=None,
        description="Optional dataset key. Recommended when stable dataset keys are known.",
        examples=["product_docs"],
    )
    incremental_loading: bool = Field(
        default=True,
        description=(
            "Only process newly added or changed content when possible. Best default: `true`."
        ),
    )
    graph_prompt_profile: GraphPromptProfile = Field(
        default=GraphPromptProfile.DEFAULT,
        description="Prompt profile for graph extraction. Best default: `default`.",
    )
    chunking: ChunkingOptions = Field(
        default_factory=ChunkingOptions,
        description="Chunking controls used before graph creation.",
    )
    webhook: WebhookConfig | None = Field(
        default=None,
        description="Optional webhook callback. Best default: omit.",
    )

    @model_validator(mode="after")
    def validate_dataset_ref(self) -> "CognifyJobRequest":
        if not self.dataset_id and not self.dataset_key:
            raise ValueError("Either `dataset_id` or `dataset_key` is required.")
        return self


class MemifyJobRequest(BaseModel):
    dataset_id: str | None = Field(
        default=None,
        description="Optional dataset ID. Provide either `dataset_id` or `dataset_key`.",
        examples=["dset_9558cfc9178444e4a4c60d5658db78f5"],
    )
    dataset_key: str | None = Field(
        default=None,
        description="Optional dataset key. Recommended for copy-paste requests.",
        examples=["product_docs"],
    )
    pipeline: MemifyPipeline = Field(
        default=MemifyPipeline.CODING_RULES,
        description="Memify enrichment pipeline. Best default: `coding_rules`.",
    )
    node_type: str | None = Field(
        default=None,
        description="Optional node type filter. Best default: omit.",
        examples=["document"],
    )
    node_names: list[str] = Field(
        default_factory=list,
        description="Optional node-name filter. Best default: empty list.",
        examples=[["Cortex API Overview"]],
    )
    session_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Optional session filters for session-aware pipelines. Best default: empty list."
        ),
        examples=[["session_demo_001"]],
    )
    custom_extraction_profile: str | None = Field(
        default=None,
        description="Optional custom extraction profile for `pipeline=custom`. Best default: omit.",
        examples=["custom/memify/extract-v1"],
    )
    custom_enrichment_profile: str | None = Field(
        default=None,
        description="Optional custom enrichment profile for `pipeline=custom`. Best default: omit.",
        examples=["custom/memify/enrich-v1"],
    )
    webhook: WebhookConfig | None = Field(
        default=None,
        description="Optional webhook callback. Best default: omit.",
    )

    @model_validator(mode="after")
    def validate_dataset_ref(self) -> "MemifyJobRequest":
        if not self.dataset_id and not self.dataset_key:
            raise ValueError("Either `dataset_id` or `dataset_key` is required.")
        return self


class SearchFilters(BaseModel):
    document_ids: list[str] = Field(
        default_factory=list,
        description="Optional document allow-list. Best default: empty list.",
        examples=[["doc_71fe50adf1cb4981bb322f0d74f32598"]],
    )
    object_ids: list[str] = Field(
        default_factory=list,
        description="Optional object allow-list. Best default: empty list.",
        examples=[["obj_3f6c1d5e9b1646b5a4eabdbf8b417bd3"]],
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Optional tag filter. Best default: empty list.",
        examples=[["docs"]],
    )
    node_sets: list[str] = Field(
        default_factory=list,
        description="Optional node-set filter. Best default: empty list.",
        examples=[["docs"]],
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional exact-match metadata filters. Best default: empty object.",
        examples=[{"domain": "product"}],
    )


class SearchRequest(BaseModel):
    query_text: str = Field(
        description="Required natural-language query or search expression.",
        examples=["What does the documentation say about Cortex parse workflows?"],
    )
    dataset_ids: list[str] = Field(
        default_factory=list,
        description="Optional dataset ID scope. Best default: empty list.",
        examples=[["dset_9558cfc9178444e4a4c60d5658db78f5"]],
    )
    dataset_keys: list[str] = Field(
        default_factory=list,
        description=(
            "Optional dataset key scope. Recommended for "
            "human-authored requests. Best default: empty list."
        ),
        examples=[["product_docs"]],
    )
    search_type: SearchType = Field(
        default=SearchType.GRAPH_COMPLETION,
        description="Search strategy. Best default: `GRAPH_COMPLETION`.",
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of context hits to return. Best default: 10.",
        examples=[10],
    )
    session_id: str | None = Field(
        default=None,
        description="Optional session scope for session-aware search. Best default: omit.",
        examples=["session_demo_001"],
    )
    filters: SearchFilters = Field(
        default_factory=SearchFilters,
        description="Optional structured filters. Best default: empty filters.",
    )
    only_context: bool = Field(
        default=False,
        description="Return context hits without an answer synthesis. Best default: `false`.",
    )
    include_provenance: bool = Field(
        default=True,
        description="Include citation/provenance metadata in hits. Best default: `true`.",
    )
    include_graph_paths: bool = Field(
        default=False,
        description="Include graph path explanations when supported. Best default: `false`.",
    )
    timeout_seconds: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Search timeout in seconds. Best default: 30.",
        examples=[30],
    )


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
    context_items: list[SearchHit]
    latency_ms: int = Field(ge=0)
    created_at: datetime
    dataset_scope: list[str] = Field(default_factory=list)
    answer: str | None = None
    graph_paths: list[GraphPath] = Field(default_factory=list)
    telemetry: TelemetryContext | None = None
