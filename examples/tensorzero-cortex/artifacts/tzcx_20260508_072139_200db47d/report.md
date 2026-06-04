# TensorZero Cortex Experiment Report

- Run ID: `tzcx_20260508_072139_200db47d`
- Dataset: `tensorzero_cortex_tzcx_20260508_072139_200db47d`
- TensorZero Gateway: http://127.0.0.1:3002
- TensorZero UI: http://127.0.0.1:4000

## Scorecard

- `parse_markdown_quality`: 0.7444
- `rag_context_quality`: 0.9245
- `llm_answer_quality`: 0.6527
- `rag_end_to_end_pass_rate`: 1.0
- `rag_end_to_end_pass`: True
- `tensorzero_strategy`: exhaustive
- `tensorzero_variants_requested`: ['openrouter']
- `tensorzero_variant_counts`: {'openrouter': 5}
- `tensorzero_inference_count`: 5
- `tensorzero_error_count`: 0
- `parse_success_count`: 6
- `parse_failure_count`: 0
- `parse_by_engine`: {'auto': {'success': 1, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 78026}, 'crawl4ai': {'success': 1, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 78026}, 'markitdown': {'success': 1, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 43010}, 'llama_parse': {'success': 1, 'failure': 0, 'avg_score': 1.0, 'markdown_chars': 15668}, 'jina_reader': {'success': 1, 'failure': 0, 'avg_score': 0.4666, 'markdown_chars': 1903}, 'docling': {'success': 1, 'failure': 0, 'avg_score': 0.0, 'markdown_chars': 0}}
- `context_group_count`: 5
- `context_source`: parse_artifact_fallback
- `knowledge_status`: failed
- `cortex_eval_mode`: async
- `cortex_eval_types`: ['rag', 'custom']

## Parse Artifacts

| URL | Engine | Mode | Markdown chars | Parse score | Object ID | Error |
| --- | --- | --- | ---: | ---: | --- | --- |
| Federal Reserve FOMC calendar | `auto` | `sync` | 78026 | 1.000 | obj_60b888adee8b4efaa97086e4 |  |
| Federal Reserve FOMC calendar | `crawl4ai` | `sync` | 78026 | 1.000 | obj_5ecc324b4428486fb4bf8635 |  |
| Federal Reserve FOMC calendar | `markitdown` | `sync` | 43010 | 1.000 | obj_94f5d9c564c54528bf4bfe9a |  |
| Federal Reserve FOMC calendar | `llama_parse` | `sync` | 15668 | 1.000 | obj_30558bec943f4b1c9287b3c3 |  |
| Federal Reserve FOMC calendar | `jina_reader` | `sync` | 1903 | 0.467 | obj_c4b698def4d64fa5bb7a29f2 |  |
| Federal Reserve FOMC calendar | `docling` | `async` | 0 | 0.000 | obj_17255f6442fb4ce3be8796af |  |

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
| `openrouter` | `parse_engine:auto` | `auto` | 0.84 | True | `019e0677-ac1d-7043-85fa-41af64a6fe20` |  |
| `openrouter` | `parse_engine:crawl4ai` | `crawl4ai` | 0.4633 | True | `019e0677-bbd9-7621-a2ff-353e5943d1ee` |  |
| `openrouter` | `parse_engine:jina_reader` | `jina_reader` | 0.6467 | True | `019e0677-c80e-72a0-ba5f-b986e7e96a57` |  |
| `openrouter` | `parse_engine:llama_parse` | `llama_parse` | 0.6567 | True | `019e0677-d3da-7023-9efd-e55ee7e74c0f` |  |
| `openrouter` | `parse_engine:markitdown` | `markitdown` | 0.6567 | True | `019e0677-e5ce-7800-88db-50607a83bc8d` |  |

## Evaluation Cases

- `openrouter` on `parse_engine:auto`: Compare the main macroeconomic, inflation, monetary policy, and financial stability risks across these sources. Cite source names.
- `openrouter` on `parse_engine:crawl4ai`: Compare the main macroeconomic, inflation, monetary policy, and financial stability risks across these sources. Cite source names.
- `openrouter` on `parse_engine:jina_reader`: Compare the main macroeconomic, inflation, monetary policy, and financial stability risks across these sources. Cite source names.

## Artifacts

- Eval dataset JSONL: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260508_072139_200db47d\tensorzero_eval_dataset.jsonl`
- Knowledge graph HTML: `not generated`
- JSON report: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260508_072139_200db47d\report.json`
