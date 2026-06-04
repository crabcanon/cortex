# TensorZero Cortex Experiment Report

- Run ID: `tzcx_20260509_083215_854b667f`
- Dataset: `tensorzero_cortex_tzcx_20260509_083215_854b667f`
- TensorZero Gateway: http://127.0.0.1:3002
- TensorZero UI: http://127.0.0.1:4000

## Scorecard

- `parse_markdown_quality`: 0.7444
- `rag_context_quality`: 0.9245
- `llm_answer_quality`: 0.6727
- `rag_end_to_end_pass_rate`: 1.0
- `rag_end_to_end_pass`: True
- `tensorzero_strategy`: exhaustive
- `tensorzero_variants_requested`: ['openrouter']
- `tensorzero_variant_counts`: {'openrouter': 5}
- `tensorzero_inference_count`: 5
- `tensorzero_error_count`: 0
- `parse_success_count`: 6
- `parse_failure_count`: 0
- `parse_by_engine`: {'auto': {'success': 1, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 78026}, 'crawl4ai': {'success': 1, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 78026}, 'markitdown': {'success': 1, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 43010}, 'llama_parse': {'success': 1, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 13730}, 'jina_reader': {'success': 1, 'failure': 0, 'avg_score': 0.4666, 'markdown_chars': 1903}, 'docling': {'success': 1, 'failure': 0, 'avg_score': 0.0, 'markdown_chars': 0}}
- `context_group_count`: 5
- `context_source`: parse_artifact_fallback
- `knowledge_status`: failed
- `cortex_eval_mode`: async
- `cortex_eval_types`: ['rag', 'custom']

## Parse Artifacts

| URL | Engine | Mode | Markdown chars | Parse score | Object ID | Error |
| --- | --- | --- | ---: | ---: | --- | --- |
| Federal Reserve FOMC calendar | `auto` | `sync` | 78026 | 1.000 | obj_0306dc7403fd473193b624b2 |  |
| Federal Reserve FOMC calendar | `crawl4ai` | `sync` | 78026 | 1.000 | obj_2d6c711e60054901a5d7c1af |  |
| Federal Reserve FOMC calendar | `markitdown` | `sync` | 43010 | 1.000 | obj_f41bad3bea3e4cdfb1e593ec |  |
| Federal Reserve FOMC calendar | `llama_parse` | `sync` | 13730 | 1.000 | obj_1e119188972942dd8231db5f |  |
| Federal Reserve FOMC calendar | `jina_reader` | `sync` | 1903 | 0.467 | obj_2da2a22969e543209c61b8e1 |  |
| Federal Reserve FOMC calendar | `docling` | `async` | 0 | 0.000 | obj_5b853af190aa4c958a124af9 |  |

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
| `openrouter` | `parse_engine:auto` | `auto` | 0.4633 | True | `019e0bde-d6bb-7511-889d-c1b2c4c4ba08` |  |
| `openrouter` | `parse_engine:crawl4ai` | `crawl4ai` | 0.92 | True | `019e0bde-e9de-7a81-aa01-824ae01f643a` |  |
| `openrouter` | `parse_engine:jina_reader` | `jina_reader` | 0.6767 | True | `019e0bde-fb78-7632-a662-5ed2557d101d` |  |
| `openrouter` | `parse_engine:llama_parse` | `llama_parse` | 0.6567 | True | `019e0bdf-0a45-7a10-801a-0c3bfbc52428` |  |
| `openrouter` | `parse_engine:markitdown` | `markitdown` | 0.6467 | True | `019e0bdf-166f-78e1-b87e-778ec63a38e3` |  |

## Evaluation Cases

- `openrouter` on `parse_engine:auto`: 对比这些来源中主要的宏观经济、通货膨胀、货币政策及金融稳定风险。请注明来源名称。
- `openrouter` on `parse_engine:crawl4ai`: 对比这些来源中主要的宏观经济、通货膨胀、货币政策及金融稳定风险。请注明来源名称。
- `openrouter` on `parse_engine:jina_reader`: 对比这些来源中主要的宏观经济、通货膨胀、货币政策及金融稳定风险。请注明来源名称。

## Artifacts

- Eval dataset JSONL: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260509_083215_854b667f\tensorzero_eval_dataset.jsonl`
- Knowledge graph HTML: `not generated`
- JSON report: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260509_083215_854b667f\report.json`
