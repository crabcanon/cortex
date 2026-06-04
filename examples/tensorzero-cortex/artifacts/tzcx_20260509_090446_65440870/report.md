# TensorZero Cortex Experiment Report

- Run ID: `tzcx_20260509_090446_65440870`
- Dataset: `tensorzero_cortex_tzcx_20260509_090446_65440870`
- TensorZero Gateway: http://127.0.0.1:3002
- TensorZero UI: http://127.0.0.1:4000

## Scorecard

- `parse_markdown_quality`: 0.7444
- `rag_context_quality`: 0.9245
- `llm_answer_quality`: 0.6893
- `rag_end_to_end_pass_rate`: 1.0
- `rag_end_to_end_pass`: True
- `tensorzero_strategy`: exhaustive
- `tensorzero_variants_requested`: ['openrouter']
- `tensorzero_variant_counts`: {'openrouter': 5}
- `tensorzero_inference_count`: 5
- `tensorzero_error_count`: 0
- `parse_success_count`: 6
- `parse_failure_count`: 0
- `parse_by_engine`: {'auto': {'success': 1, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 78026}, 'crawl4ai': {'success': 1, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 78026}, 'markitdown': {'success': 1, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 43010}, 'llama_parse': {'success': 1, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 13793}, 'jina_reader': {'success': 1, 'failure': 0, 'avg_score': 0.4666, 'markdown_chars': 1903}, 'docling': {'success': 1, 'failure': 0, 'avg_score': 0.0, 'markdown_chars': 0}}
- `context_group_count`: 5
- `context_source`: parse_artifact_fallback
- `knowledge_status`: built
- `cortex_eval_mode`: async
- `cortex_eval_types`: ['rag', 'custom']

## Parse Artifacts

| URL | Engine | Mode | Markdown chars | Parse score | Object ID | Error |
| --- | --- | --- | ---: | ---: | --- | --- |
| Federal Reserve FOMC calendar | `auto` | `sync` | 78026 | 1.000 | obj_578d25feeb054427a9333a68 |  |
| Federal Reserve FOMC calendar | `crawl4ai` | `sync` | 78026 | 1.000 | obj_8b3489427e974fd585665b48 |  |
| Federal Reserve FOMC calendar | `markitdown` | `sync` | 43010 | 1.000 | obj_d95d41c252c240fa87b5d2ff |  |
| Federal Reserve FOMC calendar | `llama_parse` | `sync` | 13793 | 1.000 | obj_8b92ba59608c483e94825d86 |  |
| Federal Reserve FOMC calendar | `jina_reader` | `sync` | 1903 | 0.467 | obj_80a8ae6ade3e457e9fb54a27 |  |
| Federal Reserve FOMC calendar | `docling` | `async` | 0 | 0.000 | obj_208442b2405742ca92981aa8 |  |

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
| `openrouter` | `parse_engine:auto` | `auto` | 0.6567 | True | `019e0bfd-0f81-7692-894d-e6ca2a5596e1` |  |
| `openrouter` | `parse_engine:crawl4ai` | `crawl4ai` | 0.86 | True | `019e0bfd-1e75-7da3-a72e-4bed94a35a98` |  |
| `openrouter` | `parse_engine:jina_reader` | `jina_reader` | 0.82 | True | `019e0bfd-2a70-7780-b31e-3a5a95e8deaa` |  |
| `openrouter` | `parse_engine:llama_parse` | `llama_parse` | 0.6567 | True | `019e0bfd-3636-7160-8306-bbd046139d8b` |  |
| `openrouter` | `parse_engine:markitdown` | `markitdown` | 0.4533 | True | `019e0bfd-4263-7122-a8cd-73e7f4e1fc7d` |  |

## Evaluation Cases

- `openrouter` on `parse_engine:auto`: 对比这些来源中主要的宏观经济、通货膨胀、货币政策及金融稳定风险。请注明来源名称。
- `openrouter` on `parse_engine:crawl4ai`: 对比这些来源中主要的宏观经济、通货膨胀、货币政策及金融稳定风险。请注明来源名称。
- `openrouter` on `parse_engine:jina_reader`: 对比这些来源中主要的宏观经济、通货膨胀、货币政策及金融稳定风险。请注明来源名称。

## Artifacts

- Eval dataset JSONL: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260509_090446_65440870\tensorzero_eval_dataset.jsonl`
- Knowledge graph HTML: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260509_090446_65440870\knowledge_graph.html`
- JSON report: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260509_090446_65440870\report.json`
