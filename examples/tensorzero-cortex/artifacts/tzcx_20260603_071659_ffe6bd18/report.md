# TensorZero Cortex Experiment Report

- Run ID: `tzcx_20260603_071659_ffe6bd18`
- Dataset: `tensorzero_cortex_tzcx_20260603_071659_ffe6bd18`
- TensorZero Gateway: http://127.0.0.1:3002
- TensorZero UI: http://127.0.0.1:4000

## Scorecard

- `parse_markdown_quality`: 0.6197
- `rag_context_quality`: 0.4885
- `llm_answer_quality`: 0.4125
- `rag_end_to_end_pass_rate`: 0.2
- `rag_end_to_end_pass`: False
- `tensorzero_strategy`: exhaustive
- `tensorzero_variants_requested`: ['openrouter']
- `tensorzero_variant_counts`: {'openrouter': 5}
- `tensorzero_inference_count`: 5
- `tensorzero_error_count`: 0
- `parse_success_count`: 31
- `parse_failure_count`: 29
- `parse_by_engine`: {'auto': {'success': 6, 'failure': 4, 'avg_score': 0.7603, 'markdown_chars': 912936}, 'crawl4ai': {'success': 4, 'failure': 6, 'avg_score': 0.6084, 'markdown_chars': 205103}, 'markitdown': {'success': 4, 'failure': 6, 'avg_score': 0.9354, 'markdown_chars': 238441}, 'llama_parse': {'success': 7, 'failure': 3, 'avg_score': 0.8412, 'markdown_chars': 1864205}, 'jina_reader': {'success': 6, 'failure': 4, 'avg_score': 0.4308, 'markdown_chars': 12797}, 'docling': {'success': 4, 'failure': 6, 'avg_score': 0.0, 'markdown_chars': 0}}
- `context_group_count`: 5
- `context_source`: parse_artifact_fallback
- `knowledge_status`: built
- `cortex_eval_mode`: async
- `cortex_eval_types`: ['llm', 'rag', 'custom']

## Parse Artifacts

| URL | Engine | Mode | Markdown chars | Parse score | Object ID | Error |
| --- | --- | --- | ---: | ---: | --- | --- |
| Federal Reserve FOMC calendar | `auto` | `sync` | 78224 | 1.000 | obj_9abcce23ba2946c29d0fc03a |  |
| Federal Reserve FOMC calendar | `crawl4ai` | `sync` | 78224 | 1.000 | obj_1749a9446c1447f6bba31cc1 |  |
| Federal Reserve FOMC calendar | `markitdown` | `sync` | 43151 | 1.000 | obj_e23e6a9737d1443b8ce88ac7 |  |
| Federal Reserve FOMC calendar | `llama_parse` | `sync` | 13218 | 1.000 | obj_7bc36d8ad02c41bca98f8d51 |  |
| Federal Reserve FOMC calendar | `jina_reader` | `sync` | 2941 | 0.512 | obj_5e9fb880afb7484fa484ac74 |  |
| Federal Reserve FOMC calendar | `docling` | `async` | 0 | 0.000 | obj_8e1bac6f06da435f892a0d3c |  |
| Federal Reserve Financial Stability Report PDF | `auto` | `sync` | 177811 | 1.000 | obj_4d23fbcfcf8c43a2892b8117 |  |
| Federal Reserve Financial Stability Report PDF | `crawl4ai` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 422: No active parse engine can handle the requested source. |
| Federal Reserve Financial Stability Report PDF | `markitdown` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: markitdown:engine_execution_failed (File conversion failed after 1 attempts:  - PdfConv |
| Federal Reserve Financial Stability Report PDF | `llama_parse` | `sync` | 177811 | 1.000 | obj_774930eb5a8a4859aed2262a |  |
| Federal Reserve Financial Stability Report PDF | `jina_reader` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: jina_reader:engine_execution_failed (Client error '422 Unprocessable Entity' for url 'h |
| Federal Reserve Financial Stability Report PDF | `docling` | `async` | 0 | 0.000 |  | Job job_60f6b88c3089413699aacf8a ended as failed: {'job_id': 'job_60f6b88c3089413699aacf8a', 'job_type': 'parse', 'status': 'failed', 'operation_name': 'parse.document.async', 'sub |
| IMF data API GDP growth | `auto` | `sync` | 121731 | 0.750 | obj_43cdbfcb24054527886f08af |  |
| IMF data API GDP growth | `crawl4ai` | `sync` | 121731 | 0.750 | obj_9afa1262c68845b39b426dfd |  |
| IMF data API GDP growth | `markitdown` | `sync` | 121723 | 0.750 | obj_9cb1b52192a4426cae5baba4 |  |
| IMF data API GDP growth | `llama_parse` | `sync` | 129891 | 0.867 | obj_664562f9e619413e84d97ae8 |  |
| IMF data API GDP growth | `jina_reader` | `sync` | 1045 | 0.312 | obj_08ea6a914b154a1c96968ff0 |  |
| IMF data API GDP growth | `docling` | `async` | 0 | 0.000 |  | Job job_8de66235e9d540e7aa1aef50 ended as failed: {'job_id': 'job_8de66235e9d540e7aa1aef50', 'job_type': 'parse', 'status': 'failed', 'operation_name': 'parse.document.async', 'sub |
| World Bank Global Economic Prospects | `auto` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: crawl4ai:crawl4ai_failed (crawl4ai_failed: Blocked by anti-bot protection: Structural:  |
| World Bank Global Economic Prospects | `crawl4ai` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: crawl4ai:crawl4ai_failed (crawl4ai_failed: Blocked by anti-bot protection: Structural:  |
| World Bank Global Economic Prospects | `markitdown` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: markitdown:engine_execution_failed (File conversion failed after 3 attempts:  - PdfConv |
| World Bank Global Economic Prospects | `llama_parse` | `sync` | 1011522 | 1.000 | obj_14d5ad02185947279846a036 |  |
| World Bank Global Economic Prospects | `jina_reader` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: jina_reader:engine_execution_failed (Client error '422 Unprocessable Entity' for url 'h |
| World Bank Global Economic Prospects | `docling` | `async` | 0 | 0.000 |  | Cortex API is unreachable at http://127.0.0.1:8080 while calling GET /v1/jobs/job_39080f6b10a04c4faa5b4f5d: Server disconnected without sending a response.. Start Cortex API or set |
| BIS Annual Economic Report PDF | `auto` | `sync` | 528988 | 1.000 | obj_8edeee4eca3e47caaaf5d9ba |  |
| BIS Annual Economic Report PDF | `crawl4ai` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 422: No active parse engine can handle the requested source. |
| BIS Annual Economic Report PDF | `markitdown` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: markitdown:engine_execution_failed (File conversion failed after 1 attempts:  - PdfConv |
| BIS Annual Economic Report PDF | `llama_parse` | `sync` | 528988 | 1.000 | obj_976d0a864fcf4500bf900110 |  |
| BIS Annual Economic Report PDF | `jina_reader` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: jina_reader:engine_execution_failed (Client error '422 Unprocessable Entity' for url 'h |
| BIS Annual Economic Report PDF | `docling` | `async` | 0 | 0.000 |  | Job job_f4a8da93e45249719b51e9d4 ended as failed: {'job_id': 'job_f4a8da93e45249719b51e9d4', 'job_type': 'parse', 'status': 'failed', 'operation_name': 'parse.document.async', 'sub |
| OECD Economic Outlook | `auto` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: crawl4ai:crawl4ai_failed (crawl4ai_failed: Blocked by anti-bot protection: Cloudflare J |
| OECD Economic Outlook | `crawl4ai` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: crawl4ai:crawl4ai_failed (crawl4ai_failed: Blocked by anti-bot protection: Cloudflare J |
| OECD Economic Outlook | `markitdown` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: markitdown:engine_execution_failed (403 Client Error: Forbidden for url: https://www.oe |
| OECD Economic Outlook | `llama_parse` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: llama_parse:config_error (config_error: LlamaParse completed without returning document |
| OECD Economic Outlook | `jina_reader` | `sync` | 361 | 0.174 | obj_91977f17352740c88dcaeb54 |  |
| OECD Economic Outlook | `docling` | `async` | 0 | 0.000 |  | Job job_848c21d67cb74c1b8d6b3347 ended as failed: {'job_id': 'job_848c21d67cb74c1b8d6b3347', 'job_type': 'parse', 'status': 'failed', 'operation_name': 'parse.document.async', 'sub |
| US Treasury press releases | `auto` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: crawl4ai:crawl4ai_failed (crawl4ai_failed: Blocked by anti-bot protection: Structural:  |
| US Treasury press releases | `crawl4ai` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: crawl4ai:crawl4ai_failed (crawl4ai_failed: Blocked by anti-bot protection: Structural:  |
| US Treasury press releases | `markitdown` | `sync` | 31231 | 1.000 | obj_a2a4c8748a7244d4848284c5 |  |
| US Treasury press releases | `llama_parse` | `sync` | 1373 | 0.660 | obj_7274df7049004c97a7302c5e |  |
| US Treasury press releases | `jina_reader` | `sync` | 1851 | 0.731 | obj_94f842b9fa6c4d0eb8ee0108 |  |
| US Treasury press releases | `docling` | `async` | 0 | 0.000 | obj_5e05a7f63f0f439d896ad9f5 |  |
| SEC 10-K form PDF | `auto` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: llama_parse:config_error (config_error: LlamaParse completed without returning document |
| SEC 10-K form PDF | `crawl4ai` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 422: No active parse engine can handle the requested source. |
| SEC 10-K form PDF | `markitdown` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: markitdown:engine_execution_failed (403 Client Error: Forbidden for url: https://www.se |
| SEC 10-K form PDF | `llama_parse` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: llama_parse:config_error (config_error: LlamaParse completed without returning document |
| SEC 10-K form PDF | `jina_reader` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: jina_reader:engine_execution_failed (Client error '422 Unprocessable Entity' for url 'h |
| SEC 10-K form PDF | `docling` | `async` | 0 | 0.000 | obj_aef74ccc1cdf485c84899826 |  |
| ECB monetary policy decisions | `auto` | `sync` | 2884 | 0.418 | obj_bb4c4fcef67e4942be5cbd35 |  |
| ECB monetary policy decisions | `crawl4ai` | `sync` | 2884 | 0.418 | obj_5ab2e56499164d8aa10ab791 |  |
| ECB monetary policy decisions | `markitdown` | `sync` | 42336 | 0.992 | obj_8b59925739164dfea4be481e |  |
| ECB monetary policy decisions | `llama_parse` | `sync` | 1402 | 0.361 | obj_c02f1df03f9744f9952b3868 |  |
| ECB monetary policy decisions | `jina_reader` | `sync` | 2709 | 0.435 | obj_493cc5846cc346c3aba52aba |  |
| ECB monetary policy decisions | `docling` | `async` | 0 | 0.000 | obj_66c0188205f14615ba4f76e5 |  |
| Bank of England Monetary Policy Report | `auto` | `sync` | 3298 | 0.394 | obj_58ae08bfde6740d88a304d0c |  |
| Bank of England Monetary Policy Report | `crawl4ai` | `sync` | 2264 | 0.266 | obj_42d2122ab7e042ad90a8df30 |  |
| Bank of England Monetary Policy Report | `markitdown` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: markitdown:engine_execution_failed (HTTPSConnectionPool(host='www.bankofengland.co.uk', |
| Bank of England Monetary Policy Report | `llama_parse` | `sync` | 0 | 0.000 |  | POST /v1/parse/sync failed with 502: No parse engine produced a successful result. Attempts: llama_parse:config_error (config_error: LlamaParse completed without returning document |
| Bank of England Monetary Policy Report | `jina_reader` | `sync` | 3890 | 0.420 | obj_fc2b0ddd38734cd4abe9f60b |  |
| Bank of England Monetary Policy Report | `docling` | `async` | 0 | 0.000 |  | Job job_a27cb5a654a44824bc31c5e3 ended as failed: {'job_id': 'job_a27cb5a654a44824bc31c5e3', 'job_type': 'parse', 'status': 'failed', 'operation_name': 'parse.document.async', 'sub |

## Context Groups

| Context | Source | Parse Engine | Chars | Context score |
| --- | --- | --- | ---: | ---: |
| `parse_engine:auto` | parse_artifact | `auto` | 6000 | 0.488 |
| `parse_engine:crawl4ai` | parse_artifact | `crawl4ai` | 6000 | 0.488 |
| `parse_engine:jina_reader` | parse_artifact | `jina_reader` | 6000 | 0.596 |
| `parse_engine:llama_parse` | parse_artifact | `llama_parse` | 6000 | 0.408 |
| `parse_engine:markitdown` | parse_artifact | `markitdown` | 6000 | 0.462 |

## TensorZero Inferences

| Variant | Context | Parse Engine | Answer score | E2E pass | Inference ID | Error |
| --- | --- | --- | ---: | --- | --- | --- |
| `openrouter` | `parse_engine:auto` | `auto` | 0.4169 | False | `019e8c75-b556-7ae1-8eda-462e5c229e1c` |  |
| `openrouter` | `parse_engine:crawl4ai` | `crawl4ai` | 0.3958 | False | `019e8c75-c684-7b91-8529-05366cc77110` |  |
| `openrouter` | `parse_engine:jina_reader` | `jina_reader` | 0.4592 | True | `019e8c75-da14-7d01-ba22-21844d8d80cd` |  |
| `openrouter` | `parse_engine:llama_parse` | `llama_parse` | 0.3735 | False | `019e8c75-e98a-74a3-a566-d8fd97c5773e` |  |
| `openrouter` | `parse_engine:markitdown` | `markitdown` | 0.4169 | False | `019e8c75-f566-7d30-8a34-97e1a4e0a765` |  |

## Evaluation Cases

- `openrouter` on `parse_engine:auto`: Compare the main macroeconomic, inflation, monetary policy, and financial stability risks across these sources. Cite source names.
- `openrouter` on `parse_engine:crawl4ai`: Compare the main macroeconomic, inflation, monetary policy, and financial stability risks across these sources. Cite source names.
- `openrouter` on `parse_engine:jina_reader`: Compare the main macroeconomic, inflation, monetary policy, and financial stability risks across these sources. Cite source names.

## Artifacts

- Eval dataset JSONL: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260603_071659_ffe6bd18\tensorzero_eval_dataset.jsonl`
- Knowledge graph HTML: `not generated`
- JSON report: `D:\code\codex\cortex\examples\tensorzero-cortex\artifacts\tzcx_20260603_071659_ffe6bd18\report.json`
