# TensorZero Cortex Experiment Report

- Run ID: `tzcx_20260509_060746_0cf97b90`
- Dataset: `tensorzero_cortex_tzcx_20260509_060746_0cf97b90`
- TensorZero Gateway: http://127.0.0.1:3002
- TensorZero UI: http://127.0.0.1:4000

## Scorecard

- `parse_markdown_quality`: 0.7444
- `rag_context_quality`: 0.9245
- `llm_answer_quality`: 0.728
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
| Federal Reserve FOMC calendar | `auto` | `sync` | 78026 | 1.000 | obj_f910ea3f6c5d4df0b4ebd553 |  |
| Federal Reserve FOMC calendar | `crawl4ai` | `sync` | 78026 | 1.000 | obj_96d42e082b884ee6b7ff97a5 |  |
| Federal Reserve FOMC calendar | `markitdown` | `sync` | 43010 | 1.000 | obj_21ebf948b0ae45acb0e1f55f |  |
| Federal Reserve FOMC calendar | `llama_parse` | `sync` | 13730 | 1.000 | obj_69efe9a640ab4d7895444516 |  |
| Federal Reserve FOMC calendar | `jina_reader` | `sync` | 1903 | 0.467 | obj_067400b39d424d4988bf1639 |  |
| Federal Reserve FOMC calendar | `docling` | `async` | 0 | 0.000 | obj_6ca197ba76324c7385431be4 |  |

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
| `openrouter` | `parse_engine:auto` | `auto` | 0.84 | True | `019e0b5a-a4ce-7b03-9b3f-795f953fde77` |  |
| `openrouter` | `parse_engine:crawl4ai` | `crawl4ai` | 0.83 | True | `019e0b5a-c695-78b2-af67-7a9b0631d1e1` |  |
| `openrouter` | `parse_engine:jina_reader` | `jina_reader` | 0.6567 | True | `019e0b5a-d409-74b1-9c48-0b2c4e0d2438` |  |
| `openrouter` | `parse_engine:llama_parse` | `llama_parse` | 0.4733 | True | `019e0b5a-df80-7300-91e6-f626f6d3d711` |  |
| `openrouter` | `parse_engine:markitdown` | `markitdown` | 0.84 | True | `019e0b5a-ec09-7460-83c4-64b29277f357` |  |

## Evaluation Cases

- `openrouter` on `parse_engine:auto`: 对比这些来源中主要的宏观经济、通货膨胀、货币政策及金融稳定风险。请注明来源名称。
- `openrouter` on `parse_engine:crawl4ai`: 对比这些来源中主要的宏观经济、通货膨胀、货币政策及金融稳定风险。请注明来源名称。
- `openrouter` on `parse_engine:jina_reader`: 对比这些来源中主要的宏观经济、通货膨胀、货币政策及金融稳定风险。请注明来源名称。

## Artifacts

- Eval dataset JSONL: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260509_060746_0cf97b90\tensorzero_eval_dataset.jsonl`
- Knowledge graph HTML: `not generated`
- JSON report: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260509_060746_0cf97b90\report.json`
