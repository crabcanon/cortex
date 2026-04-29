# TensorZero + Cortex 自适应 A/B Test 样例

这个样例演示一个接近真实业务的金融研究流水线：

1. 用 Cortex Parse API 对 20 个金融 / 宏观经济 URL 做多引擎解析。
2. 将不同 parse engine 产出的 Markdown 写入 Cortex Storage。
3. 将 Markdown 对象加载进 Cortex Knowledge，执行 Add + Cognify。
4. 对用户自然语言 query 执行 Knowledge Search，形成 RAG context。
5. 通过 TensorZero Gateway 在 OpenAI / Gemini / Kimi 三类模型服务之间做 adaptive A/B test。
6. 将 TensorZero 采集到的 inference / feedback 数据沉淀为评测集，并输出 parse、RAG、LLM、端到端效果报告。

## 技术栈

- Python 3.12
- uv
- FastAPI
- httpx
- TensorZero Gateway / UI
- Cortex API，本样例假设 Cortex Docker 集群已经在 `http://127.0.0.1:8080` 启动

TensorZero 参考官方文档中的 adaptive A/B test 模型：定义 function、candidate variants、优化 metric，然后对每次 inference 写入 feedback，TensorZero 会持续调整候选 variant 权重。

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
  src/tensorzero_cortex/
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
```

如果你只想先测一个供应商，可以先只填对应 key，并在 `tensorzero/tensorzero.toml.tpl` 或 `.env` 中把候选模型改成可用模型。

Parse 默认走同步模式。需要生产型长任务链路时，把 `.env` 中的 `PARSE_MODE` 改为 `async`，或在命令行传入 `--parse-mode async`。

Cortex Evaluation 默认也走同步模式。需要验证 worker-backed 评测链路时，把 `.env` 中的 `CORTEX_EVAL_MODE` 改为 `async`。如果希望每次运行都提交 Cortex Evaluation，把 `SUBMIT_CORTEX_EVAL` 改为 `true`。

## 2. 渲染 TensorZero 配置

TensorZero 的 gateway 启动前需要静态 `tensorzero.toml`。本样例用 `.env` 中的模型槽位渲染模板：

```powershell
uv run tensorzero-cortex render-config
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
  --parse-engines auto,crawl4ai,jina_reader,markitdown `
  --parse-mode sync `
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
  "query": "Summarize inflation, growth, and financial stability risks.",
  "max_urls": 3,
  "parse_engines": ["auto", "crawl4ai", "markitdown"],
  "parse_mode": "async",
  "submit_cortex_eval": false,
  "cortex_eval_mode": "sync",
  "run_knowledge_jobs": true
}
```

## 6. 输出物

每次运行会在 `artifacts/{run_id}` 下生成：

| 文件 | 说明 |
| --- | --- |
| `report.md` | 人类可读实验报告 |
| `report.json` | 结构化实验报告 |
| `tensorzero_eval_dataset.jsonl` | TensorZero 采集数据形成的评测集 |
| `raw_tensorzero_result.json` | TensorZero inference 原始响应 |
| `raw_search_result.json` | Cortex Knowledge Search 原始响应 |
| `parse/*.json` | 每个 URL + parse engine 的解析与 storage 上传结果 |

报告中的 scorecard 包含：

- `parse_markdown_quality`: Markdown 长度、结构和金融关键词覆盖的启发式分数
- `rag_context_quality`: Knowledge Search context 对目标关键词的覆盖度
- `llm_answer_quality`: TensorZero 选中模型输出的关键词、引用和置信度分数
- `rag_end_to_end_pass`: 端到端是否通过

这些指标也会通过 TensorZero `/feedback` 写回：

- `parse_markdown_quality`
- `rag_context_quality`
- `llm_answer_quality`
- `rag_end_to_end_pass`

TensorZero 会用 `rag_end_to_end_pass` 作为 adaptive A/B test 的优化 metric。

## 7. 内置 URL 类型

`src/tensorzero_cortex/finance_urls.py` 内置 20 个金融 / 宏观经济来源，覆盖：

- HTML 页面
- PDF 报告
- JSON API
- CSV 数据
- 政策声明、经济展望、CPI、FRED、SEC、BIS、IMF、World Bank、ECB、BOE、FDIC 等来源

如果某个公共站点临时限流或屏蔽爬虫，样例会记录该 URL + engine 的失败，并继续处理其他组合。

## 8. 注意事项

- TensorZero adaptive A/B test 依赖 Postgres 的 `pg_cron` 扩展；本样例使用专用 `tensorzero/postgres:17`，宿主端口默认是 `5434`。
- TensorZero observability 使用 ClickHouse；本样例会启动本地 ClickHouse。
- Kimi 通过 OpenAI-compatible provider 接入，默认 base URL 为 `https://api.moonshot.cn/v1`。
- Gemini 使用 Google AI Studio 的 OpenAI-compatible endpoint：`https://generativelanguage.googleapis.com/v1beta/openai`。
- Cortex Knowledge 的 Add / Cognify 是异步任务，文档多、模型慢或 OCR 重时会花较长时间。冒烟时先用 `--max-urls 1` 或 `--skip-knowledge-jobs`。
