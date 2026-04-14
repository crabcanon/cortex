# Cortex Development Log

## 1. 维护规则

1. 所有开发中的问题、修复、偏差和经验都按时间顺序追加。
2. 同一问题若重复出现，必须在新条目中引用此前条目并补充新的防范措施。
3. 每条记录至少包含：时间、阶段、现象、原因、处理、后续防范。

## 2. Entries

### 2026-04-12 21:28:00 +08:00 | Phase A Bootstrap

- Stage: `CTX-20260412-001 ~ CTX-20260412-005`
- Event: 开始第一轮编码前，先建立开发日志文件并把 Phase A 任务状态切换为 `in_progress`。
- Cause: 后续需要严格执行“先更新任务、再编码、再校验、再回写日志”的流程。
- Action: 新建 `specs/cortex-log.md`，作为后续问题与修复记录的统一入口。
- Prevention: 每轮开发开始前先更新 `specs/cortex-tasks.md` 和 `specs/cortex-log.md`，避免任务推进和问题经验脱节。

### 2026-04-12 21:34:00 +08:00 | uv Cache Directory Failure

- Stage: `CTX-20260412-001`
- Event: `uv sync --all-packages --all-groups` 失败，报错无法初始化 `C:\Users\hy\AppData\Local\uv\cache`，并提示 `os error 183`。
- Cause: 当前机器的全局 uv cache 路径处于异常状态，导致 uv 无法在系统默认 cache 位置创建或初始化缓存目录。
- Action: 新增根级 `uv.toml`，把 `cache-dir` 固定到仓库内的 `.uv-cache`，避免依赖系统级缓存目录。
- Prevention: 后续本仓所有 `uv` 命令统一走仓库内 cache；若再次出现缓存类问题，优先检查 `uv.toml` 与 `.uv-cache` 是否被意外占用或破坏。

### 2026-04-12 21:38:00 +08:00 | uv Managed Python Discovery Failure

- Stage: `CTX-20260412-001`
- Event: `uv sync` 与 `uv lock` 继续失败，报错无法读取 `C:\Users\hy\AppData\Roaming\uv\python`，访问被拒绝。
- Cause: 当前机器无可用系统 Python，且 uv 默认偏好使用全局 managed Python 目录；该目录当前不可访问，导致 Python 发现流程在启动前即失败。
- Action: 在 `uv.toml` 中把 `python-preference` 调整为 `only-managed`，并在开发脚本中显式设置 `UV_PYTHON_INSTALL_DIR` 指向仓库内 `.uv-python`。
- Prevention: 本仓后续统一使用仓库内 managed Python 目录，避免依赖用户目录下不可控的 uv Python 安装状态。

### 2026-04-12 21:42:00 +08:00 | Bootstrap Dependency Scope Too Broad

- Stage: `CTX-20260412-003 ~ CTX-20260412-005`
- Event: 初版 bootstrap 命令使用 `uv sync --all-packages --all-groups`，会把 docs 依赖也一起安装，导致首次同步时间偏长。
- Cause: docs 依赖只在文档构建时需要，并不是日常编码和测试的默认路径。
- Action: 将 README 与 `scripts/dev/bootstrap.ps1` 调整为 `uv sync --all-packages`，仅同步默认 dependency groups。
- Prevention: 后续新增 dependency group 时先判断是否属于默认开发路径，避免把低频依赖塞进每次启动流程。

### 2026-04-12 21:47:00 +08:00 | Ruff Import Order Failure

- Stage: `CTX-20260412-004`
- Event: 第一次运行 `ruff check .` 时失败，提示 `apps/api/src/cortex_api/main.py` 的 import 顺序不符合规则。
- Cause: 手写入口文件时未按 Ruff 的 import sorting 规则排列第三方与本地导入。
- Action: 调整 `uvicorn`、`FastAPI`、本地模块的导入顺序，重新进入 lint 校验。
- Prevention: 后续新增 Python 文件后优先运行 Ruff，再进入 type-check / pytest，尽量把格式与导入类问题截断在最前面。

### 2026-04-12 21:51:00 +08:00 | Pytest Cache Provider Permission Warning

- Stage: `CTX-20260412-004`
- Event: `pytest` 通过，但伴随 `PytestCacheWarning`，提示无法创建 `pytest-cache-files-*` 临时目录，随后该目录在 PowerShell 中也表现为 `AccessDenied`。
- Cause: 当前机器对 pytest cache provider 使用的临时目录创建/访问存在异常，导致缓存写入链路不稳定。
- Action: 在 `pyproject.toml` 中禁用 `cacheprovider`，并把 `pytest-cache-files-*` 加入 `.gitignore`。
- Prevention: 后续测试默认不依赖 pytest cache；若未来需要恢复缓存能力，应先在隔离环境中验证此机器的目录权限行为。

### 2026-04-12 21:54:00 +08:00 | Phase A Completed

- Stage: `CTX-20260412-001 ~ CTX-20260412-005`
- Event: `uv workspace` 骨架、成员包目录、根级工具链配置、`.env.example`、开发脚本和 smoke tests 已全部落地。
- Cause: 第一轮编码目标是先把工程结构、依赖解算、质量门禁和最小入口进程稳定下来，为后续业务实现提供底座。
- Action: 产出根级 `pyproject.toml`、`uv.lock`、`uv.toml`、`.python-version`、`apps/`、`workers/`、`packages/`、`tests/`、`scripts/` 与基础 README，并完成 `ruff`、`pyright`、`pytest`、API/Worker smoke validation。
- Prevention: 下一轮开始前先在 `cortex-tasks.md` 中把 `CTX-20260412-006` 及后续任务切到 `in_progress`，保持“先记账、再开发、再校验、再写日志”的节奏。

### 2026-04-12 22:00:00 +08:00 | Workspace Package Source Resolution Failure

- Stage: `CTX-20260412-009`
- Event: `uv lock` 在给 `cortex-observability` 增加 `cortex-common` 依赖后失败，提示 workspace member 缺少 `tool.uv.sources` 条目。
- Cause: 根级 `pyproject.toml` 只声明了 `tool.uv.workspace.members`，但没有为内部包互相依赖建立 workspace source 映射。
- Action: 在根级 `pyproject.toml` 中补充 `tool.uv.sources`，显式把 `cortex-api`、`cortex-common`、`cortex-contracts`、`cortex-domain`、`cortex-observability` 等成员标记为 `{ workspace = true }`。
- Prevention: 后续新增跨包依赖时，先检查对应项目名是否已出现在 `tool.uv.sources`；保持工作区依赖声明与成员清单同步更新。

### 2026-04-12 22:04:00 +08:00 | Workspace Check Script False Negative

- Stage: `CTX-20260412-006 ~ CTX-20260412-009`
- Event: 第一版 `scripts/dev/check.ps1` 在 `pyright` 与 `pytest` 已报错的情况下仍继续执行，并且 `uv run` 未携带 `--all-packages`，导致检查运行在“看不见 workspace 包”的环境中。
- Cause: PowerShell 对原生命令失败默认不会像异常一样中断；同时脚本按 root project 执行 `uv run`，没有把工作区成员包与其依赖一起解析进运行环境。
- Action: 为 `check.ps1` 增加 `Invoke-UvCheck` 包装器与 `$PSNativeCommandUseErrorActionPreference = $true`，并把 Ruff、Pyright、Pytest 全部调整为 `uv run --all-packages ...`。
- Prevention: 后续所有仓库级检查脚本都应显式处理 `$LASTEXITCODE`，并优先选择 `--all-packages` 或等价方式，避免出现“检查看起来跑了，其实环境不对”的假阳性。

### 2026-04-12 22:08:00 +08:00 | Phase B Completed

- Stage: `CTX-20260412-006 ~ CTX-20260412-009`
- Event: `cortex_common`、`cortex_contracts`、`cortex_domain`、`cortex_observability` 已完成首版实现，并通过 lint、type-check、pytest 及 API/Worker smoke validation。
- Cause: 第二轮目标是先搭建所有后续模块会共享的基础能力，包括配置树、通用异常/分页/ID、领域枚举/记录、以及 OpenTelemetry bootstrap 与 trace correlation。
- Action: 完成 settings、idempotency、ProblemDetails、Job DTO、领域模型、OTel bootstrap、metric facade 等代码，并增加 `tests/contract/test_foundation_models.py` 覆盖基础行为。
- Prevention: 进入数据库阶段前保持“先更新任务状态，再读取 specs，对齐 schema/init.sql 后再实现 engine、migration、repository、transaction helper”的顺序，避免基础设施与文档发生漂移。

### 2026-04-12 22:10:00 +08:00 | Pytest Tempdir Plugin Permission Failure

- Stage: `CTX-20260412-010 ~ CTX-20260412-013`
- Event: 新增数据库集成测试后，`pytest` 在 `tmp_path` fixture 初始化和 session 收尾阶段持续触发 `PermissionError`；无论默认系统临时目录还是仓库内自定义 `basetemp`，都会被 `tmpdir` 插件的目录清理流程卡住。
- Cause: 当前机器对 pytest tmpdir 插件创建/清理的编号目录存在异常权限行为，和此前 `pytest cache provider` 的目录权限问题属于同一类环境噪声。
- Action: 停用 `tmpdir` 插件，测试改为自行在仓库内 `runtime-test-data/` 下创建隔离目录与 SQLite 文件，不再依赖 pytest 的临时目录生命周期。
- Prevention: 后续新增集成测试时优先使用仓库内可控路径或显式测试夹具，不默认依赖系统临时目录；若未来需要恢复 `tmp_path`，应先单独验证本机对 pytest tmpdir 的目录创建与清理权限。

### 2026-04-12 22:12:00 +08:00 | Alembic Path Separator Deprecation Warning

- Stage: `CTX-20260412-011`
- Event: 数据库集成测试通过，但 Alembic 在读取 `alembic.ini` 时给出 `prepend_sys_path` 相关弃用警告。
- Cause: `alembic.ini` 仍使用旧式路径拆分行为，未显式设置 `path_separator`。
- Action: 在 `packages/db/alembic.ini` 中增加 `path_separator = os`，消除弃用警告并与当前 Alembic 配置约定对齐。
- Prevention: 后续新增工具链配置项时，同步检查上游版本的弃用提示，尽量把 warning 在本地阶段清理掉，避免进入 CI 后放大噪音。

### 2026-04-12 22:14:00 +08:00 | Phase C Completed

- Stage: `CTX-20260412-010 ~ CTX-20260412-013`
- Event: `cortex_db` 已完成首版 engine/session、naming convention、baseline migration、核心 repository 与 unit-of-work，并通过 lint、type-check 与 SQLite 集成测试。
- Cause: 第三轮目标是把控制面数据库底座搭稳，为后续鉴权、Storage、Parse 持久化和 Job/API 查询提供统一事务边界。
- Action: 新增 `cortex_db.base`、`engine`、`models`、`repositories`、`uow`、`cli`、Alembic `env.py` 与 baseline revision，并补充 `tests/integration/test_db_foundation.py` 覆盖迁移和 CRUD round-trip。
- Prevention: 进入鉴权阶段前保持“先利用现有 repository / UoW 组合资源上下文，再实现 JWT、scope、RBAC/ABAC evaluator 与决策审计”的顺序，避免 API 层直接越过数据边界访问底层表结构。

### 2026-04-13 08:45:00 +08:00 | Phase D/E Started

- Stage: `CTX-20260413-001 ~ CTX-20260413-003`
- Event: 开始推进 Auth & Governance 与 API Bootstrap，目标是先打通权限治理底座，再落地 health 与 jobs 基础 REST API。
- Cause: `storage`、`parse`、`knowledge` 三条链路后续都依赖统一的认证鉴权、ProblemDetails 错误模型与 Job 控制接口。
- Action: 在编码前先补充 `cortex-tasks.md` 新批次任务，把权限持久层对齐、授权服务与 API bootstrap 拆解到 task 粒度。
- Prevention: 后续每一轮继续按“先补 tasks/log，再编码，再测试校验，再回写日志”的顺序执行，避免实现进度与设计台账脱节。

### 2026-04-13 08:49:00 +08:00 | Auth Governance Persistence Gap

- Stage: `CTX-20260413-001`
- Event: 在对齐 `cortex-init.sql`、`cortex-schema.md` 与当前 ORM 时发现，迁移脚本已经创建 `roles`、`role_permissions`、`actor_role_bindings`、`authorization_policies` 与 `job_events`，但 `packages/db` 尚未提供对应 SQLAlchemy model / repository。
- Cause: Phase C 首轮实现优先覆盖了租户、对象、文档、数据集、Job 与决策审计最小闭环，未把权限治理与 Job 事件表完整映射到 Python 持久层。
- Action: 将该缺口提升为本轮显式任务 `CTX-20260413-001`，优先补齐 ORM、repository、domain model 与测试，再继续实现 RBAC/ABAC evaluator 和 Job API。
- Prevention: 后续新增 schema / init.sql 表时，同步检查 ORM、repository、contract test 与 migration 覆盖，避免出现“数据库已建表、代码层不可达”的隐性缺口。

### 2026-04-13 09:03:00 +08:00 | uv Managed Python Access Recurrence

- Stage: `CTX-20260413-001 ~ CTX-20260413-003`
- Event: 本轮执行 `uv sync --all-packages` 时再次触发对 `C:\Users\hy\AppData\Roaming\uv\python` 的访问拒绝，和前序 bootstrap 阶段是同类问题。
- Cause: 直接运行 `uv` 时仍会优先探测全局 managed Python 路径；如果没有显式设置 `UV_PYTHON_INSTALL_DIR`，就会绕开仓库内 `.uv-python` 目录。
- Action: 按此前日志方案，显式设置 `UV_PYTHON_INSTALL_DIR=.uv-python` 后重新执行 `uv sync` 与全量检查；同时继续通过 `scripts/dev/check.ps1` 统一封装该环境变量。
- Prevention: 后续所有仓库内 `uv` 命令默认都通过 `scripts/dev/check.ps1` 或显式设置 `UV_PYTHON_INSTALL_DIR` 执行，避免再次回退到用户目录。

### 2026-04-13 09:09:00 +08:00 | Domain/Contract Enum Boundary

- Stage: `CTX-20260413-002 ~ CTX-20260413-003`
- Event: `pyright` 在 Job API DTO 映射阶段报告 `cortex_domain` 与 `cortex_contracts` 的 `JobType` / `JobStatus` 枚举类型不兼容。
- Cause: 领域层和契约层虽然复用了相同的字面量值，但出于分层隔离分别定义了独立枚举；API service 直接把领域枚举塞进契约 DTO 时触发类型边界错误。
- Action: 在 `apps/api/src/cortex_api/services/jobs.py` 增加显式值映射，把 `domain` 枚举转换为 `contracts` 枚举后再输出；同时保留两层的独立性，避免把契约类型反向渗透到领域层。
- Prevention: 后续 API adapter / service 层一律承担“domain -> contract”的显式映射职责，不在 DTO 构造处偷懒复用跨层枚举实例。

### 2026-04-13 09:12:00 +08:00 | Phase D/E Completed

- Stage: `CTX-20260412-014 ~ CTX-20260412-020`, `CTX-20260413-001 ~ CTX-20260413-003`
- Event: 认证鉴权与 API bootstrap 本轮已完成：补齐权限治理 ORM/repository、实现 dev/JWT/introspection token validator chain、scope guard、RBAC/ABAC evaluator、授权决策审计、ProblemDetails 异常处理、中间件、`/v1/health/*` 与 `/v1/jobs/*` 基础接口，并通过 lint、type-check、pytest。
- Cause: 这是 Storage/Parse/Knowledge 三条业务链路继续落地前必须先收敛的控制面底座。
- Action: 新增/更新 `cortex_auth`、`cortex_contracts`、`cortex_domain`、`cortex_db`、`apps/api` 相关实现，并补充 `tests/integration/test_api_auth_jobs.py` 与扩展版 `tests/integration/test_db_foundation.py`。
- Prevention: 下一阶段进入 Storage 时优先复用当前 `AuthorizationService`、`ProblemDetails`、request/trace middleware 与 Job DTO，不再重复发明一套控制面基础设施。

### 2026-04-13 10:05:00 +08:00 | Phase F Started

- Stage: `CTX-20260412-021 ~ CTX-20260412-024`, `CTX-20260413-004 ~ CTX-20260413-007`
- Event: Started the Storage phase continuation, with the first focus on persistent upload-session representation, S3 abstraction, and API parity with `specs/cortex-api.yaml`.
- Cause: Storage is the next dependency for Parse and Knowledge, and it needs to reuse the existing auth, telemetry, and ProblemDetails control-plane foundation rather than inventing a parallel path.
- Action: Added a new task batch for Storage decomposition before coding and began reconciling `cortex-init.sql`, `cortex-api.yaml`, and the current `domain/contracts/db` surface.
- Prevention: Keep the implementation ordered as persistence -> storage package -> API routes -> tests -> full verification so later Parse work can build on a stable object lifecycle.

### 2026-04-13 10:11:00 +08:00 | Upload Session Persistence Gap

- Stage: `CTX-20260413-004 ~ CTX-20260413-006`
- Event: While implementing the Storage phase, `specs/cortex-api.yaml` required a durable upload-session lifecycle, but the current schema had no dedicated `upload_sessions` table.
- Cause: The initial schema modeled `objects` and `object_versions`, but left upload-session persistence implicit even though the API needs resumable completion by `uploadId`.
- Action: Bound `upload_id` to `object_id`, persisted pending session state under reserved object metadata (`__upload__`), and kept committed history in `object_versions`, which avoided in-memory session state and vendor-specific provider fields.
- Prevention: Until a dedicated upload-session table is introduced, any code that looks up a pending upload must keep using the stable `upload_id == object_id` rule and reserved storage metadata keys for transient provider refs.

### 2026-04-13 10:22:00 +08:00 | Storage Router Encoding And Annotation Cleanup

- Stage: `CTX-20260413-006`
- Event: The first storage router draft picked up mojibake in summary strings and failed lint with Ruff `B008` because one FastAPI query parameter still used a call-form default.
- Cause: Bilingual route text was copied through the terminal with encoding noise, and the query metadata was declared as `Query(...)` directly in the default position.
- Action: Rewrote the storage router with ASCII-safe summaries in code, moved the canonical bilingual wording back to `specs/cortex-api.yaml`, and switched query metadata to `Annotated[..., Query(...)]` form.
- Prevention: Keep code-side route summaries shell-safe and let the spec remain the bilingual source of truth; for FastAPI params, prefer `Annotated` metadata to avoid repeating the same `B008` issue.

### 2026-04-13 10:31:00 +08:00 | Storage Facade Protocol Boundary

- Stage: `CTX-20260413-005`, `CTX-20260413-007`
- Event: Pyright rejected the storage integration tests because `StorageService` accepted a concrete boto3-backed client type, which made the fake object-store test double fail structural checks.
- Cause: The provider seam was initially typed as a concrete class rather than a protocol, even though the design goal is vendor-neutrality and easy substitution.
- Action: Introduced `ObjectStoreClientProtocol`, updated `BucketResolver` and `StorageService` to depend on that protocol, and aligned the fake client method signatures to the protocol contract.
- Prevention: All future provider adapters should be typed as protocols or abstract contracts so local tests, alternate clouds, and future parsers/search stores can be swapped without concrete SDK coupling.

### 2026-04-13 10:38:00 +08:00 | Phase F Completed

- Stage: `CTX-20260412-021 ~ CTX-20260412-024`, `CTX-20260413-004 ~ CTX-20260413-007`
- Event: The Storage phase is now in place: object/version persistence, vendor-neutral S3 facade, upload-init and upload-complete lifecycle, download URL signing, FastAPI storage routes, and contract/integration coverage all landed and passed full validation.
- Cause: Parse and Knowledge both depend on a stable object lifecycle, so Storage had to be finished before the next parser foundation stage could move safely.
- Action: Implemented `cortex_storage`, expanded domain/contracts/DB models, wired `/v1/storage/*` endpoints into the API control plane, and reran the full repository check suite.
- Prevention: The next phase can now reuse the object/version model, bucket resolution, auth/resource checks, and direct-to-storage upload pattern instead of rebuilding storage concerns inside Parse.

### 2026-04-14 09:20:00 +08:00 | Phase G Started

- Stage: `CTX-20260412-025 ~ CTX-20260412-028`, `CTX-20260414-001 ~ CTX-20260414-004`
- Event: Started the Parse foundation continuation, with the first focus on aligning the parse control-plane schema, core routing abstractions, normalization pipeline, and persistence service before exposing new API routes.
- Cause: The task ledger places Parse immediately after Storage, and the adapters/API endpoints need a stable engine registry, profile model, and document persistence substrate rather than one-off parser code.
- Action: Added a dedicated Phase G batch to `specs/cortex-tasks.md` and began reconciling `cortex-api.yaml`, `cortex-schema.md`, `cortex-init.sql`, and the current empty `packages/parse` package.
- Prevention: Keep the implementation ordered as parse persistence foundation -> routing/normalization -> orchestration -> tests/validation so the later adapter and API stages can build on stable contracts.

### 2026-04-14 09:42:00 +08:00 | Parse Enum Boundary

- Stage: `CTX-20260414-001 ~ CTX-20260414-003`
- Event: `pyright` rejected the parse persistence layer because the in-memory registry descriptors used `cortex_contracts` parse enums while the ORM/domain layer expected the corresponding `cortex_domain` enums.
- Cause: Parse foundation spans contract, runtime, and persistence boundaries; directly reusing contract enums inside domain records repeated the same cross-layer enum mismatch that appeared earlier in the Job API work.
- Action: Added explicit value-based enum mapping when persisting registered parse engines, keeping the public API enums and the domain persistence enums independent.
- Prevention: Continue treating `contracts -> domain` as an explicit adapter boundary inside service/repository code instead of passing contract enum instances directly into domain records.

### 2026-04-14 09:47:00 +08:00 | Parse Test Constructor Strictness

- Stage: `CTX-20260414-004`
- Event: The first parse integration test draft passed raw nested `dict` objects into `ParseSyncRequest` fields that are typed as concrete Pydantic models, which `pyright` flagged even though runtime validation would have accepted them.
- Cause: The parse request surface is deeper than the earlier storage tests, so ad hoc dict literals obscured the intended contract shape and weakened static validation.
- Action: Rewrote the test to construct `ParseOutputOptions`, `ChunkingOptions`, `ParsePersistenceOptions`, and `AccessPolicy` explicitly, which made the test mirror the contract types exactly.
- Prevention: For complex request DTOs, prefer model constructors over nested dict literals in tests so type-checking catches schema drift earlier and more precisely.

### 2026-04-14 09:55:00 +08:00 | Phase G Completed

- Stage: `CTX-20260412-025 ~ CTX-20260412-028`, `CTX-20260414-001 ~ CTX-20260414-004`
- Event: The Parse foundation is now in place: parse contracts, engine/profile catalog persistence, registry/profile loading, routing/fallback, Markdown normalization, chunking, parse orchestration, and parse persistence all landed and passed full validation.
- Cause: This phase had to establish a stable vendor-neutral substrate before Phase H adapters and Phase I parse API routes can plug in concrete engines such as Crawl4AI, Jina Reader, LlamaParse, MarkItDown, and Docling.
- Action: Implemented `cortex_parse`, expanded domain/contracts/DB layers for parse entities, added a built-in default profile template, and introduced contract/integration coverage for parse routing and persistence.
- Prevention: The next phase can now focus on concrete adapters and parse API exposure without rebuilding engine registry, normalization, chunk persistence, or parse-run control-plane concerns.
