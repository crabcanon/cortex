# TensorZero Cortex Experiment Report

- Run ID: `tzcx_20260520_030852_8f1d1f63`
- Dataset: `tensorzero_cortex_tzcx_20260520_030852_8f1d1f63`
- TensorZero Gateway: http://127.0.0.1:3002
- TensorZero UI: http://127.0.0.1:4000

## Scorecard

- `parse_markdown_quality`: 0.8135
- `rag_context_quality`: 0.612
- `llm_answer_quality`: 0.6384
- `rag_end_to_end_pass_rate`: 1.0
- `rag_end_to_end_pass`: True
- `tensorzero_strategy`: exhaustive
- `tensorzero_variants_requested`: ['openai', 'gemini', 'kimi']
- `tensorzero_variant_counts`: {'openai': 5, 'gemini': 5, 'kimi': 5}
- `tensorzero_inference_count`: 5
- `tensorzero_error_count`: 10
- `parse_success_count`: 8
- `parse_failure_count`: 4
- `parse_by_engine`: {'auto': {'success': 2, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 252350}, 'crawl4ai': {'success': 1, 'failure': 1, 'avg_score': 1.0, 'markdown_chars': 78026}, 'markitdown': {'success': 1, 'failure': 1, 'avg_score': 1.0, 'markdown_chars': 43010}, 'llama_parse': {'success': 2, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 191218}, 'jina_reader': {'success': 1, 'failure': 1, 'avg_score': 0.5081, 'markdown_chars': 2851}, 'docling': {'success': 1, 'failure': 1, 'avg_score': 0.0, 'markdown_chars': 0}}
- `context_group_count`: 5
- `context_source`: parse_artifact_fallback
- `knowledge_status`: failed
- `cortex_eval_mode`: async
- `cortex_eval_types`: ['rag', 'custom']

## Parse Artifacts

| URL | Engine | Mode | Markdown chars | Parse score | Object ID | Error |
| --- | --- | --- | ---: | ---: | --- | --- |
| Federal Reserve FOMC calendar | `auto` | `sync` | 78026 | 1.000 | obj_1f99f398e1354ef79c659974 |  |
| Federal Reserve FOMC calendar | `crawl4ai` | `sync` | 78026 | 1.000 | obj_4a120db4c2104e07951075ca |  |
| Federal Reserve FOMC calendar | `markitdown` | `sync` | 43010 | 1.000 | obj_3d159e8e9df745bcb7f01de2 |  |
| Federal Reserve FOMC calendar | `llama_parse` | `sync` | 16894 | 1.000 | obj_6f9b69596a124b51aa2a3f6b |  |
| Federal Reserve FOMC calendar | `jina_reader` | `sync` | 2851 | 0.508 | obj_c3569f60ec214bcfbe2f514f |  |
| Federal Reserve FOMC calendar | `docling` | `async` | 0 | 0.000 | obj_7076d5d8818d45ef81601d6d |  |
| Federal Reserve Financial Stability Report PDF | `auto` | `sync` | 174324 | 1.000 | obj_8204f71367664d22a593e603 |  |
| Federal Reserve Financial Stability Report PDF | `crawl4ai` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 422: No active parse engine can handle the requested source. |
| Federal Reserve Financial Stability Report PDF | `markitdown` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: markitdown:engine_execution_failed (File conversion failed after 1 attempts:  - PdfConv |
| Federal Reserve Financial Stability Report PDF | `llama_parse` | `sync` | 174324 | 1.000 | obj_003e55f3c2e04ad693e573fc |  |
| Federal Reserve Financial Stability Report PDF | `jina_reader` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: jina_reader:engine_execution_failed (Client error '422 Unprocessable Entity' for url 'h |
| Federal Reserve Financial Stability Report PDF | `docling` | `async` | 0 | 0.000 |  | Timed out waiting for job job_4fa39016bb95402e8e3791bd. Last status: {'job_id': 'job_4fa39016bb95402e8e3791bd', 'job_type': 'parse', 'status': 'running', 'operation_name': 'parse.d |

## Context Groups

| Context | Source | Parse Engine | Chars | Context score |
| --- | --- | --- | ---: | ---: |
| `parse_engine:auto` | parse_artifact | `auto` | 6000 | 0.650 |
| `parse_engine:crawl4ai` | parse_artifact | `crawl4ai` | 6000 | 0.650 |
| `parse_engine:jina_reader` | parse_artifact | `jina_reader` | 3025 | 0.460 |
| `parse_engine:llama_parse` | parse_artifact | `llama_parse` | 6000 | 0.650 |
| `parse_engine:markitdown` | parse_artifact | `markitdown` | 6000 | 0.650 |

## TensorZero Inferences

| Variant | Context | Parse Engine | Answer score | E2E pass | Inference ID | Error |
| --- | --- | --- | ---: | --- | --- | --- |
| `openai` | `parse_engine:auto` | `auto` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:auto` | `auto` | 0.6167 | True | `019e43cb-046f-7493-ac3d-901e7428ba4b` |  |
| `kimi` | `parse_engine:auto` | `auto` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |
| `openai` | `parse_engine:crawl4ai` | `crawl4ai` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:crawl4ai` | `crawl4ai` | 0.6167 | True | `019e43cb-4f6e-74e3-b9f3-6e1ff63e9d11` |  |
| `kimi` | `parse_engine:crawl4ai` | `crawl4ai` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |
| `openai` | `parse_engine:jina_reader` | `jina_reader` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:jina_reader` | `jina_reader` | 0.6167 | True | `019e43cb-95b8-7341-af0b-86d130c72685` |  |
| `kimi` | `parse_engine:jina_reader` | `jina_reader` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |
| `openai` | `parse_engine:llama_parse` | `llama_parse` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:llama_parse` | `llama_parse` | 0.8167 | True | `019e43cb-c6d9-7dc0-9d04-ecba202bda21` |  |
| `kimi` | `parse_engine:llama_parse` | `llama_parse` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |
| `openai` | `parse_engine:markitdown` | `markitdown` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:markitdown` | `markitdown` | 0.525 | True | `019e43cc-0a87-7cc3-90f2-8def0bbc2996` |  |
| `kimi` | `parse_engine:markitdown` | `markitdown` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |

## Evaluation Cases

- `gemini` on `parse_engine:auto`: Compare the main macroeconomic, inflation, monetary policy, and financial stability risks across these sources. Cite source names.
- `gemini` on `parse_engine:crawl4ai`: Compare the main macroeconomic, inflation, monetary policy, and financial stability risks across these sources. Cite source names.
- `gemini` on `parse_engine:jina_reader`: Compare the main macroeconomic, inflation, monetary policy, and financial stability risks across these sources. Cite source names.

## Artifacts

- Eval dataset JSONL: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260520_030852_8f1d1f63\tensorzero_eval_dataset.jsonl`
- Knowledge graph HTML: `not generated`
- JSON report: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260520_030852_8f1d1f63\report.json`
