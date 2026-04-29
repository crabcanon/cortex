"""Reusable OpenAPI request and parameter examples."""

from __future__ import annotations

from typing import cast

from fastapi.openapi.models import Example

LOCAL_DEV_TOKEN_REQUEST_EXAMPLES: dict[str, Example] = cast(
    dict[str, Example],
    {
        "recommended_swagger_token": {
            "summary": "Recommended Swagger dev token / 推荐的 Swagger 开发令牌",
            "description": (
                "Creates a local development bearer token that can be pasted directly into "
                "Swagger UI's `Authorize` dialog. / 生成一个可直接粘贴到 Swagger UI "
                "`Authorize` 弹窗中的本地开发 Bearer token。"
            ),
            "value": {
                "subject": "alice",
                "tenant_id": "tenant_demo",
                "display_name": "Alice",
                "client_id": "swagger-ui",
                "roles": ["tenant_admin"],
                "groups": ["platform-ops"],
                "expires_in": 3600,
            },
        },
        "minimal_local_token": {
            "summary": "Minimal local token request / 最小化本地令牌请求",
            "description": (
                "Only `subject` and `tenant_id` are required. Cortex fills in the standard "
                "local developer scopes automatically. / 只需要 `subject` 和 "
                "`tenant_id`，其余标准本地开发 scope 由 Cortex 自动补齐。"
            ),
            "value": {
                "subject": "smoke-test",
                "tenant_id": "tenant_demo",
            },
        },
    },
)

PARSE_SYNC_REQUEST_EXAMPLES: dict[str, Example] = cast(
    dict[str, Example],
    {
        "auto_web_batch_parse": {
            "summary": "Auto-routed web batch parse / 自动路由网页批量解析",
            "description": (
                "Submit one or more source locators and let Cortex pick the best active engine "
                "and scene automatically."
            ),
            "value": {
                "sources": [
                    "https://docs.cognee.ai/core-concepts/overview",
                    "https://docs.crawl4ai.com/advanced/advanced-features/",
                ],
                "engine_id": "auto",
            },
        },
        "crawl4ai_deep_web": {
            "summary": "Crawl4AI deep-web parse / Crawl4AI 深度网页解析",
            "description": (
                "Use Crawl4AI explicitly with the high-intensity `deep_web` scene. This keeps "
                "fallback disabled and always routes the request to Crawl4AI."
            ),
            "value": {
                "sources": ["https://docs.crawl4ai.com/advanced/advanced-features/"],
                "engine_id": "crawl4ai",
                "scene": "deep_web",
            },
        },
        "minio_object_auto": {
            "summary": "MinIO/S3 object parse / MinIO/S3 对象解析",
            "description": (
                "Parse a Cortex-managed object stored in MinIO/S3. The locator may be the "
                "storage object key, an `s3://bucket/key` URI, or `cortex://objects/{object_id}`; "
                "Cortex extracts the `obj_...` id, signs a download URL, and detects MIME type."
            ),
            "value": {
                "sources": [
                    "s3://cortex-local/tenant_demo/obj_a3da967e3ca446cab3631bb7/bofa_note.pdf"
                ],
                "engine_id": "auto",
                "scene": "document_ai",
            },
        },
    },
)

PARSE_JOB_REQUEST_EXAMPLES: dict[str, Example] = cast(
    dict[str, Example],
    {
        "async_auto_batch_parse": {
            "summary": "Async auto-routed batch parse / 异步自动路由批量解析",
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
        "async_docling_minio_pdf": {
            "summary": "Docling async MinIO PDF parse / Docling 异步解析 MinIO PDF",
            "description": (
                "Use this for PDFs uploaded through Cortex Storage. Start the "
                "`cortex-parse-worker-docling` worker/profile so the job is claimed by the "
                "Docling runtime worker instead of the slim parse worker."
            ),
            "value": {
                "sources": [
                    "s3://cortex-local/tenant_demo/obj_a3da967e3ca446cab3631bb7/bofa_note.pdf"
                ],
                "engine_id": "docling",
                "scene": "document_ai",
                "priority": 5,
            },
        },
        "async_llamaparse_minio_pdf": {
            "summary": "LlamaParse async MinIO PDF parse / LlamaParse 异步解析 MinIO PDF",
            "description": (
                "Use this when the LlamaParse cloud API key is configured and the object should "
                "be parsed by the cloud document parser."
            ),
            "value": {
                "sources": [
                    "cortex-local/tenant_demo/obj_a3da967e3ca446cab3631bb7/bofa_note.pdf"
                ],
                "engine_id": "llama_parse",
                "scene": "document_fidelity",
                "priority": 5,
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
                "Best for small and medium files that fit in one signed PUT request. "
                "You can omit `size_bytes`; Cortex will finalize the actual object size when "
                "the upload is completed."
            ),
            "value": {
                "filename": "README.md",
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
            },
        },
        "multipart_large_file": {
            "summary": "Multipart upload for large files",
            "description": (
                "Recommended when the client already knows the file is large enough "
                "that Cortex should initialize multipart upload and return part URLs."
            ),
            "value": {
                "filename": "quarterly-report.pdf",
                "size_bytes": 67108864,
                "metadata": {
                    "source": "finance-portal",
                    "department": "fpna",
                },
                "tags": ["finance", "quarterly"],
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
        "swagger_demo_dataset": {
            "summary": "Swagger demo dataset / Swagger 演示数据集",
            "description": (
                "Creates a tenant-shared dataset used by the one-click Knowledge examples below. "
                "If this key already exists, change the suffix and reuse the same key in Add, "
                "Cognify, Memify, and Search requests."
            ),
            "value": {
                "dataset_key": "swagger_knowledge_demo",
                "display_name": "Swagger Knowledge Demo",
                "description": (
                    "Small Knowledge dataset for Swagger Try it out tests using inline text, "
                    "public URIs, and uploaded storage objects."
                ),
                "tags": ["swagger", "knowledge", "demo"],
                "retention_class": "temporary",
                "metadata": {
                    "domain": "cortex",
                    "owner_team": "platform",
                    "demo_flow": "storage-parse-knowledge",
                },
                "access_policy": {
                    "access_level": "tenant_shared",
                    "classification_labels": ["internal"],
                    "allowed_role_keys": ["tenant_admin", "analyst"],
                    "denied_role_keys": [],
                    "purpose_tags": ["search", "assistant", "swagger_demo"],
                    "constraints": {},
                },
            },
        },
        "product_docs_dataset": {
            "summary": "Product docs dataset / 产品文档数据集",
            "description": (
                "Creates a tenant-shared dataset suitable for Parse -> Add -> Search workflows."
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
        "swagger_inline_text_ingest": {
            "summary": "Runnable inline text Add / 可直接运行的内联文本 Add",
            "description": (
                "Use after creating `swagger_knowledge_demo`. This is the safest local Swagger "
                "smoke example because it does not require an existing Storage object or external "
                "network access."
            ),
            "value": {
                "dataset_key": "swagger_knowledge_demo",
                "inputs": [
                    {
                        "input_type": "text",
                        "text": (
                            "# Cortex API Demo Knowledge\n\n"
                            "Cortex provides Parse, Storage, Knowledge, Evaluation, and "
                            "Synthesis APIs. Parse normalizes URLs and files into Markdown. "
                            "Storage keeps source files in S3-compatible buckets. Knowledge "
                            "uses Add, Cognify, Memify, and Search to build graph-aware "
                            "retrieval workflows."
                        ),
                        "label": "Cortex API demo note",
                        "node_set": ["swagger_demo", "docs"],
                        "metadata": {
                            "source": "swagger-inline",
                            "domain": "cortex",
                            "document_type": "demo_note",
                        },
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
        "public_uri_ingest": {
            "summary": "Public URI Add / 公共 URI Add",
            "description": (
                "Use when the Knowledge runtime can fetch public URLs. This keeps the request "
                "copy-pasteable while exercising the URI input path."
            ),
            "value": {
                "dataset_key": "swagger_knowledge_demo",
                "inputs": [
                    {
                        "input_type": "uri",
                        "uri": "https://raw.githubusercontent.com/crabcanon/cortex/main/README.md",
                        "label": "Cortex README from GitHub",
                        "node_set": ["swagger_demo", "docs", "uri"],
                        "metadata": {
                            "source": "github-raw",
                            "domain": "cortex",
                            "document_type": "readme",
                        },
                    }
                ],
                "options": {
                    "normalize_text": True,
                    "structured_ingest": True,
                    "incremental": True,
                    "persist_source_copy": True,
                },
            },
        },
        "storage_object_ingest": {
            "summary": "Storage object Add / 存储对象 Add",
            "description": (
                "Use after uploading a file with `POST /v1/storage/files`; replace `object_id` "
                "with the returned object id. This documents the Storage -> Knowledge path."
            ),
            "value": {
                "dataset_key": "swagger_knowledge_demo",
                "inputs": [
                    {
                        "input_type": "object_id",
                        "object_id": "obj_a3da967e3ca446cab3631bb7",
                        "label": "Uploaded README or PDF",
                        "node_set": ["swagger_demo", "storage"],
                        "metadata": {
                            "source": "storage",
                            "bucket": "cortex-local",
                            "object_key": (
                                "tenant_demo/obj_a3da967e3ca446cab3631bb7/README.md"
                            ),
                        },
                    }
                ],
                "options": {
                    "normalize_text": True,
                    "structured_ingest": True,
                    "incremental": True,
                    "persist_source_copy": True,
                },
            },
        },
        "parsed_document_ingest": {
            "summary": "Parsed document Add / 解析文档 Add",
            "description": (
                "Recommended Add request after a file has been uploaded and optionally parsed."
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
            "summary": "Direct text ingest / 直接文本摄入",
            "description": (
                "Useful for small snippets, notes, or quick operator tests without a prior upload."
            ),
            "value": {
                "dataset_key": "product_docs",
                "inputs": [
                    {
                        "input_type": "text",
                        "text": (
                            "# Cortex Notes\n\nCortex supports Parse, Storage, and Knowledge APIs."
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
        "swagger_demo_cognify": {
            "summary": "Runnable Cognify for demo dataset / 演示数据集 Cognify",
            "description": (
                "Run after the `swagger_inline_text_ingest` Add job succeeds. It builds graph "
                "structure for the demo dataset with a small chunking budget."
            ),
            "value": {
                "dataset_key": "swagger_knowledge_demo",
                "incremental_loading": True,
                "graph_prompt_profile": "simple",
                "chunking": {
                    "enabled": True,
                    "strategy": "semantic",
                    "target_tokens": 384,
                    "overlap_tokens": 48,
                    "max_chunks": 64,
                },
            },
        },
        "recommended_cognify": {
            "summary": "Recommended Cognify request / 推荐 Cognify 请求",
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
        "swagger_triplet_memify": {
            "summary": "Runnable triplet Memify / 可运行的三元组 Memify",
            "description": (
                "Run after Cognify. The Python Cognee adapter currently supports "
                "`triplet_embeddings` and `session_persistence` for live execution."
            ),
            "value": {
                "dataset_key": "swagger_knowledge_demo",
                "pipeline": "triplet_embeddings",
                "node_type": "document",
                "node_names": [],
                "session_ids": [],
            },
        },
        "recommended_memify": {
            "summary": "Recommended Memify request / 推荐 Memify 请求",
            "description": (
                "Runs the default coding-rules enrichment pipeline over the selected dataset."
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
        "swagger_demo_search": {
            "summary": "Runnable demo search / 可运行的演示搜索",
            "description": (
                "Run after Add and preferably after Cognify. Uses the demo dataset key from the "
                "Swagger dataset example."
            ),
            "value": {
                "query_text": "What Cortex APIs are available and what does Knowledge do?",
                "dataset_keys": ["swagger_knowledge_demo"],
                "search_type": "GRAPH_COMPLETION",
                "top_k": 5,
                "filters": {
                    "document_ids": [],
                    "object_ids": [],
                    "tags": [],
                    "node_sets": ["swagger_demo"],
                    "metadata": {},
                },
                "only_context": False,
                "include_provenance": True,
                "include_graph_paths": True,
                "timeout_seconds": 30,
            },
        },
        "storage_object_search": {
            "summary": "Search storage-backed knowledge / 搜索存储来源知识",
            "description": (
                "Use after adding an uploaded Storage object. Replace the object id with the id "
                "returned by `/v1/storage/files` when you want to narrow results."
            ),
            "value": {
                "query_text": "Summarize the uploaded README or PDF.",
                "dataset_keys": ["swagger_knowledge_demo"],
                "search_type": "CHUNKS",
                "top_k": 5,
                "filters": {
                    "document_ids": [],
                    "object_ids": ["obj_a3da967e3ca446cab3631bb7"],
                    "tags": [],
                    "node_sets": ["storage"],
                    "metadata": {},
                },
                "only_context": True,
                "include_provenance": True,
                "include_graph_paths": False,
                "timeout_seconds": 15,
            },
        },
        "recommended_graph_completion": {
            "summary": "Recommended graph completion search / 推荐图谱补全搜索",
            "description": (
                "A good default search request for answering a question with graph-aware context."
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
            "summary": "Chunk-level retrieval / Chunk 级检索",
            "description": (
                "Useful when you only want ranked context snippets without a synthesized answer."
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

EVAL_SYNC_REQUEST_EXAMPLES: dict[str, Example] = cast(
    dict[str, Example],
    {
        "rag_eval": {
            "summary": "RAG evaluation / RAG 评测",
            "description": (
                "Recommended synchronous evaluation for a small RAG validation dataset."
            ),
            "value": {
                "name": "Fintech-RAG-QA-Eval",
                "eval_type": "rag",
                "engine_id": "auto",
                "input": {
                    "type": "dataset",
                    "dataset_id": "ds_001",
                    "field_mapping": {
                        "user_input": "question",
                        "actual_output": "answer",
                        "retrieval_contexts": "contexts",
                    },
                },
                "target": {
                    "type": "api",
                    "endpoint_url": "https://ordix.internal/v1/query",
                    "timeout_seconds": 30,
                },
                "metrics": [
                    {"metric_key": "rag.faithfulness", "threshold": 0.8},
                    {"metric_key": "rag.answer_relevance", "threshold": 0.7},
                ],
            },
        },
        "deepeval_multi_turn_sync": {
            "summary": "DeepEval multi-turn sync / DeepEval 多轮同步评测",
            "description": "Inline multi-turn conversation evaluation for quick regression checks.",
            "value": {
                "name": "swagger-dialog-smoke",
                "eval_type": "multi_turn",
                "engine_id": "deepeval",
                "input": {
                    "type": "inline_test_cases",
                    "test_cases": [
                        {
                            "conversation_turns": [
                                {"role": "user", "content": "Help me parse a PDF from storage."},
                                {
                                    "role": "assistant",
                                    "content": "Upload it to Storage and submit a Parse job.",
                                },
                            ],
                            "metadata": {"case_id": "dialog-smoke-001"},
                        }
                    ],
                },
                "metrics": [
                    {"metric_key": "dialog.conversation_relevancy", "threshold": 0.75},
                    {"metric_key": "dialog.conversation_completeness", "threshold": 0.75},
                ],
            },
        },
        "evalscope_perf_sync": {
            "summary": "EvalScope perf sync / EvalScope 性能同步评测",
            "description": (
                "Small performance smoke request routed to EvalScope. In local Docker, the "
                "target can point at the Cortex readiness endpoint."
            ),
            "value": {
                "name": "swagger-perf-smoke",
                "eval_type": "perf",
                "engine_id": "evalscope",
                "input": {"type": "builtin_dataset", "builtin_dataset_key": "openqa"},
                "target": {
                    "type": "api",
                    "endpoint_url": "http://127.0.0.1:8080/v1/health/ready",
                    "timeout_seconds": 30,
                },
                "metrics": [
                    {"metric_key": "perf.qps", "threshold": 1.0},
                    {"metric_key": "perf.p90_latency", "threshold": 2.0},
                ],
                "engine_options": {"parallel": [1], "number": [5], "stream": False},
            },
        },
    },
)

EVAL_JOB_REQUEST_EXAMPLES: dict[str, Example] = cast(
    dict[str, Example],
    {
        "agent_eval_job": {
            "summary": "Agent evaluation job / Agent 评测作业",
            "description": (
                "Recommended async submission for larger agentic or regression workloads."
            ),
            "value": {
                "name": "Support-Agent-Regressions",
                "eval_type": "agentic",
                "engine_id": "auto",
                "input": {
                    "type": "dataset",
                    "dataset_id": "ds_agent_suite",
                },
                "metrics": [
                    {"metric_key": "agent.task_completion", "threshold": 0.8},
                    {"metric_key": "agent.tool_correctness", "threshold": 0.8},
                ],
                "webhook": {
                    "url": "https://example.com/hooks/cortex/eval",
                    "event_types": ["job.succeeded", "job.failed"],
                },
            },
        },
        "evalscope_perf_job": {
            "summary": "EvalScope perf async job / EvalScope 异步性能评测",
            "description": "Recommended async submission for larger performance workloads.",
            "value": {
                "name": "swagger-perf-job",
                "eval_type": "perf",
                "engine_id": "evalscope",
                "input": {"type": "builtin_dataset", "builtin_dataset_key": "openqa"},
                "target": {
                    "type": "api",
                    "protocol": "openai_compatible",
                    "endpoint_url": "http://127.0.0.1:8080/v1/health/ready",
                    "timeout_seconds": 60,
                },
                "metrics": [
                    {"metric_key": "perf.qps", "threshold": 1.0},
                    {"metric_key": "perf.p99_latency", "threshold": 5.0},
                    {"metric_key": "perf.output_tokens_per_second", "threshold": 1.0},
                ],
                "engine_options": {"parallel": [1, 2], "number": [10], "stream": False},
            },
        },
        "deepeval_custom_job": {
            "summary": "DeepEval custom async job / DeepEval 异步自定义评测",
            "description": "Custom GEval-style quality check with a caller-provided criterion.",
            "value": {
                "name": "swagger-custom-quality-job",
                "eval_type": "custom",
                "engine_id": "deepeval",
                "input": {
                    "type": "inline_test_cases",
                    "test_cases": [
                        {
                            "user_input": "Explain Cortex Parse in one sentence.",
                            "actual_output": (
                                "Cortex Parse converts web pages and files into Markdown "
                                "with normalized metadata."
                            ),
                            "expected_output": (
                                "Cortex Parse should mention Markdown and standardized metadata."
                            ),
                        }
                    ],
                },
                "metrics": [
                    {
                        "metric_key": "quality.correctness",
                        "threshold": 0.8,
                        "params": {
                            "criteria": (
                                "Score whether the answer correctly explains the business "
                                "purpose of Cortex Parse."
                            )
                        },
                    }
                ],
                "webhook": {
                    "url": "https://example.com/hooks/cortex/eval",
                    "event_types": ["job.succeeded", "job.failed"],
                },
            },
        },
    },
)

SYNTHESIS_SYNC_REQUEST_EXAMPLES: dict[str, Example] = cast(
    dict[str, Example],
    {
        "rag_goldens": {
            "summary": "RAG goldens synthesis / RAG 黄金集生成",
            "description": (
                "Generate a small synchronous preview set of RAG golden samples from documents."
            ),
            "value": {
                "name": "Support-RAG-Goldens",
                "synthesis_type": "rag_goldens",
                "engine_id": "auto",
                "source": {
                    "type": "documents",
                    "documents": [
                        "Cortex exposes Parse, Storage, Knowledge, Evaluation, and Synthesis APIs."
                    ],
                },
                "config": {
                    "sample_count": 5,
                    "quality_gates": [{"metric_key": "quality.correctness", "threshold": 0.8}],
                },
                "output": {"output_format": "json"},
            },
        },
        "sdv_single_table": {
            "summary": "SDV single-table sync / SDV 单表同步合成",
            "description": (
                "Generate a small structured preview from inline records. Requires the SDV "
                "runtime dependency for synchronous execution."
            ),
            "value": {
                "name": "swagger-sdv-customers",
                "synthesis_type": "structured_single_table",
                "engine_id": "sdv",
                "source": {
                    "type": "inline_records",
                    "inline_records": [
                        {"customer_id": "c1", "tier": "gold", "monthly_spend": 1200},
                        {"customer_id": "c2", "tier": "silver", "monthly_spend": 300},
                    ],
                    "options": {"table_name": "customers"},
                },
                "config": {
                    "sample_count": 5,
                    "anonymize_pii": True,
                    "quality_gates": [
                        {"metric_key": "quality.row_count_match", "threshold": 1.0}
                    ],
                },
                "output": {"output_format": "json", "include_preview": True},
            },
        },
        "deepeval_qa_pairs": {
            "summary": "DeepEval QA sync / DeepEval QA 同步合成",
            "description": "Generate a tiny QA preview from inline document context.",
            "value": {
                "name": "swagger-qa-preview",
                "synthesis_type": "qa_pairs",
                "engine_id": "deepeval",
                "source": {
                    "type": "documents",
                    "documents": [
                        "Cortex Parse turns URLs and storage objects into LLM-ready Markdown."
                    ],
                },
                "config": {
                    "sample_count": 2,
                    "max_contexts_per_case": 1,
                    "include_expected_output": True,
                },
                "output": {"output_format": "json", "include_preview": True},
            },
        },
    },
)

SYNTHESIS_JOB_REQUEST_EXAMPLES: dict[str, Example] = cast(
    dict[str, Example],
    {
        "qa_pairs_job": {
            "summary": "QA pairs synthesis job / QA 对生成作业",
            "description": (
                "Recommended async submission for larger synthetic dataset generation workloads."
            ),
            "value": {
                "name": "Product-QA-Synth",
                "synthesis_type": "qa_pairs",
                "engine_id": "auto",
                "source": {
                    "type": "inline_records",
                    "inline_records": [
                        {"document": "Cortex supports pluggable evaluation and synthesis engines."}
                    ],
                },
                "config": {
                    "sample_count": 100,
                    "quality_gates": [{"metric_key": "quality.correctness", "threshold": 0.8}],
                },
                "output": {"output_format": "jsonl"},
                "webhook": {
                    "url": "https://example.com/hooks/cortex/synthesis",
                    "event_types": ["job.succeeded", "job.failed"],
                },
            },
        },
        "sdv_relational_job": {
            "summary": "SDV relational async job / SDV 关系型异步合成",
            "description": (
                "Async relational synthesis from inline table samples. This example is designed "
                "for local Swagger testing with the runtime synthesis worker."
            ),
            "value": {
                "name": "swagger-sdv-orders",
                "synthesis_type": "structured_relational",
                "engine_id": "sdv",
                "source": {
                    "type": "relational_metadata",
                    "options": {
                        "tables": {
                            "customers": [
                                {"customer_id": "c1", "tier": "gold"},
                                {"customer_id": "c2", "tier": "silver"},
                            ],
                            "orders": [
                                {"order_id": "o1", "customer_id": "c1", "amount": 99.0},
                                {"order_id": "o2", "customer_id": "c2", "amount": 42.0},
                            ],
                        }
                    },
                },
                "config": {"sample_count": 3, "anonymize_pii": True},
                "output": {"output_format": "jsonl", "include_preview": True},
            },
        },
        "deepeval_conversation_job": {
            "summary": "DeepEval conversation async job / DeepEval 会话异步合成",
            "description": "Async conversation golden generation from seed support-policy context.",
            "value": {
                "name": "swagger-conversation-goldens",
                "synthesis_type": "conversation_goldens",
                "engine_id": "deepeval",
                "source": {
                    "type": "documents",
                    "documents": [
                        "Support agents should ask for the object_id before parsing a private file."
                    ],
                },
                "config": {
                    "sample_count": 3,
                    "max_contexts_per_case": 1,
                    "include_expected_output": True,
                },
                "output": {"output_format": "jsonl", "include_preview": True},
                "webhook": {
                    "url": "https://example.com/hooks/cortex/synthesis",
                    "event_types": ["job.succeeded", "job.failed"],
                },
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
