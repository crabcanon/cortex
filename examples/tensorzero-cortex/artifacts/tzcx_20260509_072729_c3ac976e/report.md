# TensorZero Cortex Experiment Report

- Run ID: `tzcx_20260509_072729_c3ac976e`
- Dataset: `tensorzero_cortex_tzcx_20260509_072729_c3ac976e`
- TensorZero Gateway: http://127.0.0.1:3002
- TensorZero UI: http://127.0.0.1:4000

## Scorecard

- `parse_markdown_quality`: 0.7492
- `rag_context_quality`: 0.9343
- `llm_answer_quality`: 0.732
- `rag_end_to_end_pass_rate`: 1.0
- `rag_end_to_end_pass`: True
- `tensorzero_strategy`: exhaustive
- `tensorzero_variants_requested`: ['openrouter']
- `tensorzero_variant_counts`: {'openrouter': 5}
- `tensorzero_inference_count`: 5
- `tensorzero_error_count`: 0
- `parse_success_count`: 6
- `parse_failure_count`: 0
- `parse_by_engine`: {'auto': {'success': 1, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 78026}, 'crawl4ai': {'success': 1, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 78026}, 'markitdown': {'success': 1, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 43010}, 'llama_parse': {'success': 1, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 13730}, 'jina_reader': {'success': 1, 'failure': 0, 'avg_score': 0.4952, 'markdown_chars': 2556}, 'docling': {'success': 1, 'failure': 0, 'avg_score': 0.0, 'markdown_chars': 0}}
- `context_group_count`: 5
- `context_source`: parse_artifact_fallback
- `knowledge_status`: failed
- `cortex_eval_mode`: async
- `cortex_eval_types`: ['rag', 'custom']

## Parse Artifacts

| URL | Engine | Mode | Markdown chars | Parse score | Object ID | Error |
| --- | --- | --- | ---: | ---: | --- | --- |
| Federal Reserve FOMC calendar | `auto` | `sync` | 78026 | 1.000 | obj_42b79283565c4e8cb8c9c563 |  |
| Federal Reserve FOMC calendar | `crawl4ai` | `sync` | 78026 | 1.000 | obj_b4a2c24328fb4c87816ffc86 |  |
| Federal Reserve FOMC calendar | `markitdown` | `sync` | 43010 | 1.000 | obj_1a819d754ae24bf8b15f49d3 |  |
| Federal Reserve FOMC calendar | `llama_parse` | `sync` | 13730 | 1.000 | obj_338a9bf5076b437a99d7f75a |  |
| Federal Reserve FOMC calendar | `jina_reader` | `sync` | 2556 | 0.495 | obj_133b312b74974798803b5cce |  |
| Federal Reserve FOMC calendar | `docling` | `async` | 0 | 0.000 | obj_fcffddc94e11487b9f29c741 |  |

## Context Groups

| Context | Source | Parse Engine | Chars | Context score |
| --- | --- | --- | ---: | ---: |
| `parse_engine:auto` | parse_artifact | `auto` | 6000 | 1.000 |
| `parse_engine:crawl4ai` | parse_artifact | `crawl4ai` | 6000 | 1.000 |
| `parse_engine:jina_reader` | parse_artifact | `jina_reader` | 2730 | 0.671 |
| `parse_engine:llama_parse` | parse_artifact | `llama_parse` | 6000 | 1.000 |
| `parse_engine:markitdown` | parse_artifact | `markitdown` | 6000 | 1.000 |

## TensorZero Inferences

| Variant | Context | Parse Engine | Answer score | E2E pass | Inference ID | Error |
| --- | --- | --- | ---: | --- | --- | --- |
| `openrouter` | `parse_engine:auto` | `auto` | 0.88 | True | `019e0ba3-d837-7aa0-a452-7da4b76f4757` |  |
| `openrouter` | `parse_engine:crawl4ai` | `crawl4ai` | 0.6567 | True | `019e0ba3-eaa4-7a60-8605-e09eccd72086` |  |
| `openrouter` | `parse_engine:jina_reader` | `jina_reader` | 0.6467 | True | `019e0ba3-f758-7ba0-88e3-9b0347e2e32d` |  |
| `openrouter` | `parse_engine:llama_parse` | `llama_parse` | 0.6567 | True | `019e0ba4-0350-7761-8fb2-d9e5e6b745f2` |  |
| `openrouter` | `parse_engine:markitdown` | `markitdown` | 0.82 | True | `019e0ba4-0fcc-7b82-8bbf-97a04a3373c7` |  |

## Evaluation Cases

- `openrouter` on `parse_engine:auto`: 对比这些来源中主要的宏观经济、通货膨胀、货币政策及金融稳定风险。请注明来源名称。
- `openrouter` on `parse_engine:crawl4ai`: 对比这些来源中主要的宏观经济、通货膨胀、货币政策及金融稳定风险。请注明来源名称。
- `openrouter` on `parse_engine:jina_reader`: 对比这些来源中主要的宏观经济、通货膨胀、货币政策及金融稳定风险。请注明来源名称。

## Artifacts

- Eval dataset JSONL: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260509_072729_c3ac976e\tensorzero_eval_dataset.jsonl`
- Knowledge graph HTML: `not generated`
- JSON report: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260509_072729_c3ac976e\report.json`
