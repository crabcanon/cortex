# TensorZero Cortex Experiment Report

- Run ID: `tzcx_20260509_060039_721a43d6`
- Dataset: `tensorzero_cortex_tzcx_20260509_060039_721a43d6`
- TensorZero Gateway: http://127.0.0.1:3002
- TensorZero UI: http://127.0.0.1:4000

## Scorecard

- `parse_markdown_quality`: 0.8933
- `rag_context_quality`: 0.9245
- `llm_answer_quality`: 0.6953
- `rag_end_to_end_pass_rate`: 1.0
- `rag_end_to_end_pass`: True
- `tensorzero_strategy`: exhaustive
- `tensorzero_variants_requested`: ['openrouter']
- `tensorzero_variant_counts`: {'openrouter': 5}
- `tensorzero_inference_count`: 5
- `tensorzero_error_count`: 0
- `parse_success_count`: 5
- `parse_failure_count`: 1
- `parse_by_engine`: {'auto': {'success': 1, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 78026}, 'crawl4ai': {'success': 1, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 78026}, 'markitdown': {'success': 1, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 43010}, 'llama_parse': {'success': 1, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 13730}, 'jina_reader': {'success': 1, 'failure': 0, 'avg_score': 0.4666, 'markdown_chars': 1903}, 'docling': {'success': 0, 'failure': 1, 'avg_score': 0.0, 'markdown_chars': 0}}
- `context_group_count`: 5
- `context_source`: parse_artifact_fallback
- `knowledge_status`: failed
- `cortex_eval_mode`: async
- `cortex_eval_types`: ['rag', 'custom']

## Parse Artifacts

| URL | Engine | Mode | Markdown chars | Parse score | Object ID | Error |
| --- | --- | --- | ---: | ---: | --- | --- |
| Federal Reserve FOMC calendar | `auto` | `sync` | 78026 | 1.000 | obj_139d539d428a415590d9d6d7 |  |
| Federal Reserve FOMC calendar | `crawl4ai` | `sync` | 78026 | 1.000 | obj_ad9aa6b347544045943cf08f |  |
| Federal Reserve FOMC calendar | `markitdown` | `sync` | 43010 | 1.000 | obj_6457c9eec63a42929712b233 |  |
| Federal Reserve FOMC calendar | `llama_parse` | `sync` | 13730 | 1.000 | obj_251a95d60f5b4833822a32dc |  |
| Federal Reserve FOMC calendar | `jina_reader` | `sync` | 1903 | 0.467 | obj_ec7b465522e742aa81854a64 |  |
| Federal Reserve FOMC calendar | `docling` | `async` | 0 | 0.000 |  | Cortex API is unreachable at http://127.0.0.1:8080 while calling GET /v1/jobs/job_5a2c49083e7743c3b7d73296: Server disconnected without sending a response.. Start Cortex API or set |

## Context Groups

| Context | Source | Parse Engine | Chars | Context score |
| --- | --- | --- | ---: | ---: |
| `parse_engine:auto` | parse_artifact | `auto` | 6000 | 1.000 |
| `parse_engine:crawl4ai` | parse_artifact | `crawl4ai` | 6000 | 1.000 |
| `parse_engine:jina_reader` | parse_artifact | `jina_reader` | 2077 | 0.622 |
| `parse_engine:llama_parse` | parse_artifact | `llama_parse` | 6000 | 1.000 |
| `parse_engine:markitdown` | parse_artifact | `markitdown` | 6000 | 1.000 |

## TensorZero Inferences

| Variant | Context | Parse Engine | Answer score | E2E pass | Inference ID | Error |
| --- | --- | --- | ---: | --- | --- | --- |
| `openrouter` | `parse_engine:auto` | `auto` | 0.84 | True | `019e0b58-4d0e-7e93-aa54-5e0ba9570406` |  |
| `openrouter` | `parse_engine:crawl4ai` | `crawl4ai` | 0.88 | True | `019e0b58-5dc6-7192-a4c4-028d50227e57` |  |
| `openrouter` | `parse_engine:jina_reader` | `jina_reader` | 0.4633 | True | `019e0b58-6b01-7b80-a90b-67f217e18b04` |  |
| `openrouter` | `parse_engine:llama_parse` | `llama_parse` | 0.6467 | True | `019e0b58-773c-7551-8851-f1e530f708c5` |  |
| `openrouter` | `parse_engine:markitdown` | `markitdown` | 0.6467 | True | `019e0b58-8584-7802-b9da-b7eed8391244` |  |

## Evaluation Cases

- `openrouter` on `parse_engine:auto`: 对比这些来源中主要的宏观经济、通货膨胀、货币政策及金融稳定风险。请注明来源名称。
- `openrouter` on `parse_engine:crawl4ai`: 对比这些来源中主要的宏观经济、通货膨胀、货币政策及金融稳定风险。请注明来源名称。
- `openrouter` on `parse_engine:jina_reader`: 对比这些来源中主要的宏观经济、通货膨胀、货币政策及金融稳定风险。请注明来源名称。

## Artifacts

- Eval dataset JSONL: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260509_060039_721a43d6\tensorzero_eval_dataset.jsonl`
- Knowledge graph HTML: `not generated`
- JSON report: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260509_060039_721a43d6\report.json`
