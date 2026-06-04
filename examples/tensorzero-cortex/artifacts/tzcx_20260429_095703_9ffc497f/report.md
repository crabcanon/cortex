# TensorZero Cortex Experiment Report

- Run ID: `tzcx_20260429_095703_9ffc497f`
- Dataset: `tensorzero_cortex_tzcx_20260429_095703_9ffc497f`
- TensorZero Gateway: http://127.0.0.1:3002
- TensorZero UI: http://127.0.0.1:4000

## Scorecard

- `parse_markdown_quality`: 0.8187
- `rag_context_quality`: 0.7278
- `llm_answer_quality`: 0.6305
- `rag_end_to_end_pass_rate`: 1.0
- `rag_end_to_end_pass`: True
- `tensorzero_strategy`: exhaustive
- `tensorzero_variants_requested`: ['openai', 'gemini', 'kimi']
- `tensorzero_variant_counts`: {'openai': 4, 'gemini': 4, 'kimi': 4}
- `tensorzero_inference_count`: 4
- `tensorzero_error_count`: 8
- `parse_success_count`: 8
- `parse_failure_count`: 7
- `parse_by_engine`: {'auto': {'success': 2, 'failure': 1, 'avg_score': 1.0, 'markdown_chars': 253934}, 'crawl4ai': {'success': 2, 'failure': 1, 'avg_score': 0.775, 'markdown_chars': 119522}, 'markitdown': {'success': 1, 'failure': 2, 'avg_score': 1.0, 'markdown_chars': 42750}, 'llama_parse': {'success': 2, 'failure': 1, 'avg_score': 1.0, 'markdown_chars': 187779}, 'docling': {'success': 1, 'failure': 2, 'avg_score': 0.0, 'markdown_chars': 0}}
- `context_group_count`: 4
- `context_source`: parse_artifact_fallback
- `knowledge_status`: failed
- `cortex_eval_mode`: async
- `cortex_eval_types`: ['rag', 'custom']

## Parse Artifacts

| URL | Engine | Mode | Markdown chars | Parse score | Object ID | Error |
| --- | --- | --- | ---: | ---: | --- | --- |
| Federal Reserve FOMC calendar | `auto` | `sync` | 77648 | 1.000 | obj_a3a9352337424e8d974bb92b |  |
| Federal Reserve FOMC calendar | `crawl4ai` | `sync` | 77648 | 1.000 | obj_3305bc295ceb4a279775238b |  |
| Federal Reserve FOMC calendar | `markitdown` | `sync` | 42750 | 1.000 | obj_e036636d057045ef906d473f |  |
| Federal Reserve FOMC calendar | `llama_parse` | `sync` | 11493 | 1.000 | obj_135aec033ec14d6ab8249dfe |  |
| Federal Reserve FOMC calendar | `docling` | `async` | 0 | 0.000 | obj_c65a2f75e4c14d7db8d72f95 |  |
| Federal Reserve Financial Stability Report PDF | `auto` | `sync` | 176286 | 1.000 | obj_6bd3b7d0cfd24299ab3d7d23 |  |
| Federal Reserve Financial Stability Report PDF | `crawl4ai` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 422: No active parse engine can handle the requested source. |
| Federal Reserve Financial Stability Report PDF | `markitdown` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: markitdown:engine_execution_failed (File conversion failed after 1 attempts:  - PdfConv |
| Federal Reserve Financial Stability Report PDF | `llama_parse` | `sync` | 176286 | 1.000 | obj_f244bab41fa94c2e9dfe2bad |  |
| Federal Reserve Financial Stability Report PDF | `docling` | `async` | 0 | 0.000 |  | Job job_8df45aada9ee40039ca239d3 ended as failed: {'job_id': 'job_8df45aada9ee40039ca239d3', 'job_type': 'parse', 'status': 'failed', 'operation_name': 'parse.document.async', 'sub |
| Federal Reserve Beige Book | `auto` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: crawl4ai:crawl4ai_failed (crawl4ai_failed: Unexpected error in _crawl_web at line 778 i |
| Federal Reserve Beige Book | `crawl4ai` | `sync` | 41874 | 0.550 | obj_189bad5331c54607928473f8 |  |
| Federal Reserve Beige Book | `markitdown` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: markitdown:engine_execution_failed (404 Client Error: Not Found for url: https://www.fe |
| Federal Reserve Beige Book | `llama_parse` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: llama_parse:config_error (config_error: LlamaParse completed without returning document |
| Federal Reserve Beige Book | `docling` | `async` | 0 | 0.000 |  | Job job_e8c9c944e5ee4d4bb68e0f98 ended as failed: {'job_id': 'job_e8c9c944e5ee4d4bb68e0f98', 'job_type': 'parse', 'status': 'failed', 'operation_name': 'parse.document.async', 'sub |

## Context Groups

| Context | Source | Parse Engine | Chars | Context score |
| --- | --- | --- | ---: | ---: |
| `parse_engine:auto` | parse_artifact | `auto` | 12000 | 0.922 |
| `parse_engine:crawl4ai` | parse_artifact | `crawl4ai` | 12000 | 0.533 |
| `parse_engine:llama_parse` | parse_artifact | `llama_parse` | 12000 | 0.922 |
| `parse_engine:markitdown` | parse_artifact | `markitdown` | 6173 | 0.533 |

## TensorZero Inferences

| Variant | Context | Parse Engine | Answer score | E2E pass | Inference ID | Error |
| --- | --- | --- | ---: | --- | --- | --- |
| `openai` | `parse_engine:auto` | `auto` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:auto` | `auto` | 0.7767 | True | `019dd8b2-0c09-7fc3-8f73-d3db65d79872` |  |
| `kimi` | `parse_engine:auto` | `auto` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |
| `openai` | `parse_engine:crawl4ai` | `crawl4ai` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:crawl4ai` | `crawl4ai` | 0.4944 | True | `019dd8b2-61a4-78b2-b88f-b26b6427ddd9` |  |
| `kimi` | `parse_engine:crawl4ai` | `crawl4ai` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |
| `openai` | `parse_engine:llama_parse` | `llama_parse` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:llama_parse` | `llama_parse` | 0.7567 | True | `019dd8b2-a64e-7963-acef-4f4563c10ee4` |  |
| `kimi` | `parse_engine:llama_parse` | `llama_parse` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |
| `openai` | `parse_engine:markitdown` | `markitdown` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:markitdown` | `markitdown` | 0.4944 | True | `019dd8b2-ede6-7cd0-96d3-3309c765d5ba` |  |
| `kimi` | `parse_engine:markitdown` | `markitdown` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |

## Evaluation Cases

- `gemini` on `parse_engine:auto`: Compare the main macroeconomic, inflation, monetary policy, and financial stability risks across these sources. Cite source names.
- `gemini` on `parse_engine:crawl4ai`: Compare the main macroeconomic, inflation, monetary policy, and financial stability risks across these sources. Cite source names.
- `gemini` on `parse_engine:llama_parse`: Compare the main macroeconomic, inflation, monetary policy, and financial stability risks across these sources. Cite source names.
- `gemini` on `parse_engine:markitdown`: Compare the main macroeconomic, inflation, monetary policy, and financial stability risks across these sources. Cite source names.

## Artifacts

- Eval dataset JSONL: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260429_095703_9ffc497f\tensorzero_eval_dataset.jsonl`
- Knowledge graph HTML: `not generated`
- JSON report: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260429_095703_9ffc497f\report.json`
