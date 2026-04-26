"""Contract-level enums."""

from enum import StrEnum


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class AccessLevel(StrEnum):
    TENANT_PRIVATE = "tenant_private"
    TENANT_SHARED = "tenant_shared"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"


class UploadMode(StrEnum):
    SINGLE_PART = "single_part"
    MULTIPART = "multipart"


class UploadSessionStatus(StrEnum):
    PENDING_UPLOAD = "pending_upload"


class StorageObjectStatus(StrEnum):
    AVAILABLE = "available"
    ARCHIVED = "archived"
    DELETED = "deleted"


class DatasetRetentionClass(StrEnum):
    STANDARD = "standard"
    DURABLE = "durable"
    TEMPORARY = "temporary"


class KnowledgeDatasetStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETING = "deleting"


class KnowledgeInputType(StrEnum):
    OBJECT_ID = "object_id"
    DOCUMENT_ID = "document_id"
    TEXT = "text"
    URI = "uri"


class GraphPromptProfile(StrEnum):
    DEFAULT = "default"
    SIMPLE = "simple"
    STRICT = "strict"
    GUIDED = "guided"


class MemifyPipeline(StrEnum):
    CODING_RULES = "coding_rules"
    TRIPLET_EMBEDDINGS = "triplet_embeddings"
    SESSION_PERSISTENCE = "session_persistence"
    ENTITY_CONSOLIDATION = "entity_consolidation"
    CUSTOM = "custom"


class SearchType(StrEnum):
    GRAPH_COMPLETION = "GRAPH_COMPLETION"
    RAG_COMPLETION = "RAG_COMPLETION"
    CHUNKS = "CHUNKS"
    SUMMARIES = "SUMMARIES"
    GRAPH_SUMMARY_COMPLETION = "GRAPH_SUMMARY_COMPLETION"
    GRAPH_COMPLETION_COT = "GRAPH_COMPLETION_COT"
    GRAPH_COMPLETION_CONTEXT_EXTENSION = "GRAPH_COMPLETION_CONTEXT_EXTENSION"
    TRIPLET_COMPLETION = "TRIPLET_COMPLETION"
    CHUNKS_LEXICAL = "CHUNKS_LEXICAL"
    CODING_RULES = "CODING_RULES"
    TEMPORAL = "TEMPORAL"
    CYPHER = "CYPHER"
    NATURAL_LANGUAGE = "NATURAL_LANGUAGE"


class SearchHitType(StrEnum):
    CHUNK = "chunk"
    SUMMARY = "summary"
    GRAPH_NODE = "graph_node"
    GRAPH_EDGE = "graph_edge"
    TRIPLET = "triplet"
    RULE = "rule"
    CYPHER_ROW = "cypher_row"


class DownloadDisposition(StrEnum):
    ATTACHMENT = "attachment"
    INLINE = "inline"


class ParseInputKind(StrEnum):
    URL = "url"
    OBJECT = "object"
    URI = "uri"


class EvalType(StrEnum):
    PERF = "perf"
    RAG = "rag"
    AGENTIC = "agentic"
    MULTI_TURN = "multi_turn"
    CUSTOM = "custom"


class SynthesisType(StrEnum):
    STRUCTURED_SINGLE_TABLE = "structured_single_table"
    STRUCTURED_RELATIONAL = "structured_relational"
    RAG_GOLDENS = "rag_goldens"
    QA_PAIRS = "qa_pairs"
    CONVERSATION_GOLDENS = "conversation_goldens"
    AGENT_TRAJECTORIES = "agent_trajectories"
    CUSTOM = "custom"


class ParseEngineDeploymentMode(StrEnum):
    LOCAL = "local"
    REMOTE = "remote"
    HYBRID = "hybrid"


class ParseEngineStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"


class ParseAttemptStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class FallbackMode(StrEnum):
    NONE = "none"
    ORDERED = "ordered"
    CAPABILITY_BASED = "capability_based"
    QUALITY_BASED = "quality_based"


class FallbackOnError(StrEnum):
    TRY_NEXT = "try_next"
    FAIL_FAST = "fail_fast"


class ParseLlmReadyMode(StrEnum):
    MARKDOWN = "markdown"
    FIT_MARKDOWN = "fit_markdown"


class ChunkingStrategy(StrEnum):
    NONE = "none"
    HEADING = "heading"
    SEMANTIC = "semantic"
    FIXED_TOKENS = "fixed_tokens"


class ParseStoragePolicy(StrEnum):
    METADATA_ONLY = "metadata_only"
    MARKDOWN_ONLY = "markdown_only"
    FULL_ARTIFACTS = "full_artifacts"


class JobType(StrEnum):
    PARSE = "parse"
    KNOWLEDGE_ADD = "knowledge_add"
    KNOWLEDGE_COGNIFY = "knowledge_cognify"
    KNOWLEDGE_MEMIFY = "knowledge_memify"
    EVAL = "eval"
    SYNTHESIS = "synthesis"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
