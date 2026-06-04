# TensorZero Cortex Experiment Report

- Run ID: `tzcx_20260429_120013_fb02b449`
- Dataset: `tensorzero_cortex_tzcx_20260429_120013_fb02b449`
- TensorZero Gateway: http://127.0.0.1:3002
- TensorZero UI: http://127.0.0.1:4000

## Scorecard

- `parse_markdown_quality`: 0.7889
- `rag_context_quality`: 0.7278
- `llm_answer_quality`: 0.6508
- `rag_end_to_end_pass_rate`: 0.75
- `rag_end_to_end_pass`: False
- `tensorzero_strategy`: exhaustive
- `tensorzero_variants_requested`: ['openai', 'gemini', 'kimi']
- `tensorzero_variant_counts`: {'openai': 4, 'gemini': 4, 'kimi': 4}
- `tensorzero_inference_count`: 4
- `tensorzero_error_count`: 8
- `parse_success_count`: 9
- `parse_failure_count`: 6
- `parse_by_engine`: {'auto': {'success': 3, 'failure': 0, 'avg_score': 0.85, 'markdown_chars': 295808}, 'crawl4ai': {'success': 2, 'failure': 1, 'avg_score': 0.775, 'markdown_chars': 119522}, 'markitdown': {'success': 1, 'failure': 2, 'avg_score': 1.0, 'markdown_chars': 42750}, 'llama_parse': {'success': 2, 'failure': 1, 'avg_score': 1.0, 'markdown_chars': 187699}, 'docling': {'success': 1, 'failure': 2, 'avg_score': 0.0, 'markdown_chars': 0}}
- `context_group_count`: 4
- `context_source`: parse_artifact_fallback
- `knowledge_status`: failed
- `cortex_eval_mode`: async
- `cortex_eval_types`: ['rag', 'custom']

## Parse Artifacts

| URL | Engine | Mode | Markdown chars | Parse score | Object ID | Error |
| --- | --- | --- | ---: | ---: | --- | --- |
| Federal Reserve FOMC calendar | `auto` | `sync` | 77648 | 1.000 | obj_b2c81eb5c42041c392251a9c |  |
| Federal Reserve FOMC calendar | `crawl4ai` | `sync` | 77648 | 1.000 | obj_333f9fd724fc4bd5ab2a1d7e |  |
| Federal Reserve FOMC calendar | `markitdown` | `sync` | 42750 | 1.000 | obj_847259c17d8f4f4fbf6a1c74 |  |
| Federal Reserve FOMC calendar | `llama_parse` | `sync` | 11413 | 1.000 | obj_2b17e3ca13a3475d814db4ab |  |
| Federal Reserve FOMC calendar | `docling` | `async` | 0 | 0.000 | obj_13003eeea52a46bdab051480 |  |
| Federal Reserve Financial Stability Report PDF | `auto` | `sync` | 176286 | 1.000 | obj_0702d9411ce6445995ed9b2b |  |
| Federal Reserve Financial Stability Report PDF | `crawl4ai` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 422: No active parse engine can handle the requested source. |
| Federal Reserve Financial Stability Report PDF | `markitdown` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: markitdown:engine_execution_failed (File conversion failed after 1 attempts:  - PdfConv |
| Federal Reserve Financial Stability Report PDF | `llama_parse` | `sync` | 176286 | 1.000 | obj_aacf73e24b874755bec82a27 |  |
| Federal Reserve Financial Stability Report PDF | `docling` | `async` | 0 | 0.000 |  | Job job_7500a691fa7547b4b8f1bc63 ended as failed: {'job_id': 'job_7500a691fa7547b4b8f1bc63', 'job_type': 'parse', 'status': 'failed', 'operation_name': 'parse.document.async', 'sub |
| Federal Reserve Beige Book | `auto` | `sync` | 41874 | 0.550 | obj_ec0ea781889d4b058b10dfea |  |
| Federal Reserve Beige Book | `crawl4ai` | `sync` | 41874 | 0.550 | obj_43784f656f8a4d78a5751865 |  |
| Federal Reserve Beige Book | `markitdown` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: markitdown:engine_execution_failed (404 Client Error: Not Found for url: https://www.fe |
| Federal Reserve Beige Book | `llama_parse` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: llama_parse:config_error (config_error: LlamaParse completed without returning document |
| Federal Reserve Beige Book | `docling` | `async` | 0 | 0.000 |  | Job job_02a40a0db2df4d2598f6fb81 ended as failed: {'job_id': 'job_02a40a0db2df4d2598f6fb81', 'job_type': 'parse', 'status': 'failed', 'operation_name': 'parse.document.async', 'sub |

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
| `gemini` | `parse_engine:auto` | `auto` | 0.8178 | True | `019dd923-0175-7160-999f-edb6a8e18c25` |  |
| `kimi` | `parse_engine:auto` | `auto` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |
| `openai` | `parse_engine:crawl4ai` | `crawl4ai` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:crawl4ai` | `crawl4ai` | 0.4944 | True | `019dd923-5170-74d0-98f3-9430993bac16` |  |
| `kimi` | `parse_engine:crawl4ai` | `crawl4ai` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |
| `openai` | `parse_engine:llama_parse` | `llama_parse` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:llama_parse` | `llama_parse` | 0.8578 | True | `019dd923-86dd-7050-bfe8-ca7e2e85ef41` |  |
| `kimi` | `parse_engine:llama_parse` | `llama_parse` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |
| `openai` | `parse_engine:markitdown` | `markitdown` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:markitdown` | `markitdown` | 0.4333 | False | `019dd923-dddf-7e32-993a-568e78584f65` |  |
| `kimi` | `parse_engine:markitdown` | `markitdown` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |

## Evaluation Cases

- `gemini` on `parse_engine:auto`: Compare the main macroeconomic, inflation, monetary policy, and financial stability risks across these sources. Cite source names.
- `gemini` on `parse_engine:crawl4ai`: Compare the main macroeconomic, inflation, monetary policy, and financial stability risks across these sources. Cite source names.
- `gemini` on `parse_engine:llama_parse`: Compare the main macroeconomic, inflation, monetary policy, and financial stability risks across these sources. Cite source names.
- `gemini` on `parse_engine:markitdown`: Compare the main macroeconomic, inflation, monetary policy, and financial stability risks across these sources. Cite source names.

## Artifacts

- Eval dataset JSONL: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260429_120013_fb02b449\tensorzero_eval_dataset.jsonl`
- Knowledge graph HTML: `not generated`
- JSON report: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260429_120013_fb02b449\report.json`
