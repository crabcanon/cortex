# TensorZero Cortex Experiment Report

- Run ID: `tzcx_20260429_085020_bd0c1daa`
- Dataset: `tensorzero_cortex_tzcx_20260429_085020_bd0c1daa`
- TensorZero Gateway: http://127.0.0.1:3002
- TensorZero UI: http://127.0.0.1:4000

## Scorecard

- `parse_markdown_quality`: 0.7889
- `rag_context_quality`: 0.7278
- `llm_answer_quality`: 0.6558
- `rag_end_to_end_pass_rate`: 1.0
- `rag_end_to_end_pass`: True
- `tensorzero_strategy`: exhaustive
- `tensorzero_variants_requested`: ['openai', 'gemini', 'kimi']
- `tensorzero_variant_counts`: {'openai': 4, 'gemini': 4, 'kimi': 4}
- `tensorzero_inference_count`: 4
- `tensorzero_error_count`: 8
- `parse_success_count`: 9
- `parse_failure_count`: 6
- `parse_by_engine`: {'auto': {'success': 3, 'failure': 0, 'avg_score': 0.85, 'markdown_chars': 295808}, 'crawl4ai': {'success': 2, 'failure': 1, 'avg_score': 0.775, 'markdown_chars': 119522}, 'markitdown': {'success': 1, 'failure': 2, 'avg_score': 1.0, 'markdown_chars': 42750}, 'llama_parse': {'success': 2, 'failure': 1, 'avg_score': 1.0, 'markdown_chars': 189459}, 'docling': {'success': 1, 'failure': 2, 'avg_score': 0.0, 'markdown_chars': 0}}
- `context_group_count`: 4
- `context_source`: parse_artifact_fallback
- `knowledge_status`: failed
- `cortex_eval_mode`: async
- `cortex_eval_types`: ['rag', 'custom']

## Parse Artifacts

| URL | Engine | Mode | Markdown chars | Parse score | Object ID | Error |
| --- | --- | --- | ---: | ---: | --- | --- |
| Federal Reserve FOMC calendar | `auto` | `sync` | 77648 | 1.000 | obj_11e833233bf1403689bb6ef5 |  |
| Federal Reserve FOMC calendar | `crawl4ai` | `sync` | 77648 | 1.000 | obj_c226e04284394825be2353b1 |  |
| Federal Reserve FOMC calendar | `markitdown` | `sync` | 42750 | 1.000 | obj_4f2c88bbbcd144dd8a199a39 |  |
| Federal Reserve FOMC calendar | `llama_parse` | `sync` | 13173 | 1.000 | obj_b8622ba9ad844ae9b6d83380 |  |
| Federal Reserve FOMC calendar | `docling` | `async` | 0 | 0.000 | obj_e8dafbac2d09420b8baea375 |  |
| Federal Reserve Financial Stability Report PDF | `auto` | `sync` | 176286 | 1.000 | obj_2e253d50c42e41b188b2ca27 |  |
| Federal Reserve Financial Stability Report PDF | `crawl4ai` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 422: No active parse engine can handle the requested source. |
| Federal Reserve Financial Stability Report PDF | `markitdown` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: markitdown:engine_execution_failed (File conversion failed after 1 attempts:  - PdfConv |
| Federal Reserve Financial Stability Report PDF | `llama_parse` | `sync` | 176286 | 1.000 | obj_e00dfbae23ac450d854ee634 |  |
| Federal Reserve Financial Stability Report PDF | `docling` | `async` | 0 | 0.000 |  | Job job_7b9cce8892ac4205aab679fd ended as failed: {'job_id': 'job_7b9cce8892ac4205aab679fd', 'job_type': 'parse', 'status': 'failed', 'operation_name': 'parse.document.async', 'sub |
| Federal Reserve Beige Book | `auto` | `sync` | 41874 | 0.550 | obj_d4ad1ef55ec74252a0b936a2 |  |
| Federal Reserve Beige Book | `crawl4ai` | `sync` | 41874 | 0.550 | obj_028652c3dda142d18d8d463c |  |
| Federal Reserve Beige Book | `markitdown` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: markitdown:engine_execution_failed (404 Client Error: Not Found for url: https://www.fe |
| Federal Reserve Beige Book | `llama_parse` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: llama_parse:config_error (config_error: LlamaParse completed without returning document |
| Federal Reserve Beige Book | `docling` | `async` | 0 | 0.000 |  | Job job_ee668ef925c745448c2506c3 ended as failed: {'job_id': 'job_ee668ef925c745448c2506c3', 'job_type': 'parse', 'status': 'failed', 'operation_name': 'parse.document.async', 'sub |

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
| `gemini` | `parse_engine:auto` | `auto` | 0.7967 | True | `019dd875-0e01-7a11-ac56-ccf48554edc0` |  |
| `kimi` | `parse_engine:auto` | `auto` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |
| `openai` | `parse_engine:crawl4ai` | `crawl4ai` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:crawl4ai` | `crawl4ai` | 0.4944 | True | `019dd875-5b4e-7950-8199-ba1574b70d91` |  |
| `kimi` | `parse_engine:crawl4ai` | `crawl4ai` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |
| `openai` | `parse_engine:llama_parse` | `llama_parse` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:llama_parse` | `llama_parse` | 0.8378 | True | `019dd875-b3f7-71d2-9929-5b7d60a56f81` |  |
| `kimi` | `parse_engine:llama_parse` | `llama_parse` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |
| `openai` | `parse_engine:markitdown` | `markitdown` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:markitdown` | `markitdown` | 0.4944 | True | `019dd876-0470-7212-abc4-5e47606cf127` |  |
| `kimi` | `parse_engine:markitdown` | `markitdown` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |

## Evaluation Cases

- `gemini` on `parse_engine:auto`: Compare the main macroeconomic, inflation, monetary policy, and financial stability risks across these sources. Cite source names.
- `gemini` on `parse_engine:crawl4ai`: Compare the main macroeconomic, inflation, monetary policy, and financial stability risks across these sources. Cite source names.
- `gemini` on `parse_engine:llama_parse`: Compare the main macroeconomic, inflation, monetary policy, and financial stability risks across these sources. Cite source names.
- `gemini` on `parse_engine:markitdown`: Compare the main macroeconomic, inflation, monetary policy, and financial stability risks across these sources. Cite source names.

## Artifacts

- Eval dataset JSONL: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260429_085020_bd0c1daa\tensorzero_eval_dataset.jsonl`
- JSON report: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260429_085020_bd0c1daa\report.json`
