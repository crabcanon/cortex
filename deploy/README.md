# Cortex 构建与上线手册

本文档定义 Cortex 从代码提交到生产上线的标准路径。目标是让 API、轻量 Worker、重型 Worker、文档站点和运行时配置都能独立构建、独立扩缩、可回滚。

## 1. 发布对象

| 对象 | 镜像 / 目录 | 说明 |
| --- | --- | --- |
| API | `ghcr.io/crabcanon/cortex-api:<tag>` | FastAPI REST 入口、Swagger UI、数据库迁移镜像来源 |
| Parse Worker | `ghcr.io/crabcanon/cortex-parse-worker:<tag>` | Crawl4AI、Jina Reader、LlamaParse、MarkItDown |
| Parse Worker Docling | `ghcr.io/crabcanon/cortex-parse-worker-docling:<tag>` | Docling/OCR 重型文档解析 |
| Knowledge Worker | `ghcr.io/crabcanon/cortex-knowledge-worker:<tag>` | Cognee/Kuzu/LanceDB 知识构建 |
| Evaluation Worker | `ghcr.io/crabcanon/cortex-evaluation-worker:<tag>` | 轻量评测引擎适配 |
| Evaluation Runtime Worker | `ghcr.io/crabcanon/cortex-evaluation-worker-runtime:<tag>` | DeepEval、EvalScope SDK 重型评测运行时 |
| Synthesis Worker | `ghcr.io/crabcanon/cortex-synthesis-worker:<tag>` | 轻量数据合成适配 |
| Synthesis Runtime Worker | `ghcr.io/crabcanon/cortex-synthesis-worker-runtime:<tag>` | SDV、DeepEval Synthesizer 重型合成运行时 |
| Docs | `docs/` | Next/Fumadocs 官方文档站点，推荐部署到 Vercel |

## 2. GitHub Actions

### 2.1 质量检查

`.github/workflows/ci.yaml` 保持 Python workspace 的质量门禁：

```text
uv sync --all-packages --all-groups --frozen
uv run --all-packages --all-groups python scripts/ci/check.py
```

手工触发该 workflow 时可打开 `run_runtime_stack=true`，它会启动 Docker 依赖栈并运行集成测试。

### 2.2 Docker 镜像发布

`.github/workflows/docker-publish.yaml` 会在 `main`、`v*.*.*` tag 或手工触发时构建 Dockerfile 的所有 target，并发布到 GHCR。

手工触发建议：

1. 打开 GitHub Actions -> `Docker Images`。
2. `push_images=true`。
3. `include_heavy=true`，生产需要 Docling、DeepEval、SDV 时必须打开。
4. `runtime_config_path=configs/cortex.runtime.prod.yaml`。

镜像 tag 规则：

| 触发方式 | tag |
| --- | --- |
| 任意构建 | git short SHA，例如 `6f2b517` |
| `main` 分支 | `main`、`latest` |
| `v1.2.3` tag | `1.2.3`、`1.2` |

### 2.3 Docs 构建

`.github/workflows/docs-build.yaml` 会在 `docs/**` 变更时运行：

```text
bun install --frozen-lockfile
bun run types:check
bun run build
```

文档站点生产部署推荐使用 Vercel Dashboard：Root Directory 选择 `docs`，Build Command 使用 `bun run build`，Install Command 使用 `bun install --frozen-lockfile`。

## 3. 标准 Bash 发布入口

生产和 CI/CD 推荐统一使用 `scripts/deploy/release.sh`，它封装了构建、推送、迁移、启动和健康检查。

全量重型镜像本地构建：

```bash
bash scripts/deploy/release.sh build --tag local-heavy --heavy
```

全量重型镜像构建并推送到 GHCR：

```bash
docker login ghcr.io
bash scripts/deploy/release.sh publish --tag 2026.05.12 --heavy
```

生产服务器部署：

```bash
bash scripts/deploy/release.sh deploy --env-file .env.prod --heavy
```

同一台机器上完成构建、推送、部署：

```bash
bash scripts/deploy/release.sh build-publish-deploy --tag 2026.05.12 --heavy --env-file .env.prod
```

`release.sh` 会自动定位仓库根目录，所以可以从仓库内任意子目录执行。PowerShell 脚本保留给 Windows 开发机使用，但不是生产发布主路径。

## 4. 分步构建镜像

轻量镜像：

```bash
bash scripts/deploy/build-images.sh \
  --registry ghcr.io \
  --namespace crabcanon \
  --tag local-smoke
```

全量重型镜像：

```bash
bash scripts/deploy/build-images.sh \
  --registry ghcr.io \
  --namespace crabcanon \
  --tag local-heavy \
  --heavy
```

推送到镜像仓库：

```bash
docker login ghcr.io
bash scripts/deploy/build-images.sh --tag 2026.05.12 --heavy --push
```

Windows 开发机可选 PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\deploy\build-images.ps1 -Tag 2026.05.12 -Heavy -Push
```

## 5. Docker Compose 生产部署

### 5.1 准备服务器

推荐最低配置：

| 服务形态 | CPU | 内存 | 说明 |
| --- | ---: | ---: | --- |
| API + 轻量 Worker | 4 vCPU | 8 GB | 不跑 Docling/SDV |
| 全量单机 | 8 vCPU | 32 GB | 可跑 Docling、DeepEval、SDV |
| 生产推荐 | 多节点 | 按服务拆分 | API、Docling、Knowledge、Evaluation、Synthesis 独立扩缩 |

服务器需要安装 Docker Engine 和 Docker Compose Plugin。对象存储、Postgres、Redis、OTel 后端建议使用托管服务。

### 5.2 准备 env

```bash
cp .env.prod.example .env.prod
```

必须填写：

```text
CORTEX_DB_DSN=postgresql+asyncpg://...
CORTEX_QUEUE_URL=redis://...
CORTEX_S3_ENDPOINT=https://...
CORTEX_S3_BUCKET=...
CORTEX_S3_ACCESS_KEY=...
CORTEX_S3_SECRET_KEY=...
CORTEX_OTEL_EXPORTER_OTLP_ENDPOINT=https://...
CORTEX_AUTH_MODE=oidc
CORTEX_OIDC_ISSUER=https://...
CORTEX_AUTH_JWKS_URL=https://...
```

如需固定发布版本，把所有 `CORTEX_*_IMAGE` 从 `latest` 改成同一个 git SHA tag：

```text
CORTEX_API_IMAGE=ghcr.io/crabcanon/cortex-api:6f2b517
CORTEX_PARSE_WORKER_IMAGE=ghcr.io/crabcanon/cortex-parse-worker:6f2b517
...
```

### 5.3 启动

轻量生产：

```bash
bash scripts/deploy/release.sh deploy --env-file .env.prod
```

全量生产：

```bash
bash scripts/deploy/release.sh deploy --env-file .env.prod --heavy
```

如需跳过自动拉镜像：

```bash
bash scripts/deploy/release.sh deploy --env-file .env.prod --heavy --no-pull
```

脚本会按顺序执行：

1. `docker compose config --quiet`
2. `docker compose pull`
3. `cortex-db-migrate upgrade head`
4. `docker compose up -d`
5. 等待 `/v1/health/live`

### 5.4 回滚

1. 把 `.env.prod` 中所有 `CORTEX_*_IMAGE` 改回上一个 git SHA tag。
2. 执行：

```bash
bash scripts/deploy/release.sh deploy --env-file .env.prod --heavy --no-migrate
```

注意：数据库 migration 默认只向前。如果某次发布包含破坏性 schema 变化，需要先准备显式回滚脚本或新 migration 修复。

## 6. Railway 部署建议

Railway 适合用来跑 Cortex API 和 Worker，但不要让 Railway 对同一个仓库自动猜测 Docker target。推荐使用 GHCR 预构建镜像，然后在 Railway 中创建多个 Service：

| Railway Service | 镜像 | 是否公开 |
| --- | --- | --- |
| `cortex-api` | `ghcr.io/crabcanon/cortex-api:<tag>` | 是 |
| `cortex-parse-worker` | `ghcr.io/crabcanon/cortex-parse-worker:<tag>` | 否 |
| `cortex-parse-worker-docling` | `ghcr.io/crabcanon/cortex-parse-worker-docling:<tag>` | 否 |
| `cortex-knowledge-worker` | `ghcr.io/crabcanon/cortex-knowledge-worker:<tag>` | 否 |
| `cortex-evaluation-worker-runtime` | `ghcr.io/crabcanon/cortex-evaluation-worker-runtime:<tag>` | 否 |
| `cortex-synthesis-worker-runtime` | `ghcr.io/crabcanon/cortex-synthesis-worker-runtime:<tag>` | 否 |

依赖建议：

- Postgres：Railway Postgres 或外部 Neon/Supabase/RDS。
- Redis：Railway Redis 或 Upstash/Redis Cloud。
- S3：Cloudflare R2、AWS S3、MinIO Enterprise、Ceph RGW。
- OTel：Grafana Cloud OTLP、Honeycomb、Datadog 或自建 Collector。

API Service 配置：

```text
PORT=8080
CORTEX_HOST=0.0.0.0
CORTEX_PORT=8080
CORTEX_ENV=prod
CORTEX_DEPLOYMENT_ENV=prod
CORTEX_RUNTIME_CONFIG_PATH=configs/cortex.runtime.prod.yaml
```

Worker Service 不需要公网域名。Docling Worker 建议单独给更高内存并设置 `CORTEX_PARSE_WORKER_ENGINE_KEYS=docling`。

数据库迁移推荐三选一：

1. 发布前本地执行一次 `cortex-db-migrate upgrade head`，连接生产数据库。
2. 在 Railway 创建一次性 `cortex-migrate` Service，镜像使用 `cortex-api`，Command 设置为 `/app/.venv/bin/cortex-db-migrate upgrade head`。
3. 使用 Railway Deploy Hook 之前的 CI job 执行 migration。

## 7. 发布检查清单

上线前：

- `CI` workflow 通过。
- `Docker Images` workflow 通过，目标 tag 的所有镜像存在。
- `.env.prod` 不含 dev token、MinIO 默认密码、空 OIDC 配置。
- `CORTEX_AUTH_MODE=oidc` 或企业 JWT/Introspection 模式。
- `CORTEX_S3_AUTO_CREATE_BUCKET=false`，生产 bucket 由 IaC 或平台预创建。
- `CORTEX_OTEL_ENABLED=true`，OTLP endpoint 可从 API 与 Worker 访问。
- 重型能力需要 `--heavy` 或 Railway 对应 runtime Worker 已启动。

上线后：

```bash
curl -fsS https://api.example.com/v1/health/live
curl -fsS https://api.example.com/v1/openapi.json
```

在 Jaeger/Grafana 中确认：

- API 请求有 trace。
- Worker job 有 queue latency / run latency。
- Parse、Knowledge、Evaluation、Synthesis 失败率没有异常尖峰。

## 8. 常见问题

### Parse engine `docling` 不可用

确认生产已启动 `cortex-parse-worker-docling`，并且该 Service 的 `CORTEX_PARSE_WORKER_ENGINE_KEYS=docling`。

### Evaluation / Synthesis runtime 不可用

确认使用的是 runtime 镜像：

- `cortex-evaluation-worker-runtime`
- `cortex-synthesis-worker-runtime`

轻量 worker 不安装 DeepEval、EvalScope SDK、SDV 这类重依赖。

### Crawl4AI 浏览器缺失

API 和 Parse Worker 镜像基于 Playwright Python base image，默认在构建阶段预装浏览器。生产不要设置 `CORTEX_CRAWL4AI_INSTALL_IF_MISSING=1` 让首个请求现场下载浏览器。

### 需要蓝绿或金丝雀

推荐在负载均衡层或 Railway 多 Service 中实现：

1. 部署 `cortex-api-blue` 和 `cortex-api-green`，指向同一 Postgres/Redis/S3。
2. Worker 按队列或 engine key 分批切流。
3. 用 `CORTEX_DEPLOYMENT_ENV`、`CORTEX_CLUSTER`、`CORTEX_REGION` 和 OTel resource attributes 区分流量。
4. 指标稳定后切换公网域名。
