# TensorZero Cortex Experiment Report

- Run ID: `tzcx_20260508_083559_4e12b774`
- Dataset: `tensorzero_cortex_tzcx_20260508_083559_4e12b774`
- TensorZero Gateway: http://127.0.0.1:3002
- TensorZero UI: http://127.0.0.1:4000

## Scorecard

- `parse_markdown_quality`: 0.8083
- `rag_context_quality`: 0.5978
- `llm_answer_quality`: 0.495
- `rag_end_to_end_pass_rate`: 0.4
- `rag_end_to_end_pass`: False
- `tensorzero_strategy`: exhaustive
- `tensorzero_variants_requested`: ['openai', 'gemini', 'kimi']
- `tensorzero_variant_counts`: {'openai': 5, 'gemini': 5, 'kimi': 5}
- `tensorzero_inference_count`: 5
- `tensorzero_error_count`: 10
- `parse_success_count`: 8
- `parse_failure_count`: 4
- `parse_by_engine`: {'auto': {'success': 2, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 256658}, 'crawl4ai': {'success': 1, 'failure': 1, 'avg_score': 1.0, 'markdown_chars': 78026}, 'markitdown': {'success': 1, 'failure': 1, 'avg_score': 1.0, 'markdown_chars': 43010}, 'llama_parse': {'success': 2, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 192362}, 'jina_reader': {'success': 1, 'failure': 1, 'avg_score': 0.4666, 'markdown_chars': 1903}, 'docling': {'success': 1, 'failure': 1, 'avg_score': 0.0, 'markdown_chars': 0}}
- `context_group_count`: 5
- `context_source`: parse_artifact_fallback
- `knowledge_status`: failed
- `cortex_eval_mode`: async
- `cortex_eval_types`: ['rag', 'custom']

## Parse Artifacts

| URL | Engine | Mode | Markdown chars | Parse score | Object ID | Error |
| --- | --- | --- | ---: | ---: | --- | --- |
| Federal Reserve FOMC calendar | `auto` | `sync` | 78026 | 1.000 | obj_df8afe90928b4234bb157c63 |  |
| Federal Reserve FOMC calendar | `crawl4ai` | `sync` | 78026 | 1.000 | obj_fe2de668877e46fab7c5e650 |  |
| Federal Reserve FOMC calendar | `markitdown` | `sync` | 43010 | 1.000 | obj_8fd9011b025e4911a6372e34 |  |
| Federal Reserve FOMC calendar | `llama_parse` | `sync` | 13730 | 1.000 | obj_aa6bc14952ed483280a7bf0c |  |
| Federal Reserve FOMC calendar | `jina_reader` | `sync` | 1903 | 0.467 | obj_344ad1f16cc142ee9d87d26f |  |
| Federal Reserve FOMC calendar | `docling` | `async` | 0 | 0.000 | obj_b1b8b2f0fdc54a4ba813fbe2 |  |
| Federal Reserve Financial Stability Report PDF | `auto` | `sync` | 178632 | 1.000 | obj_90b3cdaeeb194b368c891e7a |  |
| Federal Reserve Financial Stability Report PDF | `crawl4ai` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 422: No active parse engine can handle the requested source. |
| Federal Reserve Financial Stability Report PDF | `markitdown` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: markitdown:engine_execution_failed (File conversion failed after 1 attempts:  - PdfConv |
| Federal Reserve Financial Stability Report PDF | `llama_parse` | `sync` | 178632 | 1.000 | obj_e44f0ed3477c496f8f4790ca |  |
| Federal Reserve Financial Stability Report PDF | `jina_reader` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: jina_reader:engine_execution_failed (Client error '422 Unprocessable Entity' for url 'h |
| Federal Reserve Financial Stability Report PDF | `docling` | `async` | 0 | 0.000 |  | Job job_1f838996dc9844f393b7c81b ended as failed: {'job_id': 'job_1f838996dc9844f393b7c81b', 'job_type': 'parse', 'status': 'failed', 'operation_name': 'parse.document.async', 'sub |

## Context Groups

| Context | Source | Parse Engine | Chars | Context score |
| --- | --- | --- | ---: | ---: |
| `parse_engine:auto` | parse_artifact | `auto` | 6000 | 0.650 |
| `parse_engine:crawl4ai` | parse_artifact | `crawl4ai` | 6000 | 0.650 |
| `parse_engine:jina_reader` | parse_artifact | `jina_reader` | 2077 | 0.389 |
| `parse_engine:llama_parse` | parse_artifact | `llama_parse` | 6000 | 0.650 |
| `parse_engine:markitdown` | parse_artifact | `markitdown` | 6000 | 0.650 |

## TensorZero Inferences

| Variant | Context | Parse Engine | Answer score | E2E pass | Inference ID | Error |
| --- | --- | --- | ---: | --- | --- | --- |
| `openai` | `parse_engine:auto` | `auto` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:auto` | `auto` | 0.3417 | False | `019e06c1-3819-7753-b503-38e614aae4c5` |  |
| `kimi` | `parse_engine:auto` | `auto` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |
| `openai` | `parse_engine:crawl4ai` | `crawl4ai` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:crawl4ai` | `crawl4ai` | 0.6333 | True | `019e06c2-a8cb-7110-ad58-90e79746de2e` |  |
| `kimi` | `parse_engine:crawl4ai` | `crawl4ai` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |
| `openai` | `parse_engine:jina_reader` | `jina_reader` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:jina_reader` | `jina_reader` | 0.6333 | True | `019e06c4-bc84-7761-a0e3-664b7eaf8cd9` |  |
| `kimi` | `parse_engine:jina_reader` | `jina_reader` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |
| `openai` | `parse_engine:llama_parse` | `llama_parse` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:llama_parse` | `llama_parse` | 0.4333 | False | `019e06c6-9ceb-7fd1-add0-0ee37cac9ca8` |  |
| `kimi` | `parse_engine:llama_parse` | `llama_parse` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |
| `openai` | `parse_engine:markitdown` | `markitdown` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:markitdown` | `markitdown` | 0.4333 | False | `019e06ca-5a07-7310-b27d-3297c51daa8f` |  |
| `kimi` | `parse_engine:markitdown` | `markitdown` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |

## Evaluation Cases

- `gemini` on `parse_engine:auto`: 对比这些来源中主要的宏观经济、通货膨胀、货币政策及金融稳定风险。请注明来源名称。
- `gemini` on `parse_engine:crawl4ai`: 对比这些来源中主要的宏观经济、通货膨胀、货币政策及金融稳定风险。请注明来源名称。
- `gemini` on `parse_engine:jina_reader`: 对比这些来源中主要的宏观经济、通货膨胀、货币政策及金融稳定风险。请注明来源名称。

## Artifacts

- Eval dataset JSONL: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260508_083559_4e12b774\tensorzero_eval_dataset.jsonl`
- Knowledge graph HTML: `not generated`
- JSON report: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260508_083559_4e12b774\report.json`
