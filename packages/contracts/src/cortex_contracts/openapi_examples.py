"""Reusable OpenAPI request and parameter examples."""

from __future__ import annotations

from typing import cast

from fastapi.openapi.models import Example

TOKEN_ISSUE_REQUEST_EXAMPLES: dict[str, Example] = cast(
    dict[str, Example],
    {
        "tenant_admin_bootstrap": {
            "summary": "Recommended admin bootstrap token",
            "description": "A minimal but practical bootstrap request for a tenant administrator.",
            "value": {
                "grant_type": "urn:cortex:params:oauth:grant-type:bootstrap",
                "subject": "alice",
                "tenant_id": "tenant_demo",
                "actor_id": "alice",
                "actor_ref": "alice@example.com",
                "actor_type": "user",
                "display_name": "Alice",
                "client_id": "swagger-ui",
                "scopes": [
                    "health:read",
                    "parse:read",
                    "parse:write",
                    "storage:write",
                    "storage:read",
                    "storage:download",
                    "knowledge:read",
                    "knowledge:write",
                    "jobs:read",
                    "jobs:cancel",
                ],
                "roles": ["tenant_admin"],
                "groups": ["platform-ops"],
                "expires_in": 3600,
                "additional_claims": {
                    "region": "cn-shanghai",
                    "environment": "local",
                },
            },
        },
        "service_principal": {
            "summary": "Service principal token",
            "description": "A non-human token for parse and storage automation.",
            "value": {
                "grant_type": "urn:cortex:params:oauth:grant-type:bootstrap",
                "subject": "svc_ingest_pipeline",
                "tenant_id": "tenant_demo",
                "actor_id": "svc_ingest_pipeline",
                "actor_type": "service",
                "client_id": "cortex-worker",
                "scopes": [
                    "parse:read",
                    "parse:write",
                    "storage:write",
                    "storage:read",
                    "jobs:read",
                ],
                "roles": ["tenant_operator"],
                "groups": ["automation"],
                "expires_in": 1800,
                "additional_claims": {
                    "run_purpose": "nightly_ingest",
                },
            },
        },
    },
)

PARSE_SYNC_REQUEST_EXAMPLES: dict[str, Example] = cast(
    dict[str, Example],
    {
        "auto_batch_parse": {
            "summary": "Auto-routed batch parse",
            "description": (
                "Submit one or more source locators and let Cortex pick the best active engine "
                "and scene automatically."
            ),
            "value": {
                "sources": [
                    "https://docs.cognee.ai/core-concepts/overview",
                    "s3://demo-bucket/manuals/architecture.pdf",
                ],
                "engine_id": "auto",
            },
        },
    },
)

PARSE_JOB_REQUEST_EXAMPLES: dict[str, Example] = cast(
    dict[str, Example],
    {
        "async_auto_batch_parse": {
            "summary": "Async auto-routed batch parse",
            "description": (
                "Recommended when you want one async parse job per source with the same "
                "high-level routing contract."
            ),
            "value": {
                "sources": [
                    "https://docs.cognee.ai/core-concepts/overview",
                    "s3://demo-bucket/manuals/architecture.pdf",
                ],
                "engine_id": "auto",
                "priority": 5,
                "webhook": {
                    "url": "https://example.com/hooks/cortex/parse",
                    "secret_ref": "vault:cortex/webhooks/parse",
                    "event_types": [
                        "job.succeeded",
                        "job.failed",
                    ],
                    "headers": {
                        "X-Consumer": "knowledge-pipeline",
                    },
                },
            },
        },
    },
)

STORAGE_UPLOAD_CREATE_REQUEST_EXAMPLES: dict[str, Example] = cast(
    dict[str, Example],
    {
        "recommended_single_part": {
            "summary": "Recommended single-part upload",
            "description": (
                "Best for small and medium files that "
                "comfortably fit in one signed PUT request."
            ),
            "value": {
                "filename": "product-overview.md",
                "content_type": "text/markdown",
                "size_bytes": 20480,
                "checksum_sha256": "a" * 64,
                "metadata": {
                    "source": "swagger-demo",
                    "document_type": "guide",
                },
                "access_policy": {
                    "access_level": "tenant_shared",
                    "classification_labels": ["internal"],
                    "allowed_role_keys": ["tenant_admin", "analyst"],
                    "denied_role_keys": [],
                    "purpose_tags": ["knowledge_ingest"],
                    "constraints": {},
                },
                "tags": ["docs", "product"],
                "upload_mode": "single_part",
                "part_size_bytes": 8388608,
                "bucket_ref": "default",
                "object_prefix": "uploads/docs/",
            },
        },
        "multipart_large_file": {
            "summary": "Multipart upload for large files",
            "description": (
                "Recommended when the file is large enough "
                "that you want chunked upload and retry at "
                "the part level."
            ),
            "value": {
                "filename": "quarterly-report.pdf",
                "content_type": "application/pdf",
                "size_bytes": 67108864,
                "metadata": {
                    "source": "finance-portal",
                    "department": "fpna",
                },
                "tags": ["finance", "quarterly"],
                "upload_mode": "multipart",
                "part_size_bytes": 16777216,
                "object_prefix": "uploads/reports/",
            },
        },
    },
)

STORAGE_UPLOAD_COMPLETE_REQUEST_EXAMPLES: dict[str, Example] = cast(
    dict[str, Example],
    {
        "single_part_complete": {
            "summary": "Complete a single-part upload",
            "description": (
                "Use this when the upload session returned "
                "`single_part` instead of `multipart_parts`."
            ),
            "value": {
                "parts": [],
                "checksum_sha256": "a" * 64,
            },
        },
        "multipart_complete": {
            "summary": "Complete a multipart upload",
            "description": (
                "Send the uploaded part numbers and provider "
                "ETags exactly as returned by the object store."
            ),
            "value": {
                "parts": [
                    {"part_number": 1, "etag": '"part-1-etag"'},
                    {"part_number": 2, "etag": '"part-2-etag"'},
                    {"part_number": 3, "etag": '"part-3-etag"'},
                    {"part_number": 4, "etag": '"part-4-etag"'},
                ],
                "checksum_sha256": "b" * 64,
            },
        },
    },
)

KNOWLEDGE_DATASET_CREATE_REQUEST_EXAMPLES: dict[str, Example] = cast(
    dict[str, Example],
    {
        "recommended_dataset": {
            "summary": "Recommended shared dataset",
            "description": (
                "Creates a tenant-shared dataset suitable for "
                "Parse -> Add -> Search workflows."
            ),
            "value": {
                "dataset_key": "product_docs",
                "display_name": "Product Docs",
                "description": "Primary product knowledge base for demos and regression tests.",
                "tags": ["docs", "product"],
                "retention_class": "standard",
                "metadata": {
                    "domain": "product",
                    "owner_team": "platform",
                },
                "access_policy": {
                    "access_level": "tenant_shared",
                    "classification_labels": ["internal"],
                    "allowed_role_keys": ["tenant_admin", "analyst"],
                    "denied_role_keys": [],
                    "purpose_tags": ["search", "assistant"],
                    "constraints": {},
                },
            },
        },
    },
)

ADD_JOB_REQUEST_EXAMPLES: dict[str, Example] = cast(
    dict[str, Example],
    {
        "document_ingest": {
            "summary": "Ingest parsed documents and uploaded objects",
            "description": (
                "Recommended Add request after a file has "
                "been uploaded and optionally parsed."
            ),
            "value": {
                "dataset_key": "product_docs",
                "inputs": [
                    {
                        "input_type": "object_id",
                        "object_id": "obj_3f6c1d5e9b1646b5a4eabdbf8b417bd3",
                        "label": "Uploaded source file",
                        "node_set": ["docs"],
                        "metadata": {"source": "storage"},
                    },
                    {
                        "input_type": "document_id",
                        "document_id": "doc_71fe50adf1cb4981bb322f0d74f32598",
                        "label": "Normalized parsed document",
                        "node_set": ["docs", "parsed"],
                        "metadata": {"source": "parse"},
                    },
                ],
                "options": {
                    "normalize_text": True,
                    "structured_ingest": True,
                    "incremental": True,
                    "persist_source_copy": True,
                },
                "webhook": {
                    "url": "https://example.com/hooks/cortex/knowledge-add",
                    "event_types": ["job.succeeded", "job.failed"],
                    "headers": {"X-Consumer": "knowledge-worker"},
                },
            },
        },
        "direct_text_ingest": {
            "summary": "Direct text ingest",
            "description": (
                "Useful for small snippets, notes, or quick "
                "operator tests without a prior upload."
            ),
            "value": {
                "dataset_key": "product_docs",
                "inputs": [
                    {
                        "input_type": "text",
                        "text": (
                            "# Cortex Notes\n\n"
                            "Cortex supports Parse, Storage, "
                            "and Knowledge APIs."
                        ),
                        "label": "Quick note",
                        "node_set": ["notes"],
                        "metadata": {"source": "manual"},
                    }
                ],
                "options": {
                    "normalize_text": True,
                    "structured_ingest": True,
                    "incremental": True,
                    "persist_source_copy": False,
                },
            },
        },
    },
)

COGNIFY_JOB_REQUEST_EXAMPLES: dict[str, Example] = cast(
    dict[str, Example],
    {
        "recommended_cognify": {
            "summary": "Recommended Cognify request",
            "description": (
                "Builds or refreshes the dataset graph with "
                "the default prompt profile and semantic "
                "chunking."
            ),
            "value": {
                "dataset_key": "product_docs",
                "incremental_loading": True,
                "graph_prompt_profile": "default",
                "chunking": {
                    "enabled": True,
                    "strategy": "semantic",
                    "target_tokens": 512,
                    "overlap_tokens": 64,
                    "max_chunks": 256,
                },
                "webhook": {
                    "url": "https://example.com/hooks/cortex/cognify",
                    "event_types": ["job.succeeded", "job.failed"],
                    "headers": {"X-Consumer": "graph-sync"},
                },
            },
        },
    },
)

MEMIFY_JOB_REQUEST_EXAMPLES: dict[str, Example] = cast(
    dict[str, Example],
    {
        "recommended_memify": {
            "summary": "Recommended Memify request",
            "description": (
                "Runs the default coding-rules enrichment "
                "pipeline over the selected dataset."
            ),
            "value": {
                "dataset_key": "product_docs",
                "pipeline": "coding_rules",
                "node_type": "document",
                "node_names": ["Cortex API Overview", "Runtime Configuration Guide"],
                "session_ids": [],
                "webhook": {
                    "url": "https://example.com/hooks/cortex/memify",
                    "event_types": ["job.succeeded", "job.failed"],
                    "headers": {"X-Consumer": "knowledge-memify"},
                },
            },
        },
    },
)

SEARCH_REQUEST_EXAMPLES: dict[str, Example] = cast(
    dict[str, Example],
    {
        "recommended_graph_completion": {
            "summary": "Recommended graph completion search",
            "description": (
                "A good default search request for answering "
                "a question with graph-aware context."
            ),
            "value": {
                "query_text": "What does the documentation say about Cortex parse workflows?",
                "dataset_keys": ["product_docs"],
                "search_type": "GRAPH_COMPLETION",
                "top_k": 10,
                "filters": {
                    "document_ids": [],
                    "object_ids": [],
                    "tags": ["docs"],
                    "node_sets": ["docs"],
                    "metadata": {"domain": "product"},
                },
                "only_context": False,
                "include_provenance": True,
                "include_graph_paths": True,
                "timeout_seconds": 30,
            },
        },
        "chunk_search": {
            "summary": "Chunk-level retrieval",
            "description": (
                "Useful when you only want ranked context "
                "snippets without a synthesized answer."
            ),
            "value": {
                "query_text": "OpenTelemetry integration",
                "dataset_keys": ["product_docs"],
                "search_type": "CHUNKS",
                "top_k": 5,
                "only_context": True,
                "include_provenance": True,
                "include_graph_paths": False,
                "timeout_seconds": 15,
            },
        },
    },
)

JOB_ID_EXAMPLE = "job_71fe50adf1cb4981bb322f0d74f32598"
UPLOAD_ID_EXAMPLE = "upl_9feeaad1935f4b478ff61d6347ee5562"
OBJECT_ID_EXAMPLE = "obj_3f6c1d5e9b1646b5a4eabdbf8b417bd3"
DATASET_ID_EXAMPLE = "dset_9558cfc9178444e4a4c60d5658db78f5"
IDEMPOTENCY_KEY_EXAMPLE = "parse-demo-001"
LIMIT_EXAMPLE = 100
TTL_SECONDS_EXAMPLE = 900
