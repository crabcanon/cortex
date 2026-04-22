# Cortex

## 2026-04-21 镜像瘦身与 Docling 拆分说明

以下说明优先级高于较早版本中“默认镜像包含全部解析引擎依赖”的描述：

- `cortex-api` 与默认 `cortex-parse-worker` 现在只安装默认解析引擎集：`crawl4ai`、`jina_reader`、`llama_parse`、`markitdown` 基础包。
- `docling`、`torch`、`opencv-python`、完整 `markitdown[all]` 等重型文档依赖已经拆到独立镜像 target：`parse-worker-docling`。
- 本地和生产 Compose 都新增了 `cortex-parse-worker-docling` 服务，并通过 `--profile docling` 显式启用。
- `knowledge-worker` 已经是独立 Docker target 和 Compose 服务，不再遗漏在一键启动链路之外。
- 默认 API 镜像不再因为 `docling -> torch` 下载失败而阻断构建；需要 Docling 高保真文档解析时，单独构建和扩缩容 Docling Worker。
- `knowledge-worker` 的 Python slim 基础镜像默认改为 `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`，不再依赖 Docker Hub 的 `python:3.12.12-slim`；`uv` 二进制从 `ghcr.io/astral-sh/uv:0.7.22` 复制，减少构建阶段网络故障点。

默认本地启动：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 up -Build
```

需要 Docling Worker 时再额外启用：

```powershell
docker compose -p cortex-local -f compose.local.yaml --profile docling up -d --build cortex-parse-worker-docling
```

如果企业网络对 GHCR / MCR 也做了代理或镜像加速，可通过环境变量覆盖构建基线：

```powershell
$env:CORTEX_PYTHON_BASE_IMAGE="your-registry.example.com/astral-sh/uv:python3.12-bookworm-slim"
$env:CORTEX_UV_IMAGE="your-registry.example.com/astral-sh/uv:0.7.22"
$env:CORTEX_PLAYWRIGHT_PYTHON_BASE_IMAGE="your-registry.example.com/playwright/python:v1.58.0-noble"
powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 up -Build
```

## 2026-04-19 容器内 Crawl4AI 修正说明

以下说明优先级高于前文较早版本中关于本地 Compose 的旧描述：

- `compose.local.yaml` 不再通过“跳过 Crawl4AI 浏览器能力”来换取启动成功。
- `cortex-api` 与 `cortex-parse-worker` 现在直接基于 Playwright 官方 Python 镜像 `mcr.microsoft.com/playwright/python:v1.58.0-noble` 构建。
- 该镜像已经预装浏览器与系统依赖，因此构建阶段不再执行 `playwright install --with-deps`，避免因 Debian 镜像源短时故障导致本地整栈构建失败。
- 容器运行时会继续执行 Crawl4AI 预检，真正验证 `crawl4ai` 在容器内可用，而不是仅把能力绕开。
- 容器内统一通过 `CORTEX_PLAYWRIGHT_BROWSERS_PATH=/ms-playwright` 覆盖 runtime YAML 里的宿主机浏览器目录，确保 API、Parse Worker、Docker 镜像三者看到的是同一份 Playwright 浏览器安装。
- `cortex-api` 与 `cortex-parse-worker` 默认启用 `init: true` 与 `shm_size: 1gb`，降低 Chromium 在容器内的僵尸进程与共享内存问题。

推荐本地启动：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 up -Build
```

## Docker Compose 启动方式（2026-04-17 更新）

仓库现在正式区分两套 Compose：

### 1. 本地一键联调：`compose.local.yaml`

用途：开发、集成测试、冒烟验证。

会同时启动：
- 基础依赖：`postgres`、`minio`、`redis`
- 遥测栈：`otel-collector`、`jaeger-all-in-one`、`prometheus`、`grafana`
- Cortex 核心服务：`cortex-migrate`、`cortex-api`、`cortex-parse-worker`、`cortex-knowledge-worker`

说明：
- 本地 compose 现在默认跳过 Crawl4AI 浏览器在镜像构建阶段的预安装。
- 同时默认跳过容器启动时的 Crawl4AI 浏览器预探针。
- 这样做是为了避免开发机在 `docker compose up -Build` 时因为 Debian / Playwright 镜像源抖动而整栈起不来。
- 如果你本轮只是验证 API、Storage、Jobs、非浏览器型 Parse、Knowledge，这个默认值更稳。
- 如果你要专门验证容器内的 `crawl4ai`，建议单独准备 Linux 浏览器依赖或走生产态镜像构建路径。

推荐命令：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 up -Build
```

等价原生命令：

```powershell
docker compose -p cortex-local -f compose.local.yaml up -d --build
```

常用操作：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 ps
powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 logs -Follow
powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 down
```

本地关键入口：
- API: `http://127.0.0.1:8080`
- Swagger: `http://127.0.0.1:8080/docs`
- MinIO Console: `http://127.0.0.1:9001`
- Jaeger: `http://127.0.0.1:16686`
- Prometheus: `http://127.0.0.1:9090`
- Grafana: `http://127.0.0.1:3000`

### 2. 生产/预发部署：`compose.prod.yaml`

用途：自托管生产、预发、云上容器运行时。

只编排 Cortex 核心容器：
- `cortex-migrate`
- `cortex-api`
- `cortex-parse-worker`
- `cortex-knowledge-worker`

它默认假定以下能力由外部提供：
- PostgreSQL
- S3 兼容对象存储
- Redis
- OpenTelemetry Collector
- 身份提供方 / OIDC / OAuth 2.0

建议先基于 [`.env.prod.example`](.env.prod.example) 生成 `.env.prod`，再启动生产 compose。

推荐命令：

```bash
docker compose --env-file .env.prod -f compose.prod.yaml up -d
```

如需先执行迁移：

```bash
docker compose --env-file .env.prod -f compose.prod.yaml --profile migrate up cortex-migrate
docker compose --env-file .env.prod -f compose.prod.yaml up -d
```

### 3. 为什么要拆分 local / prod

不拆分的话，最容易出现三类问题：

1. 把本地开发用的 MinIO / Grafana / Jaeger 拓扑错误带入生产。
2. 把调试态默认值、开放端口、弱鉴权配置错误带入生产。
3. 让 API、Parse Worker、Knowledge Worker 失去独立伸缩能力。

所以当前推荐策略是：
- `compose.local.yaml` 负责“本地全栈可运行”
- `compose.prod.yaml` 负责“核心服务可部署”
- 更底层的数据库、对象存储、遥测和鉴权基础设施交给云平台、IaC 或独立运维编排

面向内容解析、对象存储与知识流水线的一套厂商中立 RESTful API 平台。

Cortex 基于 Python 3.12、`uv workspace`、FastAPI、标准 SQL、S3 兼容对象存储与 OpenTelemetry 构建，目标是把以下三类能力收敛到同一套控制面中：

- Parse API：把网页 URL、对象文件或外部 URI 解析为 LLM-ready Markdown、标准化元数据和可选产物
- Storage API：把任意文件上传到 S3 兼容对象存储，并在关系型数据库中维护对象元数据、版本与审计信息
- Knowledge API：围绕 Cognee 风格的 Add / Cognify / Memify / Search 形成可扩展知识流水线

当前仓库已经包含：

- OpenAPI 3.1 合同：[specs/cortex-api.yaml](specs/cortex-api.yaml)
- 数据流设计：[specs/cortex-dfd.md](specs/cortex-dfd.md)
- 技术设计：[specs/cortex-tech.md](specs/cortex-tech.md)
- 数据库初始化与迁移基线：[specs/cortex-init.sql](specs/cortex-init.sql)
- 任务台账与问题日志：[specs/cortex-tasks.md](specs/cortex-tasks.md)、[specs/cortex-log.md](specs/cortex-log.md)

## 1. 核心特性

### 1.1 Parse API

- 支持同步解析与异步解析作业
- 解析结果统一收敛为 Markdown、结构化元数据、诊断信息和 provenance
- 通过可插拔 adapter 适配多种解析引擎：
  - Crawl4AI
  - Jina Reader
  - LlamaParse（云 API 模式）
  - MarkItDown
  - Docling
- 对外采用极简 `sources + engine_id (+ scene)` 契约，`engine_id=auto` 时由系统自动为每个来源选择最佳激活引擎，内部通过请求编译器绑定 scene preset、parser profile、回退策略和引擎默认配置
- `/v1/parse/engines` 会直接暴露当前 runtime config 与镜像安装集共同可用的解析引擎目录；默认镜像激活 `crawl4ai`、`jina_reader`、`llama_parse`、`markitdown`，`docling` 由独立 `parse-worker-docling` 镜像承载，避免默认 API / Parse Worker 被 `torch` 这类重型依赖拖大。

### 1.2 Storage API

- 基于 S3 兼容接口提供单段上传、多段上传和下载 URL 签发
- 元数据落标准 SQL，可运行于 SQLite、PostgreSQL 等关系型数据库
- 对象元数据、版本、标签、访问策略、校验和和审计字段统一管理
- 上传、下载、元数据读取均具备功能权限和数据权限校验

### 1.3 Knowledge API

- 支持数据集创建与读取
- 支持 Add / Cognify / Memify / Search 四类操作
- 长任务通过作业表和 Worker 执行，保持 REST 契约稳定
- Search 返回 answer、context items、graph paths、citation 与请求审计
- Knowledge runtime 通过统一抽象屏蔽底层 Cognee / 图库 / 向量库细节

### 1.4 权限治理

- 认证兼容 OAuth 2.0 / OIDC
- 支持 `dev`、`jwt`、`introspection`、`hybrid` 四种认证模式
- 功能权限通过 scope 表达
- 数据权限通过租户边界、`access_level`、角色绑定和资源策略综合裁决
- 授权决策持久化审计，支持 `decision_id`、`request_id`、`trace_id` 关联

### 1.5 可观测性

- 所有 API 对齐 OpenTelemetry 标准
- 支持 `traceparent`、`tracestate`、`baggage`
- API 暴露 Prometheus 兼容的 `/metrics`
- 可直接接入 Jaeger、Prometheus、Grafana
- 已补齐 live probe，可验证 `OTLP -> Collector -> Jaeger / Prometheus` 全链路

## 2. 已实现 API

### 2.1 健康检查与可观测性

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/v1/health/live` | 存活检查 |
| `GET` | `/v1/health/ready` | 就绪检查 |
| `GET` | `/metrics` | Prometheus 指标 |

### 2.2 Jobs

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/v1/jobs/{jobId}` | 查询作业状态 |
| `GET` | `/v1/jobs/{jobId}/events` | 查询作业事件轨迹 |
| `POST` | `/v1/jobs/{jobId}/cancel` | 取消作业 |

### 2.3 Parse

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/v1/parse/engines` | 查询解析引擎目录 |
| `GET` | `/v1/parse/profiles` | 查询 parser profile |
| `POST` | `/v1/parse/sync` | 同步解析 |
| `POST` | `/v1/parse/jobs` | 提交异步解析作业 |
| `GET` | `/v1/parse/jobs/{jobId}/result` | 轮询解析结果 |

### 2.4 Storage

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/v1/storage/uploads` | 创建上传会话 |
| `POST` | `/v1/storage/uploads/{uploadId}/complete` | 完成上传 |
| `GET` | `/v1/storage/objects/{objectId}` | 读取对象元数据 |
| `GET` | `/v1/storage/objects/{objectId}/download-url` | 生成下载 URL |

### 2.5 Knowledge

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/v1/knowledge/datasets` | 创建数据集 |
| `GET` | `/v1/knowledge/datasets/{datasetId}` | 查询数据集 |
| `POST` | `/v1/knowledge/add/jobs` | 提交 Add 作业 |
| `POST` | `/v1/knowledge/cognify/jobs` | 提交 Cognify 作业 |
| `POST` | `/v1/knowledge/memify/jobs` | 提交 Memify 作业 |
| `POST` | `/v1/knowledge/search` | 执行知识检索 |

静态合同在 [specs/cortex-api.yaml](specs/cortex-api.yaml)，运行态文档在：

- `http://127.0.0.1:8080/docs`
- `http://127.0.0.1:8080/redoc`
- `http://127.0.0.1:8080/openapi.json`

## 3. 架构总览

```mermaid
flowchart LR
    Client["Client / SDK / Agent"] --> API["Cortex API (FastAPI)"]
    API --> SQL["Relational DB (SQLite / PostgreSQL)"]
    API --> S3["S3-compatible Object Storage"]
    API --> Parse["Parse Runtime / Adapters"]
    API --> Knowledge["Knowledge Runtime / Cognee Adapter"]
    ParseWorker["Parse Worker"] --> SQL
    ParseWorker --> Parse
    KnowledgeWorker["Knowledge Worker"] --> SQL
    KnowledgeWorker --> Knowledge
    API --> OTel["OpenTelemetry Collector"]
    ParseWorker --> OTel
    KnowledgeWorker --> OTel
    OTel --> Jaeger["Jaeger"]
    OTel --> Prom["Prometheus"]
    Prom --> Grafana["Grafana"]
```

## 4. 仓库结构

| 路径 | 说明 |
| --- | --- |
| `apps/api` | FastAPI 控制面应用 |
| `workers/parse-worker` | Parse Worker |
| `workers/knowledge-worker` | Knowledge Worker |
| `packages/common` | settings、异常、ID、runtime config 等共享基础设施 |
| `packages/contracts` | Pydantic DTO / OpenAPI 对应模型 |
| `packages/domain` | 领域模型 |
| `packages/db` | SQLAlchemy、Alembic、repository、unit-of-work |
| `packages/auth` | 认证、scope、RBAC/ABAC、审计 |
| `packages/storage` | S3 兼容存储 facade 与服务 |
| `packages/parse` | 解析抽象、profile、adapter、parse 服务 |
| `packages/knowledge` | 数据集、Cognee runtime 抽象、搜索与作业服务 |
| `packages/observability` | OTel bootstrap、trace、metrics、日志关联 |
| `configs` | 统一运行时配置及 local/staging/prod overlay |
| `scripts/dev` | 本地启动、栈管理、探针、PowerShell 辅助脚本 |
| `scripts/ci` | 跨平台校验入口 |
| `tests` | contract / unit / integration 测试 |
| `specs` | API、架构、schema、任务、问题日志等设计文档 |

## 5. 运行环境要求

建议环境：

- Python `3.12`
- [uv](https://docs.astral.sh/uv/)（依赖管理与 workspace 安装）
- PowerShell 7（Windows 下建议）
- Docker / Docker Compose（需要完整本地依赖栈时）

可选依赖：

- MinIO 或任意 S3 兼容对象存储
- PostgreSQL
- OpenTelemetry Collector
- Jaeger
- Prometheus
- Grafana
- 各解析/知识引擎对应的 provider 凭据

## 6. 配置模型

### 6.1 `.env`

根目录 `.env` 负责非结构化运行参数和密钥注入，模板见 [.env.example](.env.example)。

最重要的环境变量如下：

| 变量 | 说明 |
| --- | --- |
| `CORTEX_DB_DSN` | 主业务数据库 DSN，支持 SQLite / PostgreSQL |
| `CORTEX_S3_ENDPOINT` | S3 兼容存储端点 |
| `CORTEX_S3_BUCKET` | 默认 bucket |
| `CORTEX_AUTH_MODE` | `dev` / `jwt` / `introspection` / `hybrid` |
| `CORTEX_AUTH_JWT_SHARED_SECRET` | `jwt` / `hybrid` 模式下验证外部 JWT 的共享密钥 |
| `CORTEX_AUTH_INTROSPECTION_URL` | `introspection` / `hybrid` 模式下的外部 token introspection 地址 |
| `CORTEX_AUTH_INTROSPECTION_CLIENT_ID` / `CORTEX_AUTH_INTROSPECTION_CLIENT_SECRET` | 调用 introspection 端点所需的客户端凭据 |
| `CORTEX_RUNTIME_CONFIG_PATH` | 指向统一 runtime config 文件 |
| `CORTEX_OTEL_ENABLED` | 是否开启 OTel |
| `CORTEX_OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP HTTP 导出地址 |
| `JINA_API_KEY` | Jina Reader API Key |
| `LLAMA_CLOUD_API_KEY` | LlamaParse 云 API Key |
| `OPENAI_API_KEY` | Cognee LLM / Embedding 所需 |
| `COGNEE_*` | Cognee 外部图库/向量库/关系库配置 |

### 6.2 统一 runtime config

运行时的结构化配置收敛在 `configs/` 目录：

| 文件 | 用途 |
| --- | --- |
| `configs/cortex.runtime.yaml` | 基线默认值 |
| `configs/cortex.runtime.local.yaml` | 本地开发 / 本地集成验证 |
| `configs/cortex.runtime.staging.yaml` | 预发环境 |
| `configs/cortex.runtime.prod.yaml` | 生产环境 |

切换方式：

```bash
export CORTEX_RUNTIME_CONFIG_PATH=configs/cortex.runtime.prod.yaml
```

或在 PowerShell 中：

```powershell
$env:CORTEX_RUNTIME_CONFIG_PATH = "configs/cortex.runtime.prod.yaml"
```

### 6.3 runtime config 中的引用规则

统一 runtime config 支持以下引用方式：

- `env:NAME`：从环境变量读取
- `file:relative/or/absolute/path`：读取文件内容
- `path:relative/or/absolute/path`：解析成绝对路径
- `literal:value`：直接使用字面量

例如：

```yaml
parse:
  engines:
    crawl4ai:
      base_directory_ref: path:../.data/crawl4ai/local
    jina_reader:
      api_key_ref: env:JINA_API_KEY
knowledge:
  cognee:
    vector_db:
      vector_db_url_ref: env:COGNEE_VECTOR_DB_URL
```

### 6.4 Parse 引擎与 Knowledge Provider

当前 runtime config 已内置以下槽位：

- Parse engines
  - `crawl4ai`
  - `jina_reader`
  - `llama_parse`
  - `markitdown`
  - `docling`
- Knowledge provider
  - `cognee`

内置 parse scene profile 位于：

- `packages/parse/src/cortex_parse/profiles/crawl4ai_balanced.yaml`
- `packages/parse/src/cortex_parse/profiles/crawl4ai_deep_web.yaml`
- `packages/parse/src/cortex_parse/profiles/crawl4ai_authenticated_web.yaml`
- `packages/parse/src/cortex_parse/profiles/jina_reader_balanced.yaml`
- `packages/parse/src/cortex_parse/profiles/jina_reader_fast_extract.yaml`
- `packages/parse/src/cortex_parse/profiles/llama_parse_document_fidelity.yaml`
- `packages/parse/src/cortex_parse/profiles/markitdown_lightweight.yaml`
- `packages/parse/src/cortex_parse/profiles/docling_document_ai.yaml`

其中 `crawl4ai` 建议始终通过 `parse.engines.crawl4ai.base_directory_ref` 统一指定工作目录，把缓存、日志、数据库和下载目录收敛到仓库内 `.data/crawl4ai/<env>`。这样可以避免默认落到用户 Home 目录后出现权限漂移，也更方便容器化和环境迁移。

如果要启用 `crawl4ai` 的真实浏览器抓取能力，还需要部署环境本身允许 Playwright 创建子进程与命名管道；否则 `jina_reader`、`markitdown`、`docling` 这类非浏览器引擎仍可正常工作，但 `crawl4ai` 会在浏览器驱动启动阶段失败。

## 7. 权限模型

### 7.0 鉴权模式与 token 来源

当前实现支持 4 种模式，但 token 来源并不相同：

| 模式 | Cortex 如何验 token | token 从哪里来 | 需要哪些密钥 / 凭据 |
| --- | --- | --- | --- |
| `dev` | 解析 `dev:` payload | 本地手工构造 | 无 |
| `jwt` | 使用 `CORTEX_AUTH_JWT_SHARED_SECRET` 校验共享密钥 JWT | 外部系统自签发 | `CORTEX_AUTH_JWT_SHARED_SECRET` |
| `introspection` | 调用外部 introspection 端点验 opaque token | 必须由外部授权服务器签发 | `CORTEX_AUTH_INTROSPECTION_URL`、`...CLIENT_ID`、`...CLIENT_SECRET` |
| `hybrid` | 先尝试 JWT，再回退 introspection | JWT 与 opaque token 都来自外部授权体系 | `CORTEX_AUTH_JWT_SHARED_SECRET` + introspection 客户端凭据 |

有一个关键边界：

- Cortex 本质上仍然是资源服务器，不默认充当完整的 OAuth 2.0 / OIDC 授权服务器。
- Cortex 当前不再暴露内建 token 签发 API，令牌生成仍由调用方本地脚本、CI 密钥注入或外部 IdP 负责。
- 真正的浏览器登录、授权码流程、用户目录、MFA、账号生命周期，仍建议交给外部 IdP。

### 7.1 功能权限 scope

当前 API 使用的核心 scope：

| Scope | 说明 |
| --- | --- |
| `health:read` | 读取健康检查 |
| `parse:read` | 查询 parse 引擎、profile、结果 |
| `parse:write` | 发起同步/异步解析 |
| `storage:write` | 创建与完成上传 |
| `storage:read` | 读取对象元数据 |
| `storage:download` | 生成下载 URL |
| `knowledge:read` | 查询数据集与搜索 |
| `knowledge:write` | 创建数据集、提交 Add/Cognify/Memify |
| `jobs:read` | 查询作业状态与事件 |
| `jobs:cancel` | 取消作业 |

### 7.2 数据权限

除 scope 之外，Cortex 还会对资源做二次授权判断：

- 租户边界
- `access_level`
  - `tenant_private`
  - `tenant_shared`
- 资源 owner
- 角色绑定
- 资源策略中的 allow / deny actor、role、标签、用途约束

### 7.3 Swagger / 本地调试如何拿 token

如果你通过本地 Swagger UI (`/docs`) 调试受保护接口，请使用右上角的 `Authorize` 按钮，并填入一个已有的 bearer token。

- `dev` 模式：可直接使用下文 `9.1` 的本地脚本生成 `Bearer dev:...`
- `jwt` / `hybrid` 模式：请填入外部系统签发的 JWT
- `introspection` 模式：请填入外部授权服务器签发的 opaque token

Swagger UI 会自动补上 `Authorization: Bearer ...` 请求头，不需要再手工填写单独的 header 参数。

## 8. 本地启动

### 8.0 推荐先使用仓库自带 uv wrapper

为了把 uv 的托管 Python 固定在仓库内，并避免再次落到用户目录的全局安装路径，建议优先使用以下 wrapper，而不是直接裸跑 `uv`：

当前仓库的 `.python-version` 已固定为 `3.12.12`，wrapper 会把该版本的托管 Python 安装到仓库内的 `.uv-python/`，并把项目虚拟环境固定到 `.venv/`。

不要在运行这些 wrapper 之前手工执行：

- Git Bash: `source .venv/Scripts/activate`
- PowerShell: `.\.venv\Scripts\Activate.ps1`

原因很简单：这些 wrapper 自己负责检查和修复 `.venv`。如果你先激活了目标 `.venv`，Windows 很容易把 `.venv\Scripts` 锁住，后续 `uv sync` / `repair-venv` 就会报 `os error 32`。

同样地，如果你正在运行：

- `cortex-api`
- `cortex-parse-worker`
- `cortex-knowledge-worker`
- 任何仍然绑定到仓库 `.venv` 的 `python` / `uv` 进程

也请先停掉它们，再执行 `repair-venv`。

PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 sync --all-packages --all-groups
```

Git Bash：

```bash
bash scripts/dev/uv.sh sync --all-packages --all-groups
```

这两个 wrapper 会统一注入：

- `UV_PYTHON_INSTALL_DIR=<repo>/.uv-python`
- `UV_PROJECT_ENVIRONMENT=<repo>/.venv`

请不要在 Git Bash 里直接粘贴 PowerShell 语法，例如：

```powershell
while ($true) { uv run --package cortex-worker-parse cortex-parse-worker }
```

这类命令只适用于 PowerShell；在 Git Bash 中请使用上面的 `bash scripts/dev/*.sh` 启动脚本。

如果你怀疑 `.venv` 已损坏，可直接执行：

PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\repair-venv.ps1
```

强制重建：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\repair-venv.ps1 -ForceRecreate
```

Git Bash：

```bash
bash scripts/dev/repair-venv.sh
```

强制重建：

```bash
bash scripts/dev/repair-venv.sh --force-recreate
```

### 8.1 最小启动模式

适用于先验证 API 控制面、SQLite、URL 解析和基础鉴权，不依赖完整 Docker 栈。

1. 准备配置

```powershell
Copy-Item .env.example .env
```

2. 安装依赖并建立规范 `.venv`

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\bootstrap.ps1
```

Git Bash：

```bash
bash scripts/dev/uv.sh sync --all-packages --all-groups
```

或直接裸跑：

```powershell
uv sync --all-packages --all-groups
```

3. 执行数据库迁移

```powershell
uv run --package cortex-db cortex-db-migrate upgrade head
```

4. 启动 API

```powershell
uv run --package cortex-api cortex-api
```

5. 在新终端启动 Worker

注意：当前 Worker 入口是单次 `run_once()` 轮询，不是内建常驻进程。请优先使用仓库自带启动脚本，它们会先检查/修复 `.venv`，然后直接运行 `.venv` 内生成的 worker 可执行文件，避免在死循环里反复触发 `uv run`。

Parse Worker，PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\run-parse-worker.ps1
```

Parse Worker，Git Bash：

```bash
bash scripts/dev/run-parse-worker.sh
```

Knowledge Worker，PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\run-knowledge-worker.ps1
```

Knowledge Worker，Git Bash：

```bash
bash scripts/dev/run-knowledge-worker.sh
```

单次执行模式：

PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\run-parse-worker.ps1 -Once
powershell -ExecutionPolicy Bypass -File scripts\dev\run-knowledge-worker.ps1 -Once
```

Git Bash：

```bash
bash scripts/dev/run-parse-worker.sh --once
bash scripts/dev/run-knowledge-worker.sh --once
```

启动后访问：

- Swagger UI: `http://127.0.0.1:8080/docs`
- ReDoc: `http://127.0.0.1:8080/redoc`
- OpenAPI JSON: `http://127.0.0.1:8080/openapi.json`

### 8.2 完整本地依赖栈模式

适用于验证 PostgreSQL、MinIO、OTel、Jaeger、Prometheus、Grafana 与 runtime-stack 集成测试。

1. 启动依赖栈

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 up
```

2. 查看栈状态

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 ps
```

3. 查看日志

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 logs -Follow
```

4. 关闭依赖栈

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 down
```

默认暴露端口：

| 组件 | 地址 |
| --- | --- |
| PostgreSQL | `127.0.0.1:5432` |
| MinIO API | `http://127.0.0.1:9000` |
| MinIO Console | `http://127.0.0.1:9001` |
| Redis | `127.0.0.1:6379` |
| Jaeger | `http://127.0.0.1:16686` |
| OTel Collector Health | `http://127.0.0.1:13133` |
| Collector Prometheus Exporter | `http://127.0.0.1:8889/metrics` |
| Prometheus | `http://127.0.0.1:9090` |
| Grafana | `http://127.0.0.1:3000` |

## 9. 快速验证样例

以下示例默认：

- API 地址为 `http://127.0.0.1:8080`
- 认证模式为 `dev`
- 已完成迁移并启动 API

### 9.1 生成 dev token

```bash
python - <<'PY'
import base64, json
claims = {
    "sub": "alice",
    "tenant_id": "tenant_demo",
    "actor_id": "alice",
    "actor_ref": "alice@example.com",
    "scope": "health:read parse:read parse:write storage:write storage:read storage:download knowledge:read knowledge:write jobs:read jobs:cancel"
}
payload = base64.urlsafe_b64encode(
    json.dumps(claims, separators=(",", ":")).encode("utf-8")
).decode("ascii").rstrip("=")
print(f"Bearer dev:{payload}")
PY
```

把输出保存到 `TOKEN` 环境变量后，即可调用 API。

### 9.2 健康检查

```bash
curl -H "Authorization: $TOKEN" http://127.0.0.1:8080/v1/health/live
curl -H "Authorization: $TOKEN" http://127.0.0.1:8080/v1/health/ready
curl http://127.0.0.1:8080/metrics
```

### 9.3 同步 Parse

```bash
curl -X POST http://127.0.0.1:8080/v1/parse/sync \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": [
      "https://docs.cognee.ai/core-concepts/overview",
      "s3://demo-bucket/manuals/architecture.pdf"
    ],
    "engine_id": "auto"
  }'
```

返回结果中可看到：

- `results[0].document.markdown`
- `results[0].document.metadata`
- `results[0].diagnostics.selected_engine_key`
- `results[0].job_id`
- `x-request-id`
- `x-trace-id`

### 9.4 异步 Parse 作业

提交作业：

```bash
curl -X POST http://127.0.0.1:8080/v1/parse/jobs \
  -H "Authorization: $TOKEN" \
  -H "Idempotency-Key: parse-demo-001" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": [
      "https://docs.cognee.ai/core-concepts/overview",
      "s3://demo-bucket/manuals/architecture.pdf"
    ],
    "engine_id": "auto",
    "priority": 5
  }'
```

提交响应中的 `jobs[0].job_id` 就是每个来源对应的异步作业 ID。轮询结果：

```bash
curl -H "Authorization: $TOKEN" \
  http://127.0.0.1:8080/v1/parse/jobs/<job_id>/result
```

查询作业轨迹：

```bash
curl -H "Authorization: $TOKEN" \
  http://127.0.0.1:8080/v1/jobs/<job_id>/events
```

### 9.5 Storage 上传与下载

1. 创建上传会话

```bash
curl -X POST http://127.0.0.1:8080/v1/storage/uploads \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "sample.md",
    "metadata": {"source": "demo"},
    "tags": ["docs"],
    "access_policy": {"access_level": "tenant_shared"}
  }'
```

默认单文件上传可以省略 `content_type` 和 `size_bytes`。Cortex 会优先从 `filename` 推断 MIME type；如果上传前不知道文件大小，也会默认先走 single-part。只有当客户端已经知道文件较大，希望 Cortex 直接初始化 multipart 时，才需要提供 `size_bytes`。

2. 使用响应中的 `single_part.url` 执行 `PUT` 上传；如果是 `multipart`，则依次调用返回的 `multipart_parts`

3. 完成上传

```bash
curl -X POST http://127.0.0.1:8080/v1/storage/uploads/<upload_id>/complete \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

`complete` 这一步需要保留，不能省掉。原因是文件内容是直接上传到对象存储，不经过 Cortex API 数据面；Cortex 仍然需要在这一步确认对象已经可见、拉取对象存储返回的最终元数据，并提交对象版本记录。

4. 获取对象和下载 URL

```bash
curl -H "Authorization: $TOKEN" \
  http://127.0.0.1:8080/v1/storage/objects/<object_id>

curl -H "Authorization: $TOKEN" \
  "http://127.0.0.1:8080/v1/storage/objects/<object_id>/download-url?ttl_seconds=300&disposition=attachment"
```

### 9.6 Knowledge 数据集、Add、Search

创建数据集：

```bash
curl -X POST http://127.0.0.1:8080/v1/knowledge/datasets \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_key": "product_docs",
    "display_name": "Product Docs",
    "description": "Primary product knowledge base.",
    "tags": ["docs", "product"],
    "metadata": {"domain": "product"},
    "access_policy": {"access_level": "tenant_shared"}
  }'
```

提交 Add 作业：

```bash
curl -X POST http://127.0.0.1:8080/v1/knowledge/add/jobs \
  -H "Authorization: $TOKEN" \
  -H "Idempotency-Key: add-demo-001" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "<dataset_id>",
    "inputs": [
      {"input_type": "object_id", "object_id": "<object_id>", "label": "Uploaded object"},
      {"input_type": "document_id", "document_id": "<document_id>", "label": "Parsed document"}
    ]
  }'
```

执行 Search：

```bash
curl -X POST http://127.0.0.1:8080/v1/knowledge/search \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "What does the guide say about Cortex workflows?",
    "dataset_ids": ["<dataset_id>"],
    "search_type": "GRAPH_COMPLETION",
    "include_graph_paths": true
  }'
```

## 10. 测试与校验

### 10.1 全量校验

```powershell
uv run --all-packages --all-groups python scripts/ci/check.py
```

该命令会依次执行：

- YAML / OpenAPI 校验
- Ruff
- Pyright
- pytest

### 10.2 常用定向校验

OpenAPI 与 YAML：

```powershell
uv run --all-packages --all-groups python scripts/ci/validate_yaml.py
```

主链路 E2E：

```powershell
uv run --all-packages --group test pytest tests/integration/test_api_e2e.py
```

运行时栈验证：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\check-runtime-stack.ps1
```

可观测性 live probe：

```powershell
$env:CORTEX_RUNTIME_STACK = "1"
uv run --all-packages --group test pytest tests/integration/test_runtime_observability_stack.py
```

### 10.3 已覆盖的测试层级

| 测试层级 | 说明 |
| --- | --- |
| `tests/contract` | OpenAPI 合同与 DTO 结构 |
| `tests/unit` | 纯服务逻辑、runtime config、auth、storage client 等 |
| `tests/integration` | API、Worker、DB、runtime stack、observability、主链路 E2E |

## 11. 可观测性与效果验证

### 11.1 本地观测入口

- Jaeger：`http://127.0.0.1:16686`
- Prometheus：`http://127.0.0.1:9090`
- Grafana：`http://127.0.0.1:3000`
- API Metrics：`http://127.0.0.1:8080/metrics`
- Collector Metrics：`http://127.0.0.1:8889/metrics`

### 11.2 验证建议

1. 先调用一次 `/v1/parse/sync` 或提交流水线作业
2. 在 Jaeger 中查找 `cortex-api`
3. 在 Prometheus 中查询：

```text
cortex_parse_requests_total
up{job="otel-collector"}
```

4. 在 Grafana 中查看 Prometheus 与 Jaeger 数据源是否健康

### 11.3 本仓库已具备的可观测性保证

- API 响应头携带 `x-request-id` 和 `x-trace-id`
- `/metrics` 暴露 Prometheus 文本格式指标
- `scripts/dev/live_observability_probe.py` 会自动验证：
  - Collector 健康检查
  - Jaeger trace 可见
  - Collector Prometheus 导出中可见 `cortex_parse_requests`
  - Prometheus 中指标名可发现

## 12. 线上部署方式

## 12.1 方案一：虚拟机 / 裸机 / ECS 进程部署

这是当前仓库最直接、最厂商中立的部署方式。

推荐外部依赖：

| 组件 | 推荐实现 |
| --- | --- |
| 关系库 | PostgreSQL |
| 对象存储 | AWS S3 / MinIO / 其他 S3 兼容实现 |
| 遥测 | OpenTelemetry Collector |
| Trace | Jaeger |
| Metrics | Prometheus |
| Dashboard | Grafana |
| 图库/向量库 | 由 `configs/cortex.runtime.prod.yaml` 中的 Cognee 配置决定 |

部署步骤：

1. 准备代码与配置

```bash
uv sync --all-packages --all-groups --frozen
export CORTEX_ENV=prod
export CORTEX_DB_DSN='postgresql+asyncpg://...'
export CORTEX_S3_ENDPOINT='https://s3.example.com'
export CORTEX_RUNTIME_CONFIG_PATH='configs/cortex.runtime.prod.yaml'
```

2. 执行迁移

```bash
uv run --package cortex-db cortex-db-migrate upgrade head
```

3. 启动 API

```bash
uv run --package cortex-api cortex-api
```

4. 启动 Worker

```bash
while true; do
  uv run --package cortex-worker-parse cortex-parse-worker
  sleep 1
done
```

```bash
while true; do
  uv run --package cortex-worker-knowledge cortex-knowledge-worker
  sleep 1
done
```

5. 把 API、Parse Worker、Knowledge Worker 分别交给 systemd、supervisord、PM2、Nomad 或任意进程守护器管理

推荐 systemd 拆分：

- `cortex-api.service`
- `cortex-parse-worker.service`
- `cortex-knowledge-worker.service`

健康检查与探针：

- liveness: `/v1/health/live`
- readiness: `/v1/health/ready`
- metrics: `/metrics`

## 12.2 方案二：容器平台 / Kubernetes / 云原生 PaaS

当前仓库已经明确了容器化后的入口命令，但尚未内置生产 Dockerfile。若部署到 Kubernetes、阿里云 SAE、AWS ECS/Fargate、Azure Container Apps、Render、Fly.io 等平台，建议保持以下拆分：

- `api`：对外提供 REST API
- `parse-worker`：消费 Parse 作业
- `knowledge-worker`：消费 Knowledge 作业
- `otel-collector`：独立 sidecar 或独立 Deployment

容器入口命令建议直接使用当前 workspace 脚本：

| 组件 | 启动命令 |
| --- | --- |
| API | `uv run --package cortex-api cortex-api` |
| Parse Worker | `uv run --package cortex-worker-parse cortex-parse-worker` |
| Knowledge Worker | `uv run --package cortex-worker-knowledge cortex-knowledge-worker` |

Kubernetes 推荐映射：

- `ConfigMap`：`configs/cortex.runtime.prod.yaml`
- `Secret`：`.env` 中的敏感变量
- `Deployment`：API、Parse Worker、Knowledge Worker 各自独立
- `Service` / `Ingress`：仅 API 对外暴露
- `HorizontalPodAutoscaler`：根据 CPU、内存或请求速率扩缩容
- `ServiceMonitor` / `PodMonitor`：抓取 `/metrics`

如果使用云原生对象存储与数据库：

- S3 兼容对象存储直接替换 `CORTEX_S3_ENDPOINT`
- PostgreSQL 直接替换 `CORTEX_DB_DSN`
- OTel Collector 改为云上托管 Collector 或独立 Deployment
- Cognee 的图库 / 向量库通过 `configs/cortex.runtime.prod.yaml` 与 Secret 注入切换

## 13. 生产部署建议

- API 与 Worker 分开扩容，不要混布在同一进程中
- 生产环境优先使用 PostgreSQL，不建议继续使用 SQLite
- 对象存储优先使用云厂商托管 S3 兼容服务
- OTel Collector 建议独立部署，避免与 API 共享故障域
- 把 `configs/cortex.runtime.prod.yaml` 纳入配置发布流程，避免 provider 参数散落在环境变量与代码中
- 若需要蓝绿、金丝雀、A/B 测试，优先以 API Deployment 和 Worker Deployment 为粒度进行发布切换，并通过 telemetry 标签区分版本

## 14. 常用命令清单

安装依赖：

```powershell
uv sync --all-packages --all-groups
```

推荐：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 sync --all-packages --all-groups
```

迁移数据库：

```powershell
uv run --package cortex-db cortex-db-migrate upgrade head
```

启动 API：

```powershell
uv run --package cortex-api cortex-api
```

启动 Parse Worker 单次轮询：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\run-parse-worker.ps1 -Once
```

启动 Knowledge Worker 单次轮询：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\run-knowledge-worker.ps1 -Once
```

全量校验：

```powershell
uv run --all-packages --all-groups python scripts/ci/check.py
```

启动本地依赖栈：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 up
```

## 15. 设计文档索引

| 文档 | 说明 |
| --- | --- |
| `specs/cortex-api.yaml` | OpenAPI 3.1 合同 |
| `specs/cortex-dfd.md` | 数据流设计 |
| `specs/cortex-prd.md` | 产品文档 |
| `specs/cortex-schema.md` | Schema 设计 |
| `specs/cortex-tech.md` | 技术设计与代码模型 |
| `specs/cortex-init.sql` | 初始化 SQL 基线 |
| `specs/cortex-tasks.md` | 开发任务时间轴 |
| `specs/cortex-log.md` | 问题与修复日志 |

## 16. 当前实现说明

- REST 契约、核心服务、Worker、集成测试和 OpenTelemetry 联调已经到位
- 本地依赖栈脚本 `scripts/dev/stack.ps1` 已可作为标准入口
- Worker 当前是单次轮询模型，适合由 loop 或外部 supervisor 托管
- 运行时配置已经集中到 `configs/cortex.runtime*.yaml`
- 线上部署推荐按 API / Parse Worker / Knowledge Worker 拆分为三个独立运行单元
## 17. Crawl4AI 浏览器自动化与生产部署兜底

本仓库已经把 Crawl4AI / Playwright 的准备流程收敛成统一自动化，不再依赖“先手工跑一次浏览器安装”这种脆弱前提。

### 17.1 统一准备入口

无论本地、systemd、容器还是 CI/CD，统一使用：

```bash
python scripts/runtime/prepare_crawl4ai_runtime.py --json
```

常用模式：

```bash
# 只解析运行时配置、创建 repo-local 目录、输出结果，不主动探测浏览器
python scripts/runtime/prepare_crawl4ai_runtime.py --no-probe --json

# 探测浏览器；若缺失则尝试自动安装
python scripts/runtime/prepare_crawl4ai_runtime.py --install-if-missing --json

# Linux 镜像构建阶段推荐：安装浏览器并补齐系统依赖
python scripts/runtime/prepare_crawl4ai_runtime.py --install-if-missing --with-deps --no-probe
```

输出约定：

- `status=ok`：运行时目录与浏览器路径已准备完成
- `status=error`：返回结构化 `error_code` 与 `hints`

当前已内置的错误分类：

- `browser_binary_missing`
- `host_process_policy_blocked`
- `host_browser_dependencies_missing`
- `browser_download_tls_failed`
- `playwright_runtime_preflight_failed`

### 17.2 生产入口脚本

仓库新增了 Linux / 容器可直接复用的正式入口：

- `scripts/runtime/start-api.sh`
- `scripts/runtime/start-parse-worker.sh`
- `scripts/runtime/start-knowledge-worker.sh`

它们的行为约定如下：

1. API 与 Parse Worker 启动前先执行 Crawl4AI 运行时准备。
2. Knowledge Worker 不依赖浏览器，仅负责循环消费知识作业。
3. Parse / Knowledge Worker 以“单次轮询 + 外层守护循环”运行：
   - 正常空轮询或成功处理后继续下一轮
   - 若进程非零退出，则容器 / supervisor 直接接管重启，而不是静默死循环吞错

可调环境变量：

| 变量 | 默认值 | 作用 |
| --- | --- | --- |
| `CORTEX_RUNTIME_CONFIG_PATH` | `configs/cortex.runtime.local.yaml` | 选择统一 runtime overlay |
| `CORTEX_CRAWL4AI_INSTALL_IF_MISSING` | `0` | 启动前发现浏览器缺失时是否自动安装 |
| `CORTEX_CRAWL4AI_WITH_DEPS` | `0` | 安装浏览器时是否追加 `--with-deps` |
| `CORTEX_CRAWL4AI_SKIP_PROBE` | `0` | 是否跳过启动前浏览器探针 |
| `CORTEX_PARSE_WORKER_LOOP_SLEEP_SECONDS` | `1` | Parse Worker 两次轮询之间的休眠秒数 |
| `CORTEX_KNOWLEDGE_WORKER_LOOP_SLEEP_SECONDS` | `1` | Knowledge Worker 两次轮询之间的休眠秒数 |

推荐生产约定：

- 镜像构建阶段：`CORTEX_CRAWL4AI_INSTALL_IF_MISSING=1`
- 运行阶段：`CORTEX_CRAWL4AI_INSTALL_IF_MISSING=0`，只保留探针

这样可以把“浏览器没装好”前移到 build / deploy，而不是等线上第一个请求才暴雷。

### 17.3 内置 Dockerfile

仓库现已提供正式 `Dockerfile`，包含 4 个 target：

- `api`
- `parse-worker`
- `parse-worker-docling`
- `knowledge-worker`

构建示例：

```bash
docker build --target api -t cortex-api:local .
docker build --target parse-worker -t cortex-parse-worker:local .
docker build --target parse-worker-docling -t cortex-parse-worker-docling:local .
docker build --target knowledge-worker -t cortex-knowledge-worker:local .
```

这个 Dockerfile 在构建阶段会：

1. 按镜像 target 精确执行 `uv sync --package ... --no-default-groups --frozen`
2. `api` 与默认 `parse-worker` 只安装默认解析引擎集，不安装 `docling` / `torch`
3. `parse-worker-docling` 通过 `cortex-worker-parse[docling]` 单独安装 Docling、Torch、OCR 与完整文档转换依赖
4. `knowledge-worker` 独立安装 `cortex-worker-knowledge`，用于 Cognee / Knowledge 作业
5. API 与 Parse Worker 基于 Playwright 官方 Python 镜像，容器内浏览器路径统一为 `/ms-playwright`

因此，`crawl4ai` 最常见的 “Executable doesn't exist ... chrome.exe” 这类问题会由容器镜像的 Playwright 基线兜住；`docling -> torch` 这类超大依赖下载失败，也不会再拖垮默认 API / Parse Worker 镜像构建。

基础镜像策略：

- `api` / `parse-worker` / `parse-worker-docling`：默认使用 `mcr.microsoft.com/playwright/python:v1.58.0-noble`
- `knowledge-worker`：默认使用 `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`
- `uv`：从 `ghcr.io/astral-sh/uv:0.7.22` 复制 `/uv` 和 `/uvx`，不在镜像构建阶段额外执行 `pip install uv`
- 如需改为企业内网镜像，覆盖 `CORTEX_PYTHON_BASE_IMAGE`、`CORTEX_UV_IMAGE`、`CORTEX_PLAYWRIGHT_PYTHON_BASE_IMAGE`

运行示例：

```bash
docker run --rm \
  --env-file .env \
  -e CORTEX_RUNTIME_CONFIG_PATH=configs/cortex.runtime.prod.yaml \
  -p 8080:8080 \
  cortex-api:local
```

```bash
docker run --rm \
  --env-file .env \
  -e CORTEX_RUNTIME_CONFIG_PATH=configs/cortex.runtime.prod.yaml \
  cortex-parse-worker:local
```

```bash
docker run --rm \
  --env-file .env \
  -e CORTEX_RUNTIME_CONFIG_PATH=configs/cortex.runtime.prod.yaml \
  cortex-parse-worker-docling:local
```

```bash
docker run --rm \
  --env-file .env \
  -e CORTEX_RUNTIME_CONFIG_PATH=configs/cortex.runtime.prod.yaml \
  cortex-knowledge-worker:local
```

### 17.4 对当前问题的直接结论

如果你看到的是：

- `Executable doesn't exist ... chrome.exe`：说明浏览器二进制缺失，走预装即可解决
- `spawn EPERM` / `WinError 5` / `拒绝访问`：说明不是 Cortex 代码逻辑错，而是当前宿主机阻止了 Playwright / Node 子进程或命名管道

后一类场景最稳妥的做法不是继续在受限宿主机硬扛，而是：

1. 在 Linux 容器镜像中预装浏览器
2. 使用 `scripts/runtime/start-api.sh` 与 `scripts/runtime/start-parse-worker.sh`
3. 让运行阶段只做探针，不再执行现场下载

这也是后续生产上线最推荐的方式。
