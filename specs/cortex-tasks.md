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
| CTX-20260412-014 | 2026-04-12 21:11:20 +08:00 | P0 | auth | 实现 access token 解析、caller identity 装配、基础 JWT / introspection 适配接口 | CTX-20260412-007, CTX-20260412-010 | done |
| CTX-20260412-015 | 2026-04-12 21:11:20 +08:00 | P0 | auth | 实现 scope / permission 校验器与功能权限依赖注入 | CTX-20260412-014 | done |
| CTX-20260412-016 | 2026-04-12 21:11:20 +08:00 | P0 | auth | 实现资源级 RBAC + ABAC evaluator，支持 `access_level` 与 `access_policy_json` | CTX-20260412-012, CTX-20260412-015 | done |
| CTX-20260412-017 | 2026-04-12 21:11:20 +08:00 | P1 | auth | 实现授权决策审计写入与 `decision_id` 关联 | CTX-20260412-016 | done |

#### Phase E. API Bootstrap

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260412-018 | 2026-04-12 21:11:20 +08:00 | P0 | api | 搭建 `apps/api`：FastAPI app、lifespan、settings 装配、中间件、异常处理 | CTX-20260412-006, CTX-20260412-009, CTX-20260412-014 | done |
| CTX-20260412-019 | 2026-04-12 21:11:20 +08:00 | P0 | api | 实现 `/v1/health/live`、`/v1/health/ready` | CTX-20260412-018 | done |
| CTX-20260412-020 | 2026-04-12 21:11:20 +08:00 | P0 | api | 实现 Job 查询/取消接口骨架与统一 ProblemDetails 输出 | CTX-20260412-018, CTX-20260412-012 | done |

#### Phase F. Storage

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260412-021 | 2026-04-12 21:11:20 +08:00 | P0 | storage | 实现 `cortex_storage`：S3 client facade、bucket resolver、checksum 服务 | CTX-20260412-006, CTX-20260412-010, CTX-20260412-009 | done |
| CTX-20260412-022 | 2026-04-12 21:11:20 +08:00 | P0 | storage | 实现上传初始化 API 与 multipart / single-part 选择逻辑 | CTX-20260412-021, CTX-20260412-018 | done |
| CTX-20260412-023 | 2026-04-12 21:11:20 +08:00 | P0 | storage | 实现上传完成 API、对象元数据持久化与版本记录 | CTX-20260412-022, CTX-20260412-012 | done |
| CTX-20260412-024 | 2026-04-12 21:11:20 +08:00 | P0 | storage | 实现下载 URL 生成、TTL 控制与资源级授权校验 | CTX-20260412-016, CTX-20260412-023 | done |

#### Phase G. Parse Foundation

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260412-025 | 2026-04-12 21:11:20 +08:00 | P0 | parse | 实现 `cortex_parse` 的核心模型：`ParseRequest`、`EngineAttempt`、`ParsedDocument`、`ParseDiagnostics` | CTX-20260412-007, CTX-20260412-008 | done |
| CTX-20260412-026 | 2026-04-12 21:11:20 +08:00 | P0 | parse | 实现 parser engine protocol、router、engine registry、profile loader | CTX-20260412-025, CTX-20260412-009 | done |
| CTX-20260412-027 | 2026-04-12 21:11:20 +08:00 | P0 | parse | 实现 Markdown / metadata / provenance normalization pipeline | CTX-20260412-026 | done |
| CTX-20260412-028 | 2026-04-12 21:11:20 +08:00 | P0 | parse | 实现 parse run、attempt、artifact、document 持久化服务 | CTX-20260412-012, CTX-20260412-027, CTX-20260412-021 | done |

#### Phase H. Parse Adapters

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260412-029 | 2026-04-12 21:11:20 +08:00 | P0 | parse-adapter | 实现 Crawl4AI adapter，覆盖 profile、advanced features 与 artifact 输出 | CTX-20260412-026 | in_progress |
| CTX-20260412-030 | 2026-04-12 21:11:20 +08:00 | P1 | parse-adapter | 实现 Jina Reader adapter，覆盖 markdown / metadata 快速提取 | CTX-20260412-026 | done |
| CTX-20260412-031 | 2026-04-12 21:11:20 +08:00 | P1 | parse-adapter | 实现 LlamaParse adapter，覆盖高保真文档解析输出映射 | CTX-20260412-026 | done |
| CTX-20260412-032 | 2026-04-12 21:11:20 +08:00 | P1 | parse-adapter | 实现 MarkItDown adapter，作为本地轻量文件 fallback | CTX-20260412-026 | done |
| CTX-20260412-033 | 2026-04-12 21:11:20 +08:00 | P1 | parse-adapter | 实现 Docling adapter，覆盖结构化文档与 OCR 场景 | CTX-20260412-026 | done |

#### Phase I. Parse API & Worker

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260412-034 | 2026-04-12 21:11:20 +08:00 | P0 | parse-api | 实现同步 Parse API、引擎/配置模板查询 API | CTX-20260412-018, CTX-20260412-028, CTX-20260412-029 | done |
| CTX-20260412-035 | 2026-04-12 21:11:20 +08:00 | P0 | parse-worker | 建立 Parse Worker bootstrap、队列消费者、重试与超时边界 | CTX-20260412-002, CTX-20260412-028 | done |
| CTX-20260412-036 | 2026-04-12 21:11:20 +08:00 | P0 | parse-worker | 实现异步 Parse job 提交、执行、状态回写与审计事件 | CTX-20260412-020, CTX-20260412-035 | done |

#### Phase J. Knowledge / Cognee

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260412-037 | 2026-04-12 21:11:20 +08:00 | P0 | knowledge | 实现 `cortex_knowledge`：dataset service、Cognee runtime abstraction、run model | CTX-20260412-007, CTX-20260412-008, CTX-20260412-012 | done |
| CTX-20260412-038 | 2026-04-12 21:11:20 +08:00 | P0 | knowledge | 实现 Dataset CRUD 与资源级授权 | CTX-20260412-037, CTX-20260412-016, CTX-20260412-018 | done |
| CTX-20260412-039 | 2026-04-12 21:11:20 +08:00 | P0 | knowledge | 实现 Add 作业提交与执行 | CTX-20260412-037, CTX-20260412-035 | done |
| CTX-20260412-040 | 2026-04-12 21:11:20 +08:00 | P1 | knowledge | 实现 Cognify 作业提交与执行 | CTX-20260412-039 | done |
| CTX-20260412-041 | 2026-04-12 21:11:20 +08:00 | P1 | knowledge | 实现 Memify 作业提交与执行 | CTX-20260412-040 | done |
| CTX-20260412-042 | 2026-04-12 21:11:20 +08:00 | P0 | knowledge | 实现 Search 服务、命中过滤、provenance 返回与授权二次校验 | CTX-20260412-038, CTX-20260412-039 | done |
| CTX-20260412-043 | 2026-04-12 21:11:20 +08:00 | P0 | knowledge-worker | 建立 Knowledge Worker bootstrap、Add/Cognify/Memify 后台执行链路 | CTX-20260412-002, CTX-20260412-037 | done |

#### Phase K. Quality & Delivery

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260412-044 | 2026-04-12 21:11:20 +08:00 | P0 | testing | 为 `common`、`auth`、`storage`、`parse`、`knowledge` 增加单元测试 | CTX-20260412-021, CTX-20260412-042 | planned |
| CTX-20260412-045 | 2026-04-12 21:11:20 +08:00 | P0 | testing | 增加 OpenAPI contract tests，校验 DTO 与 `cortex-api.yaml` 一致 | CTX-20260412-007, CTX-20260412-034, CTX-20260412-038 | done |
| CTX-20260412-046 | 2026-04-12 21:11:20 +08:00 | P0 | testing | 增加集成测试：SQLite/PostgreSQL、S3 兼容存储、队列、Worker | CTX-20260412-036, CTX-20260412-043 | planned |
| CTX-20260412-047 | 2026-04-12 21:11:20 +08:00 | P1 | testing | 增加端到端主链路测试：upload -> parse -> add -> search | CTX-20260412-046 | planned |
| CTX-20260412-048 | 2026-04-12 21:11:20 +08:00 | P0 | ci | 建立 CI pipeline：`uv sync`、lint、types、tests、OpenAPI/YAML 校验 | CTX-20260412-004, CTX-20260412-045 | planned |
| CTX-20260412-049 | 2026-04-12 21:11:20 +08:00 | P1 | devops | 补充本地 compose / runbook，覆盖 DB、S3、queue、OTel Collector、Jaeger、Prometheus、Grafana | CTX-20260412-005, CTX-20260412-048 | planned |

### Batch 2026-04-13 08:45:00 +08:00 | Phase D/E Continuation

目标：继续推进 Auth & Governance 与 API Bootstrap，先补齐权限治理持久层，再落地认证鉴权、健康检查、Job 查询/取消与事件读取接口。

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260413-001 | 2026-04-13 08:45:00 +08:00 | P0 | auth-db | 对齐 `cortex-init.sql` 中已有的权限治理表结构（`roles`、`role_permissions`、`actor_role_bindings`、`authorization_policies`、`job_events`）对应的 ORM 与 repository，补齐 Phase D/E 所需持久层能力 | CTX-20260412-011, CTX-20260412-012 | done |
| CTX-20260413-002 | 2026-04-13 08:45:00 +08:00 | P0 | auth | 实现 caller context、token validator chain、scope guard、RBAC/ABAC evaluator 与授权决策审计，收敛 `CTX-20260412-014 ~ CTX-20260412-017` | CTX-20260413-001 | done |
| CTX-20260413-003 | 2026-04-13 08:45:00 +08:00 | P0 | api | 实现 FastAPI middleware、exception handlers、`/v1/health/*`、`/v1/jobs/{jobId}`、`/v1/jobs/{jobId}/events`、`/v1/jobs/{jobId}/cancel` 及配套测试 | CTX-20260413-002 | done |

### Batch 2026-04-13 10:05:00 +08:00 | Phase F Storage Continuation

Goal: deliver the Storage phase end to end on top of the existing auth/API foundation, including object/version persistence, vendor-neutral S3 facade, upload session lifecycle, download signing, and matching FastAPI routes/tests.

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260413-004 | 2026-04-13 10:05:00 +08:00 | P0 | storage-db | Align `objects` / `object_versions` domain, ORM, repository, and contract models so upload sessions and committed object versions can be represented without provider-specific fields leaking into the API | CTX-20260412-021, CTX-20260412-023 | done |
| CTX-20260413-005 | 2026-04-13 10:05:00 +08:00 | P0 | storage | Implement `cortex_storage` core services: checksum helper, bucket resolver, S3 presign facade, upload-init strategy, upload-complete flow, and download URL signing | CTX-20260413-004 | done |
| CTX-20260413-006 | 2026-04-13 10:05:00 +08:00 | P0 | api | Expose `/v1/storage/uploads`, `/v1/storage/uploads/{uploadId}/complete`, `/v1/storage/objects/{objectId}`, and `/v1/storage/objects/{objectId}/download-url` with functional + resource authorization and ProblemDetails parity | CTX-20260413-005 | done |
| CTX-20260413-007 | 2026-04-13 10:05:00 +08:00 | P0 | testing | Add contract/integration coverage for storage DTOs, repository round-trips, upload session lifecycle, and download URL generation; finish with full lint/type/test validation and task/log closure | CTX-20260413-006 | done |

### Batch 2026-04-14 09:20:00 +08:00 | Phase G Parse Foundation Continuation

Goal: deliver the Parse foundation on top of the existing storage/auth/API platform, including parse contracts, registry/profile routing, normalization, persistence, and a reusable orchestration service that later adapters and API routes can build on.

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260414-001 | 2026-04-14 09:20:00 +08:00 | P0 | parse-db | Align parse-related domain, contract, ORM, repository, and unit-of-work layers for parser engines, parser profiles, parse runs, attempts, artifacts, and chunks so the control plane matches `cortex-init.sql` and `cortex-api.yaml` | CTX-20260412-025, CTX-20260412-028 | done |
| CTX-20260414-002 | 2026-04-14 09:20:00 +08:00 | P0 | parse-core | Implement `cortex_parse` core models, engine protocol, registry, profile loader, and selection router with vendor-neutral strategy/fallback behavior | CTX-20260414-001, CTX-20260412-026 | done |
| CTX-20260414-003 | 2026-04-14 09:20:00 +08:00 | P0 | parse-service | Implement Markdown/metadata/provenance normalization plus parse orchestration and persistence services that can execute a registered engine and commit the resulting document graph | CTX-20260414-001, CTX-20260414-002, CTX-20260412-027, CTX-20260412-028 | done |
| CTX-20260414-004 | 2026-04-14 09:20:00 +08:00 | P0 | testing | Add parse contract and integration coverage for registry/profile loading, router selection, normalization output, and parse persistence, then run full lint/type/test validation and close the batch in tasks/log | CTX-20260414-003 | done |

### Batch 2026-04-14 17:16:50 +08:00 | Phase H/I Parse API Continuation

Goal: land the first concrete parse adapter plus the synchronous Parse API surface, wire the runtime bootstrap into FastAPI, and close the batch with adapter/API coverage and repository-wide validation.

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260414-005 | 2026-04-14 17:16:50 +08:00 | P0 | parse-adapter | Implement the first concrete Crawl4AI-based parse adapter plus parse runtime/bootstrap wiring so the registry can expose real engine descriptors without leaking provider-specific setup into the API surface | CTX-20260414-003 | done |
| CTX-20260414-006 | 2026-04-14 17:16:50 +08:00 | P0 | parse-api | Expose `/v1/parse/engines`, `/v1/parse/profiles`, and `/v1/parse/sync` through FastAPI with auth, request correlation, and `cortex-api.yaml` parity | CTX-20260414-005 | done |
| CTX-20260414-007 | 2026-04-14 17:16:50 +08:00 | P0 | testing | Add adapter and parse API integration coverage, run focused plus full validation, and update task/log closure for the completed Phase H/I slice | CTX-20260414-006 | done |

### Batch 2026-04-14 20:16:20 +08:00 | Phase I Parse Async Worker Continuation

Goal: extend the synchronous Parse API into an asynchronous control-plane loop using a vendor-neutral DB-backed queue boundary, then add a worker `run_once` execution path that can later be replaced by Redis/SQS/Kafka without changing the public REST contract.

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260414-008 | 2026-04-14 20:16:20 +08:00 | P0 | parse-jobs | Add async Parse job request contracts plus idempotent queued-job submission and parse-result retrieval helpers on top of the existing job table | CTX-20260414-006 | done |
| CTX-20260414-009 | 2026-04-14 20:16:20 +08:00 | P0 | parse-api | Expose `/v1/parse/jobs` and `/v1/parse/jobs/{jobId}/result` with functional auth, job-resource checks, and `cortex-api.yaml` response semantics | CTX-20260414-008 | done |
| CTX-20260414-010 | 2026-04-14 20:16:20 +08:00 | P0 | parse-worker | Implement Parse Worker bootstrap and `run_once` polling/execution flow over queued parse jobs, including status transitions and job events | CTX-20260414-008 | done |
| CTX-20260414-011 | 2026-04-14 20:16:20 +08:00 | P0 | testing | Add async parse API and worker integration tests, run focused and full validation, and close the batch in task/log history | CTX-20260414-009, CTX-20260414-010 | done |

### Batch 2026-04-14 20:25:08 +08:00 | Phase I Worker Reliability Continuation

Goal: harden the DB-backed Parse Worker queue boundary with retry attempts, heartbeat/lease metadata, stale-lease recovery, and execution timeout handling before continuing the remaining adapter backlog.

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260414-012 | 2026-04-14 20:25:08 +08:00 | P0 | parse-worker | Add worker lease metadata, heartbeat refresh, stale lease detection, and retry budget accounting to the SQL job control layer | CTX-20260414-010 | done |
| CTX-20260414-013 | 2026-04-14 20:25:08 +08:00 | P0 | parse-worker | Enforce parse worker execution timeouts and retry-or-fail transitions with job events and queryable metadata | CTX-20260414-012 | done |
| CTX-20260414-014 | 2026-04-14 20:25:08 +08:00 | P1 | parse-adapter | Begin the remaining adapter backlog after worker hardening by adding vendor-neutral optional adapter scaffolding for Jina Reader, MarkItDown, and Docling | CTX-20260414-013 | done |
| CTX-20260414-015 | 2026-04-14 20:25:08 +08:00 | P0 | testing | Add focused reliability tests for retry, heartbeat, stale lease, and timeout behavior, then run full repository validation and close the batch | CTX-20260414-012, CTX-20260414-013 | done |

### Batch 2026-04-14 21:04:41 +08:00 | Phase H LlamaParse Adapter Continuation

Goal: complete the remaining high-fidelity document parser slot with an optional LlamaParse adapter, preserving the existing vendor-neutral engine protocol and configuration-template approach.

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260414-016 | 2026-04-14 21:04:41 +08:00 | P1 | parse-adapter | Implement an optional LlamaParse adapter with API-key/env validation, high-fidelity Markdown mapping, source metadata normalization, and bootstrap registration when available | CTX-20260412-031, CTX-20260414-014 | done |
| CTX-20260414-017 | 2026-04-14 21:04:41 +08:00 | P1 | testing | Add focused LlamaParse adapter tests using a fake parser implementation, then run focused and full repository validation | CTX-20260414-016 | done |

### Batch 2026-04-14 21:29:56 +08:00 | Phase J Knowledge Foundation Continuation

Goal: start the knowledge phase by aligning vendor-neutral knowledge contracts, the optional Cognee runtime abstraction, and the dataset control-plane API before queue-backed Add/Cognify/Memify/Search execution.

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260414-018 | 2026-04-14 21:29:56 +08:00 | P0 | knowledge-core | Implement `cortex_knowledge` foundation: dataset DTO/domain alignment, dataset service, optional Cognee runtime protocol/bootstrap, and response mapping that matches the Knowledge section of `cortex-api.yaml` without binding the API to a single provider | CTX-20260412-037 | done |
| CTX-20260414-019 | 2026-04-14 21:29:56 +08:00 | P0 | knowledge-api | Expose `/v1/knowledge/datasets` create/get endpoints with functional auth, dataset resource authorization, and OpenAPI-compatible responses | CTX-20260412-038, CTX-20260414-018 | done |
| CTX-20260414-020 | 2026-04-14 21:29:56 +08:00 | P0 | testing | Add focused integration coverage for dataset creation/read authorization paths, run repository validation, and close the batch plus task/log history | CTX-20260414-019 | done |

### Batch 2026-04-14 21:49:29 +08:00 | Phase J Knowledge Jobs And Search Continuation

Goal: extend the knowledge foundation into queued Add/Cognify/Memify execution plus synchronous Search, while persisting knowledge run and search audit trails behind the existing vendor-neutral REST contract.

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260414-021 | 2026-04-14 21:49:29 +08:00 | P0 | knowledge-db | Align domain, ORM, repositories, and unit-of-work layers for `knowledge_runs`, `search_requests`, and `search_hits` so Knowledge job execution and search audit/provenance can persist without provider-specific fields | CTX-20260414-018 | done |
| CTX-20260414-022 | 2026-04-14 21:49:29 +08:00 | P0 | knowledge-jobs | Implement Add/Cognify/Memify job contracts plus knowledge job control services that submit idempotent jobs and persist run metadata aligned with `cortex-api.yaml` | CTX-20260412-039, CTX-20260412-040, CTX-20260412-041, CTX-20260414-021 | done |
| CTX-20260414-023 | 2026-04-14 21:49:29 +08:00 | P0 | knowledge-search | Implement synchronous Search service with dataset resolution, resource filtering, runtime dispatch, and search request/hit persistence | CTX-20260412-042, CTX-20260414-021 | done |
| CTX-20260414-024 | 2026-04-14 21:49:29 +08:00 | P0 | knowledge-api | Expose `/v1/knowledge/add/jobs`, `/v1/knowledge/cognify/jobs`, `/v1/knowledge/memify/jobs`, and `/v1/knowledge/search` with functional and dataset-level authorization | CTX-20260414-022, CTX-20260414-023 | done |
| CTX-20260414-025 | 2026-04-14 21:49:29 +08:00 | P0 | knowledge-worker | Replace the placeholder knowledge worker with a `run_once` execution loop for Add/Cognify/Memify jobs, including status transitions, knowledge run updates, and job events | CTX-20260412-043, CTX-20260414-022 | done |
| CTX-20260414-026 | 2026-04-14 21:49:29 +08:00 | P0 | testing | Add focused contract/integration coverage for knowledge job submission, worker execution, search, and persisted run/search audit trails, then rerun full repository validation and update task/log history | CTX-20260414-024, CTX-20260414-025 | done |

### Batch 2026-04-14 22:16:28 +08:00 | Phase K OpenAPI Contract Continuation

Goal: tighten runtime API parity with `specs/cortex-api.yaml` by filling the declared observability endpoint, aligning route metadata/path parameters with the published contract, and adding automated OpenAPI contract checks.

| Task ID | Added At | Priority | Area | Task | Depends On | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CTX-20260414-027 | 2026-04-14 22:16:28 +08:00 | P0 | observability-api | Expose `/metrics` as a Prometheus-compatible plaintext endpoint and register the Observability surface in the FastAPI app so the runtime covers the documented telemetry contract baseline | CTX-20260412-018, CTX-20260412-019 | done |
| CTX-20260414-028 | 2026-04-14 22:16:28 +08:00 | P0 | api-contract | Align implemented route paths, path-parameter naming, operation IDs, summaries, and top-level OpenAPI metadata with the published `cortex-api.yaml` contract for the currently supported REST surface | CTX-20260414-027, CTX-20260412-034, CTX-20260412-024, CTX-20260414-024 | done |
| CTX-20260414-029 | 2026-04-14 22:16:28 +08:00 | P0 | testing | Add OpenAPI contract tests that load `specs/cortex-api.yaml`, compare runtime paths/operations and selected schema metadata, and cover the new `/metrics` endpoint behavior | CTX-20260412-045, CTX-20260414-028 | done |
| CTX-20260414-030 | 2026-04-14 22:16:28 +08:00 | P0 | validation | Run focused and full validation for the OpenAPI parity slice, fix contract drift discovered during the check, and update task/log history with any failures and mitigations | CTX-20260414-029 | done |

