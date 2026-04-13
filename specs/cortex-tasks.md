# Cortex Development Tasks

## 1. 维护规则

本文件是 Cortex 编码前的任务账本，后续每次开始新一轮开发前都必须先更新这里，再开始编码。

规则如下：

1. 任务按时间轴追加，新增批次一律追加到文件末尾，不重排历史批次。
2. 每个任务使用稳定 `Task ID`，格式为 `CTX-YYYYMMDD-NNN`。
3. 允许修改已有任务的 `Status`、`Notes`、`Completed At`，但不删除历史任务。
4. 若开发中拆分出新任务，应在当前批次后继续顺序追加。
5. 状态值统一使用：`planned`、`in_progress`、`blocked`、`done`、`cancelled`。

## 2. 批次时间轴

### Batch 2026-04-12 21:11:20 +08:00 | Implementation Bootstrap

目标：基于既有 specs 启动第一轮编码，先完成 `uv workspace` 骨架、共享基础设施、核心 API/Worker 主链路。

#### Phase A. Workspace & Toolchain

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260412-001 | 2026-04-12 21:11:20 +08:00 | P0 | workspace | 创建根级 `pyproject.toml`、`uv.lock`、`.python-version` 与 `uv workspace` members 清单 | - | done |
| CTX-20260412-002 | 2026-04-12 21:11:20 +08:00 | P0 | workspace | 建立 `apps/`、`workers/`、`packages/`、`tests/`、`scripts/` 的目录骨架与 `src/` 布局 | CTX-20260412-001 | done |
| CTX-20260412-003 | 2026-04-12 21:11:20 +08:00 | P0 | tooling | 配置 root dependency groups：`dev`、`lint`、`types`、`test`、`docs` | CTX-20260412-001 | done |
| CTX-20260412-004 | 2026-04-12 21:11:20 +08:00 | P0 | tooling | 增加 `ruff`、`pyright`、`pytest`、`pytest-asyncio`、`httpx` 的统一配置 | CTX-20260412-003 | done |
| CTX-20260412-005 | 2026-04-12 21:11:20 +08:00 | P1 | devops | 补充 `.env.example`、本地开发说明与基础启动脚本 | CTX-20260412-002 | done |

#### Phase B. Shared Foundation

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260412-006 | 2026-04-12 21:11:20 +08:00 | P0 | common | 实现 `cortex_common`：settings、时钟、ID、分页、异常、幂等 key、JSON helper | CTX-20260412-002 | done |
| CTX-20260412-007 | 2026-04-12 21:11:20 +08:00 | P0 | contracts | 实现 `cortex_contracts`：ProblemDetails、通用 header、枚举、分页、Job 基础 DTO | CTX-20260412-006 | done |
| CTX-20260412-008 | 2026-04-12 21:11:20 +08:00 | P0 | domain | 实现 `cortex_domain`：Object、Document、Dataset、Job、AuthorizationDecision 等核心领域模型 | CTX-20260412-006 | done |
| CTX-20260412-009 | 2026-04-12 21:11:20 +08:00 | P0 | observability | 实现 `cortex_observability`：OTel bootstrap、logger correlation、trace helper、metric facade | CTX-20260412-006 | done |

#### Phase C. Database & Persistence

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260412-010 | 2026-04-12 21:11:20 +08:00 | P0 | db | 实现 `cortex_db`：engine、session factory、metadata naming convention、base model | CTX-20260412-008 | done |
| CTX-20260412-011 | 2026-04-12 21:11:20 +08:00 | P0 | db | 按 `cortex-init.sql` 落地第一版 Alembic baseline migration | CTX-20260412-010 | done |
| CTX-20260412-012 | 2026-04-12 21:11:20 +08:00 | P0 | db | 实现 tenant、actor、object、document、dataset、job、authorization 的基础 repository | CTX-20260412-011 | done |
| CTX-20260412-013 | 2026-04-12 21:11:20 +08:00 | P1 | db | 增加 unit-of-work / transaction helper，统一 API 与 Worker 的事务边界 | CTX-20260412-012 | done |

#### Phase D. Auth & Governance

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260412-014 | 2026-04-12 21:11:20 +08:00 | P0 | auth | 实现 access token 解析、caller identity 装配、基础 JWT / introspection 适配接口 | CTX-20260412-007, CTX-20260412-010 | planned |
| CTX-20260412-015 | 2026-04-12 21:11:20 +08:00 | P0 | auth | 实现 scope / permission 校验器与功能权限依赖注入 | CTX-20260412-014 | planned |
| CTX-20260412-016 | 2026-04-12 21:11:20 +08:00 | P0 | auth | 实现资源级 RBAC + ABAC evaluator，支持 `access_level` 与 `access_policy_json` | CTX-20260412-012, CTX-20260412-015 | planned |
| CTX-20260412-017 | 2026-04-12 21:11:20 +08:00 | P1 | auth | 实现授权决策审计写入与 `decision_id` 关联 | CTX-20260412-016 | planned |

#### Phase E. API Bootstrap

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260412-018 | 2026-04-12 21:11:20 +08:00 | P0 | api | 搭建 `apps/api`：FastAPI app、lifespan、settings 装配、中间件、异常处理 | CTX-20260412-006, CTX-20260412-009, CTX-20260412-014 | planned |
| CTX-20260412-019 | 2026-04-12 21:11:20 +08:00 | P0 | api | 实现 `/v1/health/live`、`/v1/health/ready` | CTX-20260412-018 | planned |
| CTX-20260412-020 | 2026-04-12 21:11:20 +08:00 | P0 | api | 实现 Job 查询/取消接口骨架与统一 ProblemDetails 输出 | CTX-20260412-018, CTX-20260412-012 | planned |

#### Phase F. Storage

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260412-021 | 2026-04-12 21:11:20 +08:00 | P0 | storage | 实现 `cortex_storage`：S3 client facade、bucket resolver、checksum 服务 | CTX-20260412-006, CTX-20260412-010, CTX-20260412-009 | planned |
| CTX-20260412-022 | 2026-04-12 21:11:20 +08:00 | P0 | storage | 实现上传初始化 API 与 multipart / single-part 选择逻辑 | CTX-20260412-021, CTX-20260412-018 | planned |
| CTX-20260412-023 | 2026-04-12 21:11:20 +08:00 | P0 | storage | 实现上传完成 API、对象元数据持久化与版本记录 | CTX-20260412-022, CTX-20260412-012 | planned |
| CTX-20260412-024 | 2026-04-12 21:11:20 +08:00 | P0 | storage | 实现下载 URL 生成、TTL 控制与资源级授权校验 | CTX-20260412-016, CTX-20260412-023 | planned |

#### Phase G. Parse Foundation

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260412-025 | 2026-04-12 21:11:20 +08:00 | P0 | parse | 实现 `cortex_parse` 的核心模型：`ParseRequest`、`EngineAttempt`、`ParsedDocument`、`ParseDiagnostics` | CTX-20260412-007, CTX-20260412-008 | planned |
| CTX-20260412-026 | 2026-04-12 21:11:20 +08:00 | P0 | parse | 实现 parser engine protocol、router、engine registry、profile loader | CTX-20260412-025, CTX-20260412-009 | planned |
| CTX-20260412-027 | 2026-04-12 21:11:20 +08:00 | P0 | parse | 实现 Markdown / metadata / provenance normalization pipeline | CTX-20260412-026 | planned |
| CTX-20260412-028 | 2026-04-12 21:11:20 +08:00 | P0 | parse | 实现 parse run、attempt、artifact、document 持久化服务 | CTX-20260412-012, CTX-20260412-027, CTX-20260412-021 | planned |

#### Phase H. Parse Adapters

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260412-029 | 2026-04-12 21:11:20 +08:00 | P0 | parse-adapter | 实现 Crawl4AI adapter，覆盖 profile、advanced features 与 artifact 输出 | CTX-20260412-026 | planned |
| CTX-20260412-030 | 2026-04-12 21:11:20 +08:00 | P1 | parse-adapter | 实现 Jina Reader adapter，覆盖 markdown / metadata 快速提取 | CTX-20260412-026 | planned |
| CTX-20260412-031 | 2026-04-12 21:11:20 +08:00 | P1 | parse-adapter | 实现 LlamaParse adapter，覆盖高保真文档解析输出映射 | CTX-20260412-026 | planned |
| CTX-20260412-032 | 2026-04-12 21:11:20 +08:00 | P1 | parse-adapter | 实现 MarkItDown adapter，作为本地轻量文件 fallback | CTX-20260412-026 | planned |
| CTX-20260412-033 | 2026-04-12 21:11:20 +08:00 | P1 | parse-adapter | 实现 Docling adapter，覆盖结构化文档与 OCR 场景 | CTX-20260412-026 | planned |

#### Phase I. Parse API & Worker

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260412-034 | 2026-04-12 21:11:20 +08:00 | P0 | parse-api | 实现同步 Parse API、引擎/配置模板查询 API | CTX-20260412-018, CTX-20260412-028, CTX-20260412-029 | planned |
| CTX-20260412-035 | 2026-04-12 21:11:20 +08:00 | P0 | parse-worker | 建立 Parse Worker bootstrap、队列消费者、重试与超时边界 | CTX-20260412-002, CTX-20260412-028 | planned |
| CTX-20260412-036 | 2026-04-12 21:11:20 +08:00 | P0 | parse-worker | 实现异步 Parse job 提交、执行、状态回写与审计事件 | CTX-20260412-020, CTX-20260412-035 | planned |

#### Phase J. Knowledge / Cognee

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260412-037 | 2026-04-12 21:11:20 +08:00 | P0 | knowledge | 实现 `cortex_knowledge`：dataset service、Cognee runtime abstraction、run model | CTX-20260412-007, CTX-20260412-008, CTX-20260412-012 | planned |
| CTX-20260412-038 | 2026-04-12 21:11:20 +08:00 | P0 | knowledge | 实现 Dataset CRUD 与资源级授权 | CTX-20260412-037, CTX-20260412-016, CTX-20260412-018 | planned |
| CTX-20260412-039 | 2026-04-12 21:11:20 +08:00 | P0 | knowledge | 实现 Add 作业提交与执行 | CTX-20260412-037, CTX-20260412-035 | planned |
| CTX-20260412-040 | 2026-04-12 21:11:20 +08:00 | P1 | knowledge | 实现 Cognify 作业提交与执行 | CTX-20260412-039 | planned |
| CTX-20260412-041 | 2026-04-12 21:11:20 +08:00 | P1 | knowledge | 实现 Memify 作业提交与执行 | CTX-20260412-040 | planned |
| CTX-20260412-042 | 2026-04-12 21:11:20 +08:00 | P0 | knowledge | 实现 Search 服务、命中过滤、provenance 返回与授权二次校验 | CTX-20260412-038, CTX-20260412-039 | planned |
| CTX-20260412-043 | 2026-04-12 21:11:20 +08:00 | P0 | knowledge-worker | 建立 Knowledge Worker bootstrap、Add/Cognify/Memify 后台执行链路 | CTX-20260412-002, CTX-20260412-037 | planned |

#### Phase K. Quality & Delivery

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260412-044 | 2026-04-12 21:11:20 +08:00 | P0 | testing | 为 `common`、`auth`、`storage`、`parse`、`knowledge` 增加单元测试 | CTX-20260412-021, CTX-20260412-042 | planned |
| CTX-20260412-045 | 2026-04-12 21:11:20 +08:00 | P0 | testing | 增加 OpenAPI contract tests，校验 DTO 与 `cortex-api.yaml` 一致 | CTX-20260412-007, CTX-20260412-034, CTX-20260412-038 | planned |
| CTX-20260412-046 | 2026-04-12 21:11:20 +08:00 | P0 | testing | 增加集成测试：SQLite/PostgreSQL、S3 兼容存储、队列、Worker | CTX-20260412-036, CTX-20260412-043 | planned |
| CTX-20260412-047 | 2026-04-12 21:11:20 +08:00 | P1 | testing | 增加端到端主链路测试：upload -> parse -> add -> search | CTX-20260412-046 | planned |
| CTX-20260412-048 | 2026-04-12 21:11:20 +08:00 | P0 | ci | 建立 CI pipeline：`uv sync`、lint、types、tests、OpenAPI/YAML 校验 | CTX-20260412-004, CTX-20260412-045 | planned |
| CTX-20260412-049 | 2026-04-12 21:11:20 +08:00 | P1 | devops | 补充本地 compose / runbook，覆盖 DB、S3、queue、OTel Collector、Jaeger、Prometheus、Grafana | CTX-20260412-005, CTX-20260412-048 | planned |
