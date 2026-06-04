# TensorZero Cortex Experiment Report

- Run ID: `tzcx_20260508_090112_d6ecf380`
- Dataset: `tensorzero_cortex_tzcx_20260508_090112_d6ecf380`
- TensorZero Gateway: http://127.0.0.1:3002
- TensorZero UI: http://127.0.0.1:4000

## Scorecard

- `parse_markdown_quality`: 0.8148
- `rag_context_quality`: 0.6156
- `llm_answer_quality`: 0.5133
- `rag_end_to_end_pass_rate`: 0.4
- `rag_end_to_end_pass`: False
- `tensorzero_strategy`: exhaustive
- `tensorzero_variants_requested`: ['openai', 'gemini', 'kimi']
- `tensorzero_variant_counts`: {'openai': 5, 'gemini': 5, 'kimi': 5}
- `tensorzero_inference_count`: 5
- `tensorzero_error_count`: 10
- `parse_success_count`: 8
- `parse_failure_count`: 4
- `parse_by_engine`: {'auto': {'success': 2, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 256658}, 'crawl4ai': {'success': 1, 'failure': 1, 'avg_score': 1.0, 'markdown_chars': 78026}, 'markitdown': {'success': 1, 'failure': 1, 'avg_score': 1.0, 'markdown_chars': 43010}, 'llama_parse': {'success': 2, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 192362}, 'jina_reader': {'success': 1, 'failure': 1, 'avg_score': 0.5183, 'markdown_chars': 3086}, 'docling': {'success': 1, 'failure': 1, 'avg_score': 0.0, 'markdown_chars': 0}}
- `context_group_count`: 5
- `context_source`: parse_artifact_fallback
- `knowledge_status`: failed
- `cortex_eval_mode`: async
- `cortex_eval_types`: ['rag', 'custom']

## Parse Artifacts

| URL | Engine | Mode | Markdown chars | Parse score | Object ID | Error |
| --- | --- | --- | ---: | ---: | --- | --- |
| Federal Reserve FOMC calendar | `auto` | `sync` | 78026 | 1.000 | obj_d1670eebe1e24b99aef596c4 |  |
| Federal Reserve FOMC calendar | `crawl4ai` | `sync` | 78026 | 1.000 | obj_64e403bb51d3495a969a318f |  |
| Federal Reserve FOMC calendar | `markitdown` | `sync` | 43010 | 1.000 | obj_5832b8127be943e9b034b3d8 |  |
| Federal Reserve FOMC calendar | `llama_parse` | `sync` | 13730 | 1.000 | obj_e55d20e9e9fa4b22b391c235 |  |
| Federal Reserve FOMC calendar | `jina_reader` | `sync` | 3086 | 0.518 | obj_1c16099d60f1441b8ae6b9ae |  |
| Federal Reserve FOMC calendar | `docling` | `async` | 0 | 0.000 | obj_efd01797932a4325aa750707 |  |
| Federal Reserve Financial Stability Report PDF | `auto` | `sync` | 178632 | 1.000 | obj_18b7edd55cf84aed9b80134e |  |
| Federal Reserve Financial Stability Report PDF | `crawl4ai` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 422: No active parse engine can handle the requested source. |
| Federal Reserve Financial Stability Report PDF | `markitdown` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: markitdown:engine_execution_failed (File conversion failed after 1 attempts:  - PdfConv |
| Federal Reserve Financial Stability Report PDF | `llama_parse` | `sync` | 178632 | 1.000 | obj_250f38fb63074ce48ae89ab7 |  |
| Federal Reserve Financial Stability Report PDF | `jina_reader` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: jina_reader:engine_execution_failed (Client error '422 Unprocessable Entity' for url 'h |
| Federal Reserve Financial Stability Report PDF | `docling` | `async` | 0 | 0.000 |  | Job job_de8ed0f9f2134513ab9da07c ended as failed: {'job_id': 'job_de8ed0f9f2134513ab9da07c', 'job_type': 'parse', 'status': 'failed', 'operation_name': 'parse.document.async', 'sub |

## Context Groups

| Context | Source | Parse Engine | Chars | Context score |
| --- | --- | --- | ---: | ---: |
| `parse_engine:auto` | parse_artifact | `auto` | 6000 | 0.650 |
| `parse_engine:crawl4ai` | parse_artifact | `crawl4ai` | 6000 | 0.650 |
| `parse_engine:jina_reader` | parse_artifact | `jina_reader` | 3260 | 0.478 |
| `parse_engine:llama_parse` | parse_artifact | `llama_parse` | 6000 | 0.650 |
| `parse_engine:markitdown` | parse_artifact | `markitdown` | 6000 | 0.650 |

## TensorZero Inferences

| Variant | Context | Parse Engine | Answer score | E2E pass | Inference ID | Error |
| --- | --- | --- | ---: | --- | --- | --- |
| `openai` | `parse_engine:auto` | `auto` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:auto` | `auto` | 0.6333 | True | `019e06d7-9126-7a70-9e7e-bb125dbc6806` |  |
| `kimi` | `parse_engine:auto` | `auto` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |
| `openai` | `parse_engine:crawl4ai` | `crawl4ai` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:crawl4ai` | `crawl4ai` | 0.4333 | False | `019e06d9-9319-7180-9a4b-49c62df287ae` |  |
| `kimi` | `parse_engine:crawl4ai` | `crawl4ai` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |
| `openai` | `parse_engine:jina_reader` | `jina_reader` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:jina_reader` | `jina_reader` | 0.6333 | True | `019e06da-e2c5-7cd2-958d-bd6d6f0c52c1` |  |
| `kimi` | `parse_engine:jina_reader` | `jina_reader` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |
| `openai` | `parse_engine:llama_parse` | `llama_parse` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:llama_parse` | `llama_parse` | 0.4333 | False | `019e06dc-1544-7df0-a8f6-147b944f6278` |  |
| `kimi` | `parse_engine:llama_parse` | `llama_parse` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |
| `openai` | `parse_engine:markitdown` | `markitdown` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: openai: Error 429 Too Many Requests from openai client: {\n    \"error\": {\n        \"m |
| `gemini` | `parse_engine:markitdown` | `markitdown` | 0.4333 | False | `019e06dd-2822-70f2-9613-37326cb24720` |  |
| `kimi` | `parse_engine:markitdown` | `markitdown` |  |  | `` | TensorZero inference failed: 500 {"error":"All model providers failed to infer with errors: kimi_openai_compatible: Error from openai client: Error sending request: error sending r |

## Evaluation Cases

- `gemini` on `parse_engine:auto`: 对比这些来源中主要的宏观经济、通货膨胀、货币政策及金融稳定风险。请注明来源名称。
- `gemini` on `parse_engine:crawl4ai`: 对比这些来源中主要的宏观经济、通货膨胀、货币政策及金融稳定风险。请注明来源名称。
- `gemini` on `parse_engine:jina_reader`: 对比这些来源中主要的宏观经济、通货膨胀、货币政策及金融稳定风险。请注明来源名称。

## Artifacts

- Eval dataset JSONL: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260508_090112_d6ecf380\tensorzero_eval_dataset.jsonl`
- Knowledge graph HTML: `not generated`
- JSON report: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260508_090112_d6ecf380\report.json`
