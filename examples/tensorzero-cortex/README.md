# TensorZero + Cortex 矩阵评测与自适应 A/B Test 样例

这个样例演示一个接近真实业务的金融研究流水线：

1. 用 Cortex Parse API 对 20 个金融 / 宏观经济 URL 做多引擎解析。
2. 将不同 parse engine 产出的 Markdown 写入 Cortex Storage。
3. 将 Markdown 对象加载进 Cortex Knowledge，执行 Add + Cognify。
4. 对用户自然语言 query 执行 Knowledge Search，形成 RAG context。
5. 通过 TensorZero Gateway 在 OpenAI / Gemini / Kimi 等模型服务之间做 exhaustive 矩阵对比或 adaptive A/B test。
6. 将 TensorZero 采集到的 inference / feedback 数据沉淀为评测集，并通过 Cortex Evaluation 输出 parse、RAG、LLM、agentic、端到端效果报告。

## 技术栈

- Python 3.12
- uv
- FastAPI
- httpx
- TensorZero Gateway / UI
- Cortex API，本样例假设 Cortex Docker 集群已经在 `http://127.0.0.1:8080` 启动

TensorZero 参考官方文档中的 adaptive A/B test 模型：定义 function、candidate variants、优化 metric，然后对每次 inference 写入 feedback，TensorZero 会持续调整候选 variant 权重。本样例同时支持 `exhaustive` 模式，显式 pin 住每个 TensorZero variant，避免小样本实验中所有请求都被 adaptive 抽样到同一个模型。

## 目录结构

```text
examples/tensorzero-cortex/
  pyproject.toml
  .env.example
  README.md
  artifacts/
  tensorzero/
    docker-compose.tensorzero.yaml
    tensorzero.toml.tpl
    templates/rag_system.minijinja
    schemas/rag_answer.schema.json
  src/
    cli.py
    main.py
    pipeline.py
    cortex_client.py
    tensorzero_client.py
    finance_urls.py
```

## 1. 准备配置

```powershell
cd examples\tensorzero-cortex
Copy-Item .env.example .env
```

编辑 `.env`，至少填入你要测试的模型供应商密钥：

```text
OPENAI_API_KEY=...
GEMINI_API_KEY=...
KIMI_API_KEY=...
OPENROUTER_API_KEY=...
OLLAMA_API_KEY=ollama
```

如果你只想先测一个供应商，可以先只填对应 key，并在 `.env` 中把候选模型改成可用模型。TensorZero 的最终配置由 `tensorzero/tensorzero.toml.tpl` 加 `.env` 渲染而来，`src/render_tensorzero_config.py` 不再保留任何内置默认值；模板中出现的每个变量都必须在 `.env` 或你通过 `--env-file` 指定的文件中填写。

Parse 默认走同步模式。需要生产型长任务链路时，把 `.env` 中的 `PARSE_MODE` 改为 `async`，或在命令行传入 `--parse-mode async`。Docling 属于重型 worker-only 引擎，样例默认会把 `docling` 覆盖为 async，即使全局 `PARSE_MODE=sync` 也会提交 `/v1/parse/jobs`，让 `cortex-parse-worker-docling` 消费任务。

Cortex Evaluation 默认也走同步模式。需要验证 worker-backed 评测链路时，把 `.env` 中的 `CORTEX_EVAL_MODE` 改为 `async`。如果希望每次运行都提交 Cortex Evaluation，把 `SUBMIT_CORTEX_EVAL` 改为 `true`。Cortex 本地 runtime 默认将 DeepEval / DeepEval Synthesizer 的 judge model 绑定到 `KIMI_*` 槽位；如果你刚从 Gemini 切换过来，确认仓库根目录 `.env` 已填写 `KIMI_BASE_URL`、`KIMI_API_KEY`、`KIMI_MODEL_ID`，并重启 `cortex-api` 与 `cortex-evaluation-worker-runtime`。DeepEval 会通过 Cortex 的 OpenAI-compatible judge wrapper 显式使用 Kimi 的 `base_url` 和 `api_key`，不再依赖 DeepEval 对模型字符串的隐式供应商路由。

如果 Cortex Evaluation 也切到本地 Ollama，建议先使用轻量冒烟评测，避免 DeepEval 多指标、多 case 把本地 judge 模型压到超时：

```text
SUBMIT_CORTEX_EVAL=true
CORTEX_EVAL_MODE=async
CORTEX_EVAL_TYPES=rag
CORTEX_EVAL_METRIC_PROFILE=deepeval_local_smoke
CORTEX_EVAL_MAX_CASES=1
CORTEX_EVAL_MAX_CONTEXT_CHARS_PER_CASE=2000
CORTEX_EVAL_ASYNC_TIMEOUT_SECONDS=3600
```

`deepeval_local_smoke` 只提交一个 RAG 核心指标和少量 case，用来确认链路可用。确认稳定后，再逐步切回 `deepeval_rag_core`、增加 `CORTEX_EVAL_MAX_CASES`，或增加 `CORTEX_EVAL_TYPES=rag,custom`。

Knowledge 的 Cognee LLM 和 embedding 在本地默认使用 `OPENROUTER_*`。OpenRouter 的 OpenAI-compatible base URL 是 `https://openrouter.ai/api/v1`，并支持 `/embeddings`。推荐在仓库根目录 `.env` 中配置：

```text
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=...
OPENROUTER_MODEL_ID=openrouter/auto
OPENROUTER_EMBEDDING_MODEL_ID=openai/text-embedding-3-small
OPENROUTER_EMBEDDING_DIMENSIONS=1536
```

如果把 embedding 切到 OpenRouter 的 BGE-M3，请同步把维度改成模型实际维度，例如：

```text
OPENROUTER_EMBEDDING_MODEL_ID=baai/bge-m3
OPENROUTER_EMBEDDING_DIMENSIONS=1024
```

Cognee 的 OpenAI/LiteLLM embedding 路径会用 tiktoken 做 chunk token 估算，而 `baai/bge-m3` 不是 tiktoken 内置模型名。Cortex 已在 Knowledge runtime 中加了兜底：遇到这类 OpenAI-compatible 非 OpenAI embedding 模型时，token 估算退回 `cl100k_base`；实际 `/embeddings` 请求会按 provider alias 自动路由为 LiteLLM 的 `openrouter/baai/bge-m3`。

更通用地说，Knowledge 的 embedding 服务与 tokenizer 估算策略已经解耦。你可以在仓库根目录 `configs/cortex.runtime.local.yaml` 的 `knowledge.cognee.embedding.tokenizer` 下切换策略：

```yaml
tokenizer:
  # auto: 先让 Cognee 按 provider/model 自己选择；失败后走 fallback_strategy
  # tiktoken: 固定使用指定 tiktoken encoding
  # huggingface: 使用 HuggingFace tokenizer，model 可写 BAAI/bge-m3 等
  # approximate / none: 不依赖 tokenizer 包，按词数做保守估算
  strategy: auto
  encoding: cl100k_base
  fallback_strategy: tiktoken
```

如果你希望 BGE-M3 token 估算也贴近原模型，可以改成：

```yaml
tokenizer:
  strategy: huggingface
  model: BAAI/bge-m3
  fallback_strategy: tiktoken
```

这只影响本地 chunk/token 估算，不会改变发给 OpenRouter 的 embedding 模型 ID。

如果日志里出现 `litellm.RateLimitError: OpenAIException`，说明 Knowledge 仍在打 OpenAI 默认通道，请确认 `configs/cortex.runtime.local.yaml` 已把 Cognee LLM 与 embedding 指向 `OPENROUTER_*`，并重建/重启 `cortex-knowledge-worker`。Cortex 会把 `openrouter` provider alias 映射为 OpenAI-compatible SDK 调用，并把 OpenRouter 槽位写入 `OPENAI_BASE_URL` / `LITELLM_API_BASE` 等 Cognee/LiteLLM 会读取的环境变量。如果 OpenRouter 在宿主机可访问但 Docker 容器内连接失败，请在 `.env` 里配置 `HTTPS_PROXY` / `HTTP_PROXY` / `ALL_PROXY`，本样例和 Cortex Compose 都会透传这些代理变量。本地 Docker Desktop 使用宿主机代理时建议写成 `http://host.docker.internal:7890`，Cortex 本地 Compose 会把 `host.docker.internal` 映射到宿主机网关。

如果想把 Cortex Knowledge / Evaluation / Synthesis 全部切到本机 Ollama，在仓库根目录 `.env` 中配置：

```text
OLLAMA_BASE_URL=http://host.docker.internal:11434/v1
OLLAMA_API_KEY=ollama
OLLAMA_MODEL_ID=llama3.1:8b
OLLAMA_EMBEDDING_MODEL_ID=nomic-embed-text
OLLAMA_EMBEDDING_DIMENSIONS=768
CORTEX_RUNTIME_CONFIG_PATH=configs/cortex.runtime.ollama.yaml
```

宿主机先执行 `ollama pull llama3.1:8b` 与 `ollama pull nomic-embed-text`。如果想让 TensorZero 矩阵或 adaptive A/B test 额外比较 Ollama LLM，在本样例 `.env` 里设置 `TENSORZERO_VARIANTS=openai,gemini,kimi,ollama`，并重新渲染 TensorZero 配置。

修改 `TENSORZERO_VARIANTS` 或 `tensorzero/tensorzero.toml.tpl` 后，必须重新渲染并重启 Gateway；TensorZero Gateway 只在启动时读取 `/app/config/tensorzero.toml`：

```powershell
uv run tensorzero-cortex render-config
docker compose --env-file .env -f tensorzero\docker-compose.tensorzero.yaml up -d --force-recreate gateway ui
```

如果报告里出现 `Unknown variant: ollama`，说明运行中的 Gateway 仍在使用旧版 `tensorzero.toml`。先确认生成文件里已经存在 `[functions.cortex_rag_answer.variants.ollama]`，再重启 Gateway：

```powershell
Select-String -Path tensorzero\tensorzero.toml -Pattern "variants.ollama"
```

如果 `ollama` variant 显示 `timed out`，通常是本地模型冷启动、上下文过长或 Gateway 容器无法访问 Ollama。先用最小请求确认宿主机 Ollama 正常：

```powershell
$body = @{
  model = $env:OLLAMA_MODEL_ID
  messages = @(@{ role = "user"; content = "Say ok." })
  stream = $false
  max_tokens = 32
} | ConvertTo-Json -Depth 8

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:11434/v1/chat/completions" `
  -ContentType "application/json" `
  -Body $body `
  -TimeoutSec 300
```

再确认 TensorZero Gateway 容器能访问宿主机 Ollama：

```powershell
docker exec tensorzero-gateway-1 wget -qO- http://host.docker.internal:11434/api/tags
```

本地 Ollama 推荐先把上下文和输出 token 调小，再逐步放大：

```text
TENSORZERO_VARIANTS=ollama
TENSORZERO_MAX_CONTEXT_CHARS_PER_GROUP=3000
TENSORZERO_OLLAMA_MAX_TOKENS=512
REQUEST_TIMEOUT_SECONDS=600
```

修改后重新渲染并重启 Gateway：

```powershell
uv run tensorzero-cortex render-config
docker compose --env-file .env -f tensorzero\docker-compose.tensorzero.yaml up -d --force-recreate gateway ui
```

矩阵实验相关的推荐配置：

```text
PARSE_ENGINES=auto,crawl4ai,jina_reader,markitdown,llama_parse,docling
TENSORZERO_STRATEGY=exhaustive
TENSORZERO_VARIANTS=openai,gemini,kimi
TENSORZERO_CONTEXT_GROUPING=by_parse_engine
SUBMIT_CORTEX_EVAL=true
CORTEX_EVAL_MODE=async
CORTEX_EVAL_TYPES=rag
CORTEX_EVAL_METRIC_PROFILE=deepeval_local_smoke
CORTEX_EVAL_MAX_CASES=1
CORTEX_EVAL_MAX_CONTEXT_CHARS_PER_CASE=2000
CORTEX_EVAL_ASYNC_TIMEOUT_SECONDS=3600
KNOWLEDGE_GRAPH_VISUALIZATION=true
CORTEX_KNOWLEDGE_WORKER_CONTAINER=cortex-local-cortex-knowledge-worker-1
```

`TENSORZERO_STRATEGY` 可选值：

- `exhaustive`: 每个 context group 都显式请求 OpenAI / Gemini / Kimi 等 variant，适合离线评测。
- `adaptive`: 不传 `variant_name`，由 TensorZero Gateway 自动抽样并根据 feedback 优化权重，适合线上流量。
- `selected`: 只跑第一个 variant，适合快速 smoke test。

`TENSORZERO_CONTEXT_GROUPING` 可选值：

- `by_parse_engine`: 按 parse engine 聚合上下文，适合比较不同解析器对 RAG 的影响。
- `combined`: 将 Knowledge Search 或 fallback context 合并为一个上下文。
- `knowledge_or_parse`: Knowledge 可用时使用 Knowledge Search，不可用时退回 parse artifacts。

## 2. 渲染 TensorZero 配置

TensorZero 的 gateway 启动前需要静态 `tensorzero.toml`。本样例用 `.env` 中的模型槽位渲染模板：

```powershell
uv run tensorzero-cortex render-config
```

也可以显式指定配置文件，便于 CI 或本地多套模型配置切换：

```powershell
uv run tensorzero-cortex render-config --env-file .env.openrouter
```

会生成：

```text
tensorzero/tensorzero.toml
```

## 3. 启动 TensorZero

Cortex 主服务请先在仓库根目录按你的方式启动，例如：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 up -Build -Heavy
```

如果只是修改 `configs/cortex.runtime.local.yaml` 这类运行时配置，不需要重新构建重型镜像。当前本地 Compose 会把仓库里的 `./configs` 挂载到容器内 `/app/configs`，所以更新配置后只要重启相关 Cortex 容器即可：

```powershell
cd D:\code\codex\cortex

docker compose --env-file .env -f compose.local.yaml `
  --profile docling `
  --profile eval-runtime `
  --profile synthesis-runtime `
  up -d --no-build --force-recreate `
  cortex-api `
  cortex-knowledge-worker `
  cortex-evaluation-worker-runtime `
  cortex-synthesis-worker-runtime
```

如果你没有启用某个 profile，可以把对应 worker 从命令里删掉。已经失败的旧 Evaluation job 不会自动重跑，需要重新触发 example 或重新提交评测任务。

如果改动包含 Python 代码，例如 Evaluation 的 DeepEval judge wrapper、worker lease/heartbeat 逻辑或依赖，则必须重建相关镜像。只修 Evaluation runtime 时可以只重建目标服务，避免重建全部重型镜像：

```powershell
cd D:\code\codex\cortex

docker compose --env-file .env -f compose.local.yaml `
  --profile eval-runtime `
  up -d --build --force-recreate `
  cortex-api `
  cortex-knowledge-worker `
  cortex-evaluation-worker-runtime
```

如果报告中出现 `evaluation_worker_lease_expired`，优先确认 Cortex 容器已使用新版 worker 代码，并在仓库根目录 `.env` 中保留下面的默认值：

```text
CORTEX_EVALUATION_WORKER_LEASE_SECONDS=300
CORTEX_EVALUATION_WORKER_HEARTBEAT_INTERVAL_SECONDS=30
CORTEX_KNOWLEDGE_WORKER_LEASE_SECONDS=300
CORTEX_KNOWLEDGE_WORKER_HEARTBEAT_INTERVAL_SECONDS=30
```

如果报告中出现 `deepeval_provider_connection_failed` 或 `Connection error.`，说明 Evaluation runtime 容器内无法访问所选模型供应商。用下面命令验证容器内看到的配置和网络连通性，命令不会打印 API key：

```powershell
cd D:\code\codex\cortex

docker compose --env-file .env -f compose.local.yaml --profile eval-runtime `
  exec cortex-evaluation-worker-runtime `
  /app/.venv/bin/python -c "import os; print({'KIMI_BASE_URL': os.getenv('KIMI_BASE_URL'), 'KIMI_MODEL_ID': os.getenv('KIMI_MODEL_ID'), 'HTTPS_PROXY': os.getenv('HTTPS_PROXY'), 'HTTP_PROXY': os.getenv('HTTP_PROXY'), 'ALL_PROXY': os.getenv('ALL_PROXY'), 'NO_PROXY': os.getenv('NO_PROXY'), 'KIMI_API_KEY_PRESENT': bool(os.getenv('KIMI_API_KEY'))})"

docker compose --env-file .env -f compose.local.yaml --profile eval-runtime `
  exec cortex-evaluation-worker-runtime `
  /app/.venv/bin/python -c "import os, httpx; base=os.getenv('KIMI_BASE_URL','').rstrip('/'); url=f'{base}/models'; print('GET', url); r=httpx.get(url, headers={'Authorization':'Bearer '+os.getenv('KIMI_API_KEY','')}, timeout=20); print(r.status_code, r.text[:300])"
```

然后在本目录启动 TensorZero：

```powershell
docker compose --env-file .env -f tensorzero\docker-compose.tensorzero.yaml up -d
```

TensorZero adaptive A/B test 依赖 Postgres 的 `pg_cron` 扩展。Cortex 本地栈的 `postgres:16` 默认不包含该扩展，所以 TensorZero 样例会启动一个专用的 `tensorzero/postgres:17`，并把宿主端口放到 `5434`，避免和 Cortex 的 `5432` 冲突。TensorZero Gateway 的容器内端口仍是 `3000`，但宿主机端口默认映射到 `3002`，避免和 Cortex 本地 Grafana 的 `3000` 冲突：

```text
TENSORZERO_GATEWAY_HOST_PORT=3002
TENSORZERO_GATEWAY_URL=http://127.0.0.1:3002
TENSORZERO_READY_TIMEOUT_SECONDS=180
TENSORZERO_POSTGRES_IMAGE_TAG=17
TENSORZERO_POSTGRES_HOST_PORT=5434
TENSORZERO_POSTGRES_USER=postgres
TENSORZERO_POSTGRES_PASSWORD=postgres
TENSORZERO_POSTGRES_DB=tensorzero
TENSORZERO_POSTGRES_URL=postgres://postgres:postgres@postgres:5432/tensorzero
```

如果 TensorZero 的容器或 volume 已经存在，直接执行上面的 `docker compose up -d` 即可，Compose 会复用现有实例和数据卷。如果上一次失败停在 migration，建议先清理失败容器和旧版 orphan 容器，再启动；不要加 `-v`，这样会保留 ClickHouse / Postgres 数据卷：

```powershell
docker compose --env-file .env -f tensorzero\docker-compose.tensorzero.yaml down --remove-orphans
docker compose --env-file .env -f tensorzero\docker-compose.tensorzero.yaml up -d --remove-orphans
```

入口：

| 服务 | 地址 |
| --- | --- |
| Cortex Swagger | http://127.0.0.1:8080/docs |
| TensorZero Gateway | http://127.0.0.1:3002 |
| TensorZero UI | http://127.0.0.1:4000 |

Gateway 容器刚启动后，`/status` 可能短暂返回 `502`，通常是依赖服务还在完成初始化。样例应用会自动重试 readiness；你也可以手动确认：

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:3002/status
```

如果你通过 FastAPI example 调用，也可以用同一套 `.env` 配置检查：

```text
GET http://127.0.0.1:8090/tensorzero/status
```

这个诊断接口会返回它实际使用的 `gateway_url`。如果这里仍然显示 `http://127.0.0.1:3000`，说明 FastAPI 进程没有重启或 shell 中旧环境变量覆盖了 `.env`。

样例内置的 Cortex / TensorZero HTTP client 会禁用系统代理环境变量，避免本地 `127.0.0.1` 请求被 `HTTP_PROXY` / `HTTPS_PROXY` 转发到代理后返回 502。

## 4. 运行一次实验

建议先用少量 URL 冒烟：

```powershell
uv run tensorzero-cortex run --max-urls 1 --parse-engines markitdown --skip-knowledge-jobs
```

这个最小冒烟只依赖 Cortex Parse / Storage、TensorZero Gateway 和模型供应商，不要求 Cortex API 进程内安装 Cognee runtime。样例会用解析后的 Markdown 片段作为 RAG context fallback。

默认使用 Cortex 同步解析接口 `/v1/parse/sync`。如果你要测试异步 job 链路，可以切到 `/v1/parse/jobs`，样例会等待 job 成功后再访问 `/v1/parse/jobs/{jobId}/result`：

```powershell
uv run tensorzero-cortex run `
  --max-urls 2 `
  --parse-engines auto,crawl4ai `
  --parse-mode async
```

完整一点的本地实验：

```powershell
uv run tensorzero-cortex run `
  --max-urls 5 `
  --parse-engines auto,crawl4ai,jina_reader,markitdown,llama_parse,docling `
  --parse-mode sync `
  --tensorzero-strategy exhaustive `
  --tensorzero-variants openai,gemini,kimi `
  --context-grouping by_parse_engine `
  --submit-cortex-eval `
  --cortex-eval-mode async `
  --cortex-eval-types rag,custom `
  --query "What macroeconomic and financial stability risks are highlighted across these documents?"
```

如果 Cortex Knowledge 的 Cognee runtime 不可用，样例不会中断，会自动退回到已解析并上传的 Markdown 片段作为 RAG context，并在报告 scorecard 中标记：

```text
context_source=parse_artifact_fallback
knowledge_status=failed
```

如果你的 Cortex Evaluation runtime 已经启用 DeepEval，也可以把生成的评测集同步提交给 Cortex Eval：

```text
SUBMIT_CORTEX_EVAL=true
CORTEX_EVAL_MODE=sync
```

```powershell
uv run tensorzero-cortex run --max-urls 3
```

如果你要测试异步评测 job 链路，可以切到 `/v1/eval/jobs`。样例会先轮询 `/v1/jobs/{jobId}`，成功后再读取 `/v1/eval/jobs/{jobId}/result`：

```text
SUBMIT_CORTEX_EVAL=true
CORTEX_EVAL_MODE=async
```

```powershell
uv run tensorzero-cortex run --max-urls 3
```

如果你不想改 `.env`，仍然可以临时覆盖：

```powershell
uv run tensorzero-cortex run --max-urls 3 --submit-cortex-eval --cortex-eval-mode async
```

## 5. 启动 FastAPI 样例服务

```powershell
uv run tensorzero-cortex serve --host 127.0.0.1 --port 8090
```

访问：

- http://127.0.0.1:8090/docs
- `GET /finance-urls` 查看内置 20 个金融经济 URL
- `POST /tensorzero/render-config` 重新渲染 TensorZero 配置
- `POST /experiments/run` 触发一次实验

请求示例：

```json
{
  "query": "Compare the main macroeconomic, inflation, monetary policy, and financial stability risks across these sources. Cite source names.",
  "parse": {
    "max_urls": 3,
    "engines": ["auto", "crawl4ai", "markitdown", "llama_parse", "docling"],
    "mode": "sync",
    "engine_modes": {
      "docling": "async"
    },
    "scene": null,
    "timeout_seconds": 1200
  },
  "knowledge": {
    "enabled": true,
    "search_type": "CHUNKS",
    "top_k": 8,
    "fallback_to_parse_artifacts": true,
    "build_timeout_seconds": 1800
  },
  "tensorzero": {
    "strategy": "exhaustive",
    "variants": ["openai", "gemini", "kimi"],
    "context_grouping": "by_parse_engine",
    "max_context_chars_per_group": 12000,
    "feedback_enabled": true,
    "include_raw_response": false
  },
  "evaluation": {
    "enabled": true,
    "mode": "async",
    "engine_id": "deepeval",
    "eval_types": ["rag", "custom"],
    "metric_profile": "deepeval_rag_core",
    "persist_report_object": true
  }
}
```

Swagger 的 `/experiments/run` 已内置 `full_matrix_async`、`adaptive_smoke`、`legacy_compatible` 三个 examples，可以直接 `Try it out`。

## 6. 输出物

每次运行会在 `artifacts/{run_id}` 下生成：

| 文件 | 说明 |
| --- | --- |
| `report.md` | 人类可读实验报告 |
| `report.json` | 结构化实验报告 |
| `tensorzero_eval_dataset.jsonl` | TensorZero 采集数据形成的评测集 |
| `raw_tensorzero_result.json` | TensorZero inference 矩阵响应摘要 |
| `raw_search_result.json` | Cortex Knowledge Search 原始响应 |
| `knowledge_graph.html` | Cognee 当前知识图谱的交互式静态 HTML，可直接用浏览器打开 |
| `parse/*.json` | 每个 URL + parse engine 的解析与 storage 上传结果 |

报告中的 scorecard 包含：

- `parse_markdown_quality`: Markdown 长度、结构和金融关键词覆盖的启发式分数
- `rag_context_quality`: Knowledge Search 或 parse-engine context 对目标关键词的覆盖度
- `llm_answer_quality`: 每个 TensorZero variant 输出的关键词、引用和置信度分数
- `rag_end_to_end_pass_rate`: 矩阵中端到端通过的比例
- `parse_by_engine`: 每个 parse engine 的成功数、失败数、平均解析质量和 Markdown 字符数
- `tensorzero_variant_counts`: 每个 TensorZero variant 实际运行次数

这些指标也会通过 TensorZero `/feedback` 写回：

- `parse_markdown_quality`
- `rag_context_quality`
- `llm_answer_quality`
- `rag_end_to_end_pass`

TensorZero 会用 `rag_end_to_end_pass` 作为 adaptive A/B test 的优化 metric。

Cortex Evaluation 默认使用 DeepEval 对齐的核心指标：

- RAG: `rag.answer_relevance`、`rag.faithfulness`、`rag.contextual_precision`、`rag.contextual_recall`、`rag.contextual_relevance`
- Custom quality: `quality.correctness`、`quality.completeness`、`quality.relevance`、`custom.g_eval`
- Agentic 可按需在请求中配置 `eval_types=["agentic"]`，推荐先使用 `agent.task_completion`、`agent.goal_success`、`agent.reasoning_quality`

## 7. Cognee 知识图谱可视化

Cognee 官方提供图谱可视化能力。TensorZero Cortex 样例不会直接读取默认全局图，而是根据本次 run 的 `dataset_key` 进入 Cognee 的 dataset-scoped graph context，再把该数据集下的节点和边渲染为可交互 HTML。

当 `knowledge.enabled=true` 且 Knowledge Add/Cognify 成功时，样例会尝试通过 Docker 中的 `cortex-knowledge-worker` 运行 Cognee 可视化，并把结果写入：

```text
examples\tensorzero-cortex\artifacts\{run_id}\knowledge_graph.html
```

如果你已经跑完一次实验，也可以对现有 run 补生成图谱：

```powershell
cd D:\code\codex\cortex\examples\tensorzero-cortex

uv run tensorzero-cortex visualize-knowledge --run-id tzcx_20260429_085020_bd0c1daa
```

如果要显式指定数据集：

```powershell
uv run tensorzero-cortex visualize-knowledge `
  --run-id tzcx_20260429_085020_bd0c1daa `
  --dataset-key tensorzero_cortex_tzcx_20260429_085020_bd0c1daa
```

如果你的容器名不同：

```powershell
uv run tensorzero-cortex visualize-knowledge `
  --run-id tzcx_20260429_085020_bd0c1daa `
  --container cortex-local-cortex-knowledge-worker-1
```

如果 Knowledge runtime 没有成功构建图谱，或者当前 API 退回到了 `parse_artifact_fallback`，这个 HTML 可能无法生成；这种情况下先确认 `cortex-knowledge-worker` 正常运行，并且本次 run 的 Add/Cognify job 已经成功。

如果报告里 `knowledge_graph_html_path=null`，先看同一个 `report.json` 中的 `knowledge_events`。只要 `knowledge_events.status=failed`，样例就会自动退回到 parse artifacts，并不会进入 Cognee `visualize_graph(path)`。常见原因是 Knowledge Add 阶段的 embedding provider 预检超时，错误中会出现 `Embedding connection test timed out after 30s`。本地 Docker 可以在仓库根目录 `.env` 中保留：

```text
COGNEE_SKIP_CONNECTION_TEST=true
```

然后重启 Cortex API 与 Knowledge Worker：

```powershell
docker compose --env-file ..\..\.env -f ..\..\compose.local.yaml up -d --no-build --force-recreate cortex-api cortex-knowledge-worker
```

本地 Kuzu 图数据库有两个容易混淆的位置：

- 默认/全局图路径由 `configs/cortex.runtime.local.yaml` 或 `configs/cortex.runtime.ollama.yaml` 显式管理，默认是仓库根目录 `.data/cognee/local/graph/cognee_graph_kuzu`。
- Cognee 在启用 backend access control 时会为每个用户和数据集生成独立图数据库，通常位于容器内 `/app/.data/cognee/local/system/databases/{cognee_user_id}/{dataset_uuid}.pkl`。因此没有看到名为 `kuzu` 的目录并不代表图谱没有写入。

如果 `knowledge_graph.html` 打开后显示 `No graph data available`，通常是可视化读取了默认全局图，而不是本次 run 的 dataset graph。当前样例会从 `report.json` 读取 `dataset_key`，并调用 Cognee 的 multi-user aggregation 路径导出该 dataset 的图谱；旧版生成的空 HTML 可以用上面的 `visualize-knowledge` 命令重新生成。

如果最近的 Knowledge job 报：

```text
UNIQUE constraint failed: data.id
```

说明 Cognee 在 Add 阶段写入自己的 `data` 表时遇到了重复内容 ID。Cortex 现在会把 Add 输入包装为 Cognee `DataItem`，使用 dataset、source、parse engine 和正文 hash 生成稳定 `data_id`，避免同一批 URL 在多个解析器/多次 run 中互相撞库。更新代码后重启 `cortex-knowledge-worker` 并重新跑 example；旧失败 job 不会自动生成 Kuzu，需要重新提交。

## 8. 内置 URL 类型

`src/finance_urls.py` 内置 20 个金融 / 宏观经济来源，覆盖：

- HTML 页面
- PDF 报告
- JSON API
- CSV 数据
- 政策声明、经济展望、CPI、FRED、SEC、BIS、IMF、World Bank、ECB、BOE、FDIC 等来源

如果某个公共站点临时限流或屏蔽爬虫，样例会记录该 URL + engine 的失败，并继续处理其他组合。

## 9. 注意事项

- TensorZero adaptive A/B test 依赖 Postgres 的 `pg_cron` 扩展；本样例使用专用 `tensorzero/postgres:17`，宿主端口默认是 `5434`。
- TensorZero observability 使用 ClickHouse；本样例会启动本地 ClickHouse。
- Kimi 通过 OpenAI-compatible provider 接入，默认 base URL 为 `https://api.moonshot.cn/v1`。
- Gemini 使用 Google AI Studio 的 OpenAI-compatible endpoint：`https://generativelanguage.googleapis.com/v1beta/openai`。
- Cortex Knowledge 的 Add / Cognify 是异步任务，文档多、模型慢或 OCR 重时会花较长时间。冒烟时先用 `--max-urls 1` 或 `--skip-knowledge-jobs`。
