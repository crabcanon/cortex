# Cortex

Cortex 是一套面向 AI 原生应用的数据与知识 API 平台，统一提供网页/文件解析、对象存储、知识图谱/记忆、评测验证与数据合成能力。项目采用 Python 3.12、uv workspace、FastAPI、SQLAlchemy、S3-compatible Storage、OpenTelemetry，并通过可插拔引擎适配器保持厂商中立和可迁移。

## 功能特性

### Parse API

- `POST /v1/parse/sync`：同步解析 URL / URI / S3 object。
- `POST /v1/parse/jobs`：异步解析作业，适合长网页、批量输入和浏览器型解析。
- `GET /v1/parse/engines`：查看可用解析引擎。
- 支持 `engine_id=auto` 自动路由，也支持显式选择 `crawl4ai`、`jina_reader`、`llama_parse`、`markitdown`、`docling`。
- 用户请求保持简洁：`sources`、`engine_id`、`scene` 为核心字段；MIME、profile、重试、浏览器参数由系统自动推断和加载。

### Storage API

- `POST /v1/storage/uploads`：生产推荐的预签名上传会话。
- `POST /v1/storage/uploads/{uploadId}/complete`：确认对象已上传并写入元数据与版本记录。
- `POST /v1/storage/files`：Swagger、本地测试、小文件的单步上传接口。
- `GET /v1/storage/objects/{objectId}`：读取对象元数据。
- `POST /v1/storage/objects/{objectId}/download-url`：生成短时下载 URL。
- 兼容 MinIO、AWS S3、Ceph RGW 等 S3-compatible 实现。

### Knowledge API

- `POST /v1/knowledge/datasets`：创建知识数据集。
- `POST /v1/knowledge/add/jobs`：摄入文档、对象或解析结果。
- `POST /v1/knowledge/cognify/jobs`：构建知识图谱。
- `POST /v1/knowledge/memify/jobs`：图谱增强与派生关系。
- `POST /v1/knowledge/search`：语义、图遍历或混合搜索。
- 默认图数据库优先 Kuzu，可通过配置切换后端。

### Evaluation API

- `GET /v1/eval/engines`：查看评测引擎。
- `GET /v1/eval/metrics`：查看 Cortex 标准指标目录。
- `POST /v1/eval/sync`：小样本同步评测。
- `POST /v1/eval/jobs`：异步评测作业。
- `GET /v1/eval/jobs/{jobId}/result`：读取评测结果。
- 支持 `perf`、`rag`、`agentic`、`multi_turn`、`custom`。
- 支持 EvalScope 与 DeepEval 引擎适配。异步 Worker 会将 `dataset_id`、`object_id`、`object_ids` 自动水合为 `EvalTestCase[]`。
- Perf 压测支持直接传 OpenAI-compatible `endpoint_url`、`api_key`、`model_ref`；用户只需声明 `eval_type=perf`，Cortex 会自动展开标准 General / Latency / Tokens / Percentile 指标。
- 完成后生成 `evaluation_report` Storage object，并回写 `eval_runs.report_object_id`。

### Synthesis API

- `GET /v1/synthesis/engines`：查看数据合成引擎。
- `POST /v1/synthesis/sync`：小规模同步合成。
- `POST /v1/synthesis/jobs`：异步合成作业。
- `GET /v1/synthesis/jobs/{jobId}/result`：读取合成结果。
- 支持 `structured_single_table`、`structured_relational`、`rag_goldens`、`qa_pairs`、`conversation_goldens`、`agent_trajectories`、`custom`。
- 支持 SDV 与 DeepEval Synthesizer。异步 Worker 会将 dataset、document chunks、storage object 自动水合为 `inline_records` 或 `documents`。
- 完成后生成 `synthesis_output` Storage object，并回写 `synthesis_runs.output_object_id`。

### Auth 与 Observability

- 本地开发使用 `CORTEX_AUTH_MODE=dev`，并暴露 `POST /v1/dev/auth/token` 生成 Swagger 可用 Bearer token。
- 生产建议接入 OIDC / JWT / Introspection，把 Cortex 作为资源服务器。
- `/v1/health/live` 面向 Docker / Kubernetes liveness probe，无需 Bearer token；`/v1/health/ready` 仍需要 `health:read`。
- 所有 API 和 Worker 统一接入 OpenTelemetry，可对接 Jaeger、Prometheus、Grafana。
- Eval/Synthesis 已提供 `cortex.eval.run`、`cortex.synthesis.run` spans，以及 run count / duration 指标。

## 项目结构

```text
apps/api/                    FastAPI REST API
packages/common/             配置、错误、JSON、时间、运行时 YAML
packages/contracts/          Pydantic DTO 与 OpenAPI 契约模型
packages/db/                 SQLAlchemy models、repositories、Alembic
packages/storage/            S3-compatible storage service
packages/parse/              解析引擎注册、路由、适配器、标准化
packages/knowledge/          Cognee/Kuzu 知识域服务
packages/evaluation/         Evaluation registry、catalog、service、adapters
packages/synthesis/          Synthesis registry、service、adapters
workers/parse-worker/        Parse 异步作业执行器
workers/knowledge-worker/    Knowledge 异步作业执行器
workers/evaluation-worker/   Evaluation 异步作业执行器
workers/synthesis-worker/    Synthesis 异步作业执行器
specs/                       API、PRD、DFD、Schema、Tech、Tasks、Log
```

## 本地开发

### 1. 准备环境

推荐使用 PowerShell：

```powershell
git clone https://github.com/crabcanon/cortex.git
cd cortex

powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 sync --all-packages
```

项目固定 Python 版本由 `.python-version` 看护。请尽量通过 `scripts/dev/uv.ps1` 或 `scripts/dev/uv.sh` 运行命令，避免 uv 误删或重建 IDE 正在占用的 `.venv`。

### 2. 配置密钥

复制并填写 `.env` 与 runtime overlay：

```powershell
Copy-Item .env.example .env
Copy-Item configs\cortex.runtime.local.yaml configs\cortex.runtime.local.yaml
```

常用配置：

```text
JINA_API_KEY=...
LLAMA_CLOUD_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=...
OPENAI_MODEL_ID=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL_ID=text-embedding-3-small
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=...
OPENROUTER_MODEL_ID=openrouter/auto
OPENROUTER_EMBEDDING_MODEL_ID=openai/text-embedding-3-small
OPENROUTER_EMBEDDING_DIMENSIONS=1536
# BGE-M3 on OpenRouter:
# OPENROUTER_EMBEDDING_MODEL_ID=baai/bge-m3
# OPENROUTER_EMBEDDING_DIMENSIONS=1024
OLLAMA_BASE_URL=http://host.docker.internal:11434/v1
OLLAMA_API_KEY=ollama
OLLAMA_MODEL_ID=llama3.1:8b
OLLAMA_EMBEDDING_MODEL_ID=nomic-embed-text
OLLAMA_EMBEDDING_DIMENSIONS=768
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
GEMINI_API_KEY=...
GEMINI_MODEL_ID=gemini-2.5-flash
GEMINI_EMBEDDING_MODEL_ID=gemini/gemini-embedding-001
GEMINI_EMBEDDING_DIMENSIONS=768
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_API_KEY=...
QWEN_MODEL_ID=qwen-plus
CORTEX_AUTH_MODE=dev
CORTEX_ENV=local
CORTEX_RUNTIME_CONFIG_PATH=configs/cortex.runtime.local.yaml
```

`configs/cortex.runtime.local.yaml` 统一看护 Crawl4AI、Jina Reader、LlamaParse、Cognee、EvalScope、DeepEval、SDV 等引擎配置，避免散落在代码里。

LLM / Embedding 供应商统一按“供应商槽位”接入：

- `.env` 只声明供应商的 OpenAI-compatible `*_BASE_URL`、`*_API_KEY`、`*_MODEL_ID`、`*_EMBEDDING_MODEL_ID` 等值，例如 `OPENAI_*`、`OPENROUTER_*`、`OLLAMA_*`、`GEMINI_*`、`QWEN_*`、`LOCAL_LLM_*`。
- `configs/cortex.runtime.local.yaml` 决定不同 API 类型引用哪个槽位。默认示例中 Knowledge 的 Cognee LLM 与 embedding 都引用 `OPENROUTER_*`，Evaluation 的 DeepEval 与 Synthesis 的 DeepEval Synthesizer 仍可独立引用 `KIMI_*`。
- 如需切换供应商，只调整 runtime YAML 中的 `model_ref`、`api_url_ref`、`api_key_ref`，例如把 Evaluation 从 `env:KIMI_BASE_URL` 改为 `env:OPENAI_BASE_URL`。
- Cognee 所需的 `llm_provider`、`embedding_provider`、BAML LLM 字段由 Cortex 适配层按 OpenAI-compatible 默认值补齐；常规使用不需要在配置文件里重复填写。Cortex 也会把 Knowledge 选中的 LLM 槽位同步到 `OPENAI_BASE_URL`、`OPENAI_API_KEY`、`OPENAI_API_BASE`、`LITELLM_API_BASE`、`LITELLM_API_KEY`，防止 Cognee / LiteLLM 静默读取宿主或容器里的 OpenAI 默认值。
- 本地 Knowledge 默认将 Cognee 的 `openrouter` provider alias 映射为 OpenAI-compatible SDK 调用；推荐 `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`、`OPENROUTER_MODEL_ID=openrouter/auto`、`OPENROUTER_EMBEDDING_MODEL_ID=openai/text-embedding-3-small`。如果切到 BGE-M3 这类 OpenRouter embedding 模型，推荐使用 `OPENROUTER_EMBEDDING_MODEL_ID=baai/bge-m3`；Cortex 会在 Cognee/LiteLLM 调用前自动规范化为 `openrouter/baai/bge-m3`，同时请把 `OPENROUTER_EMBEDDING_DIMENSIONS` 改成模型实际维度，例如 BGE-M3 常用 `1024`。
- Embedding 服务和 tokenizer 估算策略是解耦的：`knowledge.cognee.embedding` 下的 `tokenizer.strategy` 可选 `auto`、`tiktoken`、`huggingface`、`approximate` / `none`，并可配置 `model`、`encoding`、`fallback_strategy`。这些字段只由 Cortex 适配层消费，不会传入 Cognee SDK 的 embedding config；真实 embedding 请求始终使用 `embedding_model_ref` 指向的模型 ID。
- 本地 Knowledge 图数据库使用 Cognee + Kuzu。默认/全局图路径由 `configs/cortex.runtime.local.yaml` 与 `configs/cortex.runtime.ollama.yaml` 显式设置为 `.data/cognee/local/graph/cognee_graph_kuzu`；启用 Cognee backend access control 后，实际 Add/Cognify 会为每个用户和数据集生成独立图数据库，通常在容器内 `/app/.data/cognee/local/system/databases/{cognee_user_id}/{dataset_uuid}.pkl`。Cognee 启动早期日志里的 `graph_database_name=` 可能仍为空，因为那条日志在 Cortex runtime config 应用前输出；真正判断以 Add/Cognify job 和 dataset-scoped graph context 为准。
- 本地 Docker 默认透传 `COGNEE_SKIP_CONNECTION_TEST=true`，用于绕过 Cognee 在 Add 阶段对 LLM/Embedding provider 的预检超时。生产 Compose 默认是 `false`，建议保留严格预检，只有在已有外部健康检查或 provider 网关预热机制时再改为 `true`。
- Cortex 会把 Knowledge Add 的 text/uri 输入包装为 Cognee `DataItem`，并用 dataset、source、engine、content hash 生成稳定 `data_id`；这避免多次实验或多解析器解析相同内容时触发 Cognee SQLite `UNIQUE constraint failed: data.id`。如果历史失败 job 仍存在，重新提交新的 Add/Cognify job 即可，旧失败记录不会自动补写 Kuzu。
- Ollama 也作为一等 provider slot 提供。容器内访问宿主机 Ollama 时使用 `OLLAMA_BASE_URL=http://host.docker.internal:11434/v1`，`OLLAMA_API_KEY=ollama` 是 OpenAI SDK 兼容路径需要的占位值。执行 `ollama pull llama3.1:8b` 与 `ollama pull nomic-embed-text` 后，将 `CORTEX_RUNTIME_CONFIG_PATH` 切到 `configs/cortex.runtime.ollama.yaml`，即可让 Knowledge、DeepEval Evaluation 和 DeepEval Synthesis 统一引用 `OLLAMA_*`。
- Cortex 会在 Evaluation / Synthesis runtime worker 中按当前引擎引用的槽位同步设置 `OPENAI_API_URL`、`OPENAI_BASE_URL`、`OPENAI_API_BASE`、`LITELLM_API_BASE`，兼容 OpenAI SDK、LiteLLM 与 DeepEval 的常见读取方式。

Evaluation / Synthesis 不再配置专属 API Key：

- EvalScope 支持两种模式：`mode: external_http` 调用外部 EvalScope 服务；`mode: self_hosted_sdk` 由 Cortex 通过 `evalscope[service]` 和 `evalscope.service.run_service(...)` 在 runtime worker 内自部署服务后再调用 `/api/v1/eval`、`/api/v1/perf`。EvalScope 不需要所谓 vendor key；如果外部服务被网关保护，请在 `evaluation.engines.evalscope.headers` 中配置 `Authorization` 等服务访问 header。
- DeepEval 与 DeepEval Synthesizer 不再使用独立的 vendor API Key；它们分别跟随 runtime YAML 所引用的模型供应商槽位。
- DeepEval Evaluation 会优先构造 Cortex 的 OpenAI-compatible judge wrapper，显式把 `base_url`、`api_key`、`model` 传给 OpenAI SDK，避免 DeepEval 仅凭模型字符串进行隐式供应商路由。
- 如果 Kimi、Moonshot 或其他模型服务在宿主机可访问但容器内连接失败，请在 `.env` 中配置 `HTTPS_PROXY` / `HTTP_PROXY` / `ALL_PROXY`，Compose 会透传给 Cortex 与 TensorZero Gateway 容器。本地 Docker Desktop 使用宿主机代理时，推荐写成 `http://host.docker.internal:7890`。
- Knowledge / Evaluation / Synthesis Worker 默认 lease 为 300 秒、heartbeat 为 30 秒，可通过 `CORTEX_*_WORKER_LEASE_SECONDS` 和 `CORTEX_*_WORKER_HEARTBEAT_INTERVAL_SECONDS` 覆盖，避免长模型调用被 60 秒旧 lease 误判为 stale job。

### 3. 启动依赖和服务

一键启动依赖、API、Parse Worker、Knowledge Worker、Evaluation Worker、Synthesis Worker：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 up -Build
```

重型构建模式会额外构建并启用 Docling Parse Worker、DeepEval Evaluation Worker、SDV / DeepEval Synthesis Worker：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 build -Heavy
powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 up -Build -Heavy
```

`up -Heavy` 默认只启动 runtime 版 Evaluation / Synthesis Worker，不启动 slim worker，避免轻量 worker 抢到需要 DeepEval、EvalScope self-hosted SDK、SDV SDK 的重型作业。若需要验证 EvalScope external HTTP adapter 或其它轻量引擎，可显式指定 slim worker 服务。

等价 Compose profile 为 `docling`、`eval-runtime`、`synthesis-runtime`：

```powershell
docker compose -p cortex-local -f compose.local.yaml --profile docling --profile eval-runtime --profile synthesis-runtime build
```

本地重型模式下，API 镜像仍保持轻量，不直接安装 Docling、DeepEval、SDV 这类重 SDK。`/v1/eval/engines` 与 `/v1/synthesis/engines` 中看到 `degraded` 表示“API 进程不可同步执行，但已启用并可路由到 runtime worker”。这时请使用 `/v1/eval/jobs`、`/v1/synthesis/jobs`；`/sync` 只有在当前 API 进程也安装对应 runtime extra 时才适合使用。

Parse Worker 也按 engine 能力领取任务：默认 `cortex-parse-worker` 只处理 `crawl4ai,jina_reader,llama_parse,markitdown`，`cortex-parse-worker-docling` 只处理 `docling`。因此 Swagger 中显式提交 `engine_id=docling` 时，请使用重型启动方式，避免任务没有 Docling worker 消费。

Docling worker 日志中的 RapidOCR `Using engine_name`、`File exists and is valid`、`Loading weights` 通常是 OCR / layout 模型冷启动信息，不代表解析失败。本地和容器启动脚本现在会让 Parse Worker 长驻轮询，并在 Docling adapter 内复用 `DocumentConverter`，避免每一轮队列轮询都重启进程、重复加载模型；真正的作业失败会以 `cortex parse worker run: failed ...` 或 job event 形式出现。

不重建镜像时：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 up
```

访问入口：

| 服务 | 地址 |
| --- | --- |
| Swagger UI | http://127.0.0.1:8080/docs |
| MinIO S3 API | http://127.0.0.1:9000 |
| MinIO Console | http://127.0.0.1:9001 |
| Jaeger | http://127.0.0.1:16686 |
| Prometheus | http://127.0.0.1:9090 |
| Grafana | http://127.0.0.1:3000 |

EvalScope self-hosted SDK 本地默认监听 `http://127.0.0.1:19000`，避免和 MinIO S3 API 的 `9000` 端口冲突。容器内由 `cortex-evaluation-worker-runtime` 按需启动，不需要在宿主机额外暴露端口。

Grafana 本地默认账号：`admin` / `admin`。

Swagger UI 静态资源由 API 镜像自托管在 `/_docs/swagger-ui/5.32.4/*`，当前内置 Swagger UI `5.32.4`，可渲染 OpenAPI `3.1.0`。若浏览器控制台出现 `SwaggerUIBundle is not defined` 或提示 OpenAPI 版本无效，通常说明镜像不是最新版本、浏览器缓存仍命中旧资源，或代理拦截了 `/_docs/swagger-ui/5.32.4/swagger-ui-bundle.js`，请重新构建 API 镜像并检查该静态资源 URL 是否返回 200。

### 4. 仅本地进程启动

如果只想本地运行 API 和 Worker，可先启动依赖：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 up
```

再运行数据库迁移和服务：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run --package cortex-db cortex-db-migrate upgrade head
powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run --package cortex-api cortex-api
```

单次消费 Worker：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run --package cortex-worker-parse cortex-parse-worker
powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run --package cortex-worker-knowledge cortex-knowledge-worker
powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run --package cortex-worker-evaluation cortex-evaluation-worker
powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run --package cortex-worker-synthesis cortex-synthesis-worker
```

`scripts/dev/run-parse-worker.ps1` 和 `scripts/dev/run-parse-worker.sh` 默认只领取轻量 parse engines：`crawl4ai,jina_reader,llama_parse,markitdown`。如果你确认本地 `.venv` 已安装 `cortex-parse[docling]` 并希望直接在宿主机消费 Docling 作业，可显式传入：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\run-parse-worker.ps1 -EngineKeys docling
```

## Swagger 调试流程

### 1. 获取本地 token

仅在 `CORTEX_ENV=local` 且 `CORTEX_AUTH_MODE=dev` 时可用：

```http
POST /v1/dev/auth/token
```

示例 body：

```json
{
  "tenant_id": "tenant_demo",
  "actor_id": "alice",
  "actor_type": "user",
  "actor_ref": "alice@example.com",
  "display_name": "Alice",
  "scopes": [
    "health:read",
    "parse:read",
    "parse:write",
    "storage:read",
    "storage:write",
    "storage:download",
    "knowledge:read",
    "knowledge:write",
    "eval:read",
    "eval:write",
    "synthesis:read",
    "synthesis:write",
    "jobs:read",
    "jobs:cancel"
  ],
  "roles": ["tenant_admin"],
  "expires_in": 86400
}
```

把响应中的 `swagger_authorize_value` 粘贴到 Swagger UI 的 Authorize 弹窗即可。

### 2. Parse 示例

```json
{
  "sources": [
    "https://docs.cognee.ai/core-concepts/overview"
  ],
  "engine_id": "auto"
}
```

解析已上传到本地 MinIO / S3 的 Cortex Storage 对象时，推荐直接传对象 ID，也可以传包含 `obj_...` 的 bucket/key。以下两种写法等价，Cortex 会自动提取 `obj_a3da...`、签发下载 URL、侦测 MIME 并按 `scene` 路由：

```json
{
  "sources": [
    "cortex://objects/obj_a3da967e3ca446cab3631bb7",
    "s3://cortex-local/tenant_demo/obj_a3da967e3ca446cab3631bb7/bofa_note.pdf"
  ],
  "engine_id": "docling",
  "scene": "document_ai",
  "priority": 5
}
```

显式指定 `engine_id` 时不会沿用 `auto` fallback：批量 sources 中的每个任务都会固定到同一个指定引擎。Docling 属于重型文档解析能力，本地 Docker 请使用 `up -Heavy` 或 `--profile docling` 启动 `cortex-parse-worker-docling`，默认轻量 `cortex-parse-worker` 不会领取 `docling` 作业。

### 3. 小文件上传示例

`POST /v1/storage/files` 使用 `multipart/form-data`：

- `file`: 选择本地文件。
- `metadata_json`: `{"source":"swagger"}`
- `tags`: `docs,product`

返回的 `object_id` 可用于 Parse、Knowledge、Evaluation 或 Synthesis。

### 4. Knowledge 一键 Try it out 示例

Swagger UI 中的 Knowledge 请求体已经内置了一组可直接复用的 examples。建议按下面顺序执行：

1. `POST /v1/knowledge/datasets`，选择 `swaggerDemoDataset`，创建 `swagger_knowledge_demo`。
2. `POST /v1/knowledge/add/jobs`，选择 `swaggerInlineTextIngest`，这条不依赖外部文件，最适合本地冒烟。
3. 启动或等待 `cortex-knowledge-worker` 消费 Add job。
4. `POST /v1/knowledge/cognify/jobs`，选择 `swaggerDemoCognify`。
5. `POST /v1/knowledge/memify/jobs`，选择 `swaggerTripletMemify`。
6. `POST /v1/knowledge/search`，选择 `swaggerDemoSearch`。

如果想验证 Storage -> Knowledge 链路，先用 `POST /v1/storage/files` 上传一个 `README.md` 或 PDF，拿到响应里的 `object_id`，再在 `POST /v1/knowledge/add/jobs` 中选择 `storageObjectIngest`，把示例里的 `obj_a3da967e3ca446cab3631bb7` 替换为真实 `object_id`。

### 5. Evaluation Job 示例

Perf 压测无需手工列出指标，默认输出 EvalScope 官方压测指标全集：

```json
{
  "name": "swagger-perf-job",
  "eval_type": "perf",
  "engine_id": "evalscope",
  "input": {
    "type": "builtin_dataset",
    "builtin_dataset_key": "longalpaca"
  },
  "target": {
    "type": "api",
    "protocol": "openai_compatible",
    "endpoint_url": "https://openrouter.ai/api/v1/chat/completions",
    "api_key": "sk-xxx",
    "model_ref": "deepseek/deepseek-v4-flash",
    "timeout_seconds": 60
  },
  "engine_options": {
    "parallel": [1, 2],
    "number": [2, 2],
    "stream": false,
    "max_tokens": 2048,
    "min_tokens": 1024,
    "max_prompt_length": 2048,
    "min_prompt_length": 1024
  },
  "output": {
    "persist_report_object": true
  }
}
```

RAG / custom / agentic 等业务评测仍可显式声明指标和阈值：

```json
{
  "name": "docs-rag-eval",
  "eval_type": "rag",
  "engine_id": "auto",
  "input": {
    "type": "object",
    "object_id": "obj_xxx",
    "field_mapping": {
      "user_input": "question",
      "actual_output": "answer",
      "expected_output": "expected",
      "retrieval_contexts": "contexts"
    }
  },
  "metrics": [
    {
      "metric_key": "rag.faithfulness",
      "threshold": 0.8
    },
    {
      "metric_key": "rag.answer_relevance",
      "threshold": 0.7
    }
  ],
  "output": {
    "persist_report_object": true
  }
}
```

Worker 完成后：

```http
GET /v1/eval/jobs/{jobId}/result
```

结果中会包含 `artifacts[].label=evaluation_report`、`artifacts[].object_id` 和 `artifacts[].uri=s3://bucket/key`。EvalScope Perf 的原生报告文件会以 `evalscope_artifact` 形式同步上传至 S3，保留 `perf` 目录内的相对路径；上传成功后，worker 会清理容器内 `/app/outputs/{job_id}/perf` 临时目录。

### 6. Synthesis Job 示例

```json
{
  "name": "rag-golden-generation",
  "synthesis_type": "rag_goldens",
  "engine_id": "auto",
  "source": {
    "type": "documents",
    "documents": [
      "Cortex supports parse, storage, knowledge, evaluation, and synthesis."
    ]
  },
  "config": {
    "sample_count": 5,
    "include_expected_output": true,
    "quality_gates": [
      {
        "metric_key": "quality.correctness",
        "threshold": 0.8
      }
    ]
  },
  "output": {
    "output_format": "json",
    "persist_object_filename": "rag-goldens.json"
  }
}
```

Worker 完成后：

```http
GET /v1/synthesis/jobs/{jobId}/result
```

结果中会包含 `outputs[].label=synthesis_output`。

## 测试与校验

常用快速校验：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run ruff check packages/evaluation/src/cortex_evaluation packages/synthesis/src/cortex_synthesis packages/storage/src/cortex_storage workers/evaluation-worker/src/cortex_worker_evaluation workers/synthesis-worker/src/cortex_worker_synthesis
powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run pyright packages/evaluation/src/cortex_evaluation packages/synthesis/src/cortex_synthesis packages/storage/src/cortex_storage workers/evaluation-worker/src/cortex_worker_evaluation workers/synthesis-worker/src/cortex_worker_synthesis
powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run python -m pytest tests/unit/test_eval_synthesis_adapters.py tests/integration/test_api_eval_synthesis.py tests/contract/test_openapi_contract.py -q
powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run python scripts/ci/validate_yaml.py specs/cortex-api.yaml
```

更完整的相关回归：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run python -m pytest tests/unit/test_eval_synthesis_adapters.py tests/integration/test_api_eval_synthesis.py tests/integration/test_api_storage.py tests/integration/test_api_e2e.py tests/contract/test_openapi_contract.py -q
```

## Docker 与生产部署

本地 Compose 是 batteries-included，包含 Postgres、Redis、MinIO、OTel Collector、Jaeger、Prometheus、Grafana、API 和核心 Workers。

生产推荐使用标准 Bash 发布脚本 + GHCR 预构建镜像 + `compose.prod.yaml` 作为模板。完整构建、发布、部署、回滚流程见 [`deploy/README.md`](deploy/README.md)。

```bash
bash scripts/deploy/release.sh deploy --env-file .env.prod --heavy
```

也可以通过 GitHub Actions 的 `Docker Images` workflow 发布所有镜像，或在本地执行：

```bash
bash scripts/deploy/release.sh build --tag local-heavy --heavy
```

生产环境建议：

- 使用托管 Postgres / S3-compatible Storage / Redis。
- `CORTEX_AUTH_MODE=oidc` 或 JWT/JWKS 模式。
- `CORTEX_S3_AUTO_CREATE_BUCKET=false`，由基础设施提前创建 bucket。
- `CORTEX_OTEL_EXPORTER_OTLP_ENDPOINT` 指向统一 Collector。
- API、Parse Worker、Knowledge Worker、Evaluation Worker、Synthesis Worker 独立扩缩容。
- Docling/OCR/Torch 走 `parse-worker-docling` profile，避免拖大默认 API 镜像。
- DeepEval / EvalScope self-hosted SDK / SDV 等评测与合成重依赖走 `evaluation-worker-runtime`、`synthesis-worker-runtime` 镜像或对应 Compose profile；默认 Evaluation / Synthesis Worker 保持轻量，适合 EvalScope external HTTP service、队列调度和 scaffold/禁用状态验证。
- Railway 上线建议使用 GHCR 预构建镜像，每个 API / Worker target 建一个独立 Service；不要让 Railway 自动猜测 Dockerfile target。

需要在本地构建包含 DeepEval / SDV 的重型 worker 时：

```bash
docker compose -f compose.local.yaml --profile eval-runtime --profile synthesis-runtime build cortex-evaluation-worker-runtime cortex-synthesis-worker-runtime
```

启用重型 worker 时，请停止或缩容同一队列上的轻量 Evaluation / Synthesis Worker，避免轻量 worker 抢到需要本地 DeepEval / EvalScope / SDV SDK 的作业。

## Crawl4AI 浏览器运行时

Crawl4AI 依赖 Playwright 浏览器。项目已将运行时准备集中到：

```bash
python scripts/runtime/prepare_crawl4ai_runtime.py --json
```

容器内默认使用官方 Playwright Python 镜像，浏览器路径为 `/ms-playwright`。生产阶段建议在镜像构建或部署前完成浏览器准备，运行阶段只做探针，不做现场下载。

## 设计文档

| 文档 | 说明 |
| --- | --- |
| `specs/cortex-api.yaml` | OpenAPI 3.x REST 契约 |
| `specs/cortex-prd.md` | 产品需求文档 |
| `specs/cortex-tech.md` | 技术设计、代码模型、运行时设计 |
| `specs/cortex-dfd.md` | 数据流设计 |
| `specs/cortex-schema.md` | 逻辑 Schema 设计 |
| `specs/cortex-init.sql` | 数据库初始化 SQL |
| `specs/cortex-tasks.md` | 开发任务时间轴 |
| `specs/cortex-log.md` | 问题、修复、验证记录 |

## 当前状态

- REST API、OpenAPI、数据库模型、Workers、运行时配置和本地 Compose 已覆盖 Parse、Storage、Knowledge、Evaluation、Synthesis 五大域。
- Evaluation / Synthesis 已具备 pluggable adapter、async job、input hydration、artifact persistence、OTel telemetry 和测试覆盖。
- 后续重点是接入更多真实评测/合成场景、完善 Grafana Dashboard，并沉淀更多云平台部署模板。
