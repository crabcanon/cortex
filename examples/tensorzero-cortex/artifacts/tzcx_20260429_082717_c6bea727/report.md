# TensorZero Cortex Experiment Report

- Run ID: `tzcx_20260429_082717_c6bea727`
- Dataset: `tensorzero_cortex_tzcx_20260429_082717_c6bea727`
- TensorZero Gateway: http://127.0.0.1:3002
- TensorZero UI: http://127.0.0.1:4000

## Scorecard

- `parse_markdown_quality`: 0.1454
- `rag_context_quality`: 0.718
- `llm_answer_quality`: 0.45
- `rag_end_to_end_pass_rate`: 0.0
- `rag_end_to_end_pass`: False
- `tensorzero_strategy`: exhaustive
- `tensorzero_variants_requested`: ['openai', 'gemini']
- `tensorzero_variant_counts`: {'openai': 2, 'gemini': 2}
- `tensorzero_inference_count`: 4
- `tensorzero_error_count`: 0
- `parse_success_count`: 2
- `parse_failure_count`: 0
- `parse_by_engine`: {'markitdown': {'success': 1, 'failure': 0, 'avg_score': 0.1454, 'markdown_chars': 86}, 'docling': {'success': 1, 'failure': 0, 'avg_score': 0.1453, 'markdown_chars': 83}}
- `context_group_count`: 2
- `context_source`: parse_artifact_fallback
- `knowledge_status`: skipped
- `cortex_eval_mode`: sync
- `cortex_eval_types`: ['rag', 'custom']

## Parse Artifacts

| URL | Engine | Mode | Markdown chars | Parse score | Object ID | Error |
| --- | --- | --- | ---: | ---: | --- | --- |
| Federal Reserve FOMC calendar | `markitdown` | `sync` | 86 | 0.145 | obj_Federal- |  |
| Federal Reserve FOMC calendar | `docling` | `async` | 83 | 0.145 | obj_Federal- |  |

## Context Groups

| Context | Source | Parse Engine | Chars | Context score |
| --- | --- | --- | ---: | ---: |
| `parse_engine:docling` | parse_artifact | `docling` | 237 | 0.718 |
| `parse_engine:markitdown` | parse_artifact | `markitdown` | 243 | 0.718 |

## TensorZero Inferences

| Variant | Context | Parse Engine | Answer score | E2E pass | Inference ID | Error |
| --- | --- | --- | ---: | --- | --- | --- |
| `openai` | `parse_engine:docling` | `docling` | 0.45 | False | `inf_openai_parse_engine:docling` |  |
| `gemini` | `parse_engine:docling` | `docling` | 0.45 | False | `inf_gemini_parse_engine:docling` |  |
| `openai` | `parse_engine:markitdown` | `markitdown` | 0.45 | False | `inf_openai_parse_engine:markitdown` |  |
| `gemini` | `parse_engine:markitdown` | `markitdown` | 0.45 | False | `inf_gemini_parse_engine:markitdown` |  |

## Evaluation Cases

- `openai` on `parse_engine:docling`: What risks matter?
- `gemini` on `parse_engine:docling`: What risks matter?
- `openai` on `parse_engine:markitdown`: What risks matter?
- `gemini` on `parse_engine:markitdown`: What risks matter?

## Artifacts

- Eval dataset JSONL: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260429_082717_c6bea727\tensorzero_eval_dataset.jsonl`
- JSON report: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260429_082717_c6bea727\report.json`
