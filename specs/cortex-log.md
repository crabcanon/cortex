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

### 2026-04-14 17:16:50 +08:00 | Phase H/I Started

- Stage: `CTX-20260412-029`, `CTX-20260412-034`, `CTX-20260414-005 ~ CTX-20260414-007`
- Event: Started the next Parse phase, focusing on the first concrete parser adapter, runtime bootstrap into FastAPI, and the synchronous Parse API endpoints defined in `cortex-api.yaml`.
- Cause: The Parse foundation is already stable, so the next highest-value step is to expose a real engine-backed API surface before moving on to async worker execution and the remaining adapters.
- Action: Added a new Phase H/I batch to `cortex-tasks.md` and began reconciling the current API app, parse runtime, and Crawl4AI integration boundary.
- Prevention: Keep the work ordered as adapter/runtime bootstrap -> API routes -> tests/validation -> batch closure so later async parse jobs can reuse the same service graph rather than fork a second implementation path.

### 2026-04-14 17:22:00 +08:00 | Optional Adapter Import Lint Boundary

- Stage: `CTX-20260414-005 ~ CTX-20260414-007`
- Event: The first full-repo validation failed after the Crawl4AI adapter landed because Ruff flagged constant-string `getattr(...)` usage on dynamically imported modules plus import-order drift in the new parse API tests.
- Cause: Optional provider adapters naturally rely on runtime imports, but the initial implementation mixed dynamic-module access with patterns that Ruff treats as avoidable, and the new tests had not yet been normalized to the repository's import grouping rules.
- Action: Replaced the flagged constant-string `getattr` calls with direct attribute access after module import, let Ruff normalize the new test file import block, and reran the full repository check suite.
- Prevention: For future optional adapters, keep dynamic imports at the module boundary, but switch to direct attribute access immediately after import so lint, type-checking, and optional-dependency isolation all stay aligned.

### 2026-04-14 17:24:45 +08:00 | Phase H/I Slice Completed

- Stage: `CTX-20260414-005 ~ CTX-20260414-007`, `CTX-20260412-034`
- Event: The first Phase H/I delivery slice is now complete: a concrete Crawl4AI-backed adapter, parse runtime bootstrap, `/v1/parse/engines`, `/v1/parse/profiles`, `/v1/parse/sync`, targeted adapter/API coverage, and full repository validation all landed successfully.
- Cause: The immediate goal for this round was to expose a real parse control-plane entrypoint on top of the Phase G foundation before moving further into async parse jobs and the remaining adapters.
- Action: Added `cortex_parse` adapter/bootstrap modules, wired ParseService into the API lifespan and runtime dependencies, introduced FastAPI parse routes, added integration tests for both the Crawl4AI adapter and parse endpoints, and reran `scripts/dev/check.ps1` to completion.
- Prevention: The next round should build on this exact service graph for async parse job submission/execution and continue the remaining adapter backlog instead of creating a separate worker-only parse path.

### 2026-04-14 20:16:20 +08:00 | Phase I Async Parse Started

- Stage: `CTX-20260414-008 ~ CTX-20260414-011`, `CTX-20260412-035 ~ CTX-20260412-036`
- Event: Started the asynchronous Parse continuation, focusing on queued job submission, a parse result endpoint, and a worker `run_once` execution path over the existing SQL job table.
- Cause: The synchronous Parse API is now wired, so the next public contract gap is `/v1/parse/jobs` plus a worker loop that can execute queued parse work without coupling the API to a specific queue vendor.
- Action: Added a new task batch before coding and selected a DB-backed queue boundary for this slice, keeping the API contract stable while deferring Redis/SQS/Kafka replacement to later infrastructure work.
- Prevention: Keep async execution as a thin layer over the same `ParseService` runtime used by sync parsing so adapter behavior, normalization, telemetry, and persistence do not fork between API and worker paths.

### 2026-04-14 20:20:00 +08:00 | Worker Bootstrap Import Formatting Failure

- Stage: `CTX-20260414-010 ~ CTX-20260414-011`
- Event: The first full-repo validation after adding the Parse Worker execution loop failed in Ruff because the new worker bootstrap imports were not sorted and one dependency import line exceeded the repository line-length limit.
- Cause: The worker file changed from a tiny smoke-test placeholder into a real runtime module, and the new multi-package imports were added faster than the formatting rules were applied.
- Action: Split the long `cortex_db` import into a parenthesized block and reran the full validation suite.
- Prevention: For future placeholder-to-runtime rewrites, run a focused `ruff check <file>` immediately after the first implementation pass, before invoking the full repository check.

### 2026-04-14 20:22:14 +08:00 | Phase I Async Parse Slice Completed

- Stage: `CTX-20260414-008 ~ CTX-20260414-011`, `CTX-20260412-036`
- Event: The asynchronous Parse slice is now complete: `ParseJobRequest`, idempotent queued-job submission, parse result retrieval, `/v1/parse/jobs`, `/v1/parse/jobs/{jobId}/result`, Parse Worker `run_once`, status transitions, job events, and integration coverage all landed.
- Cause: The REST contract needed a non-blocking parse path before larger crawling/document workloads can be routed through worker execution instead of tying up API request handlers.
- Action: Added a vendor-neutral DB-backed queue boundary using the existing `jobs` table, wired parse job control into FastAPI, expanded the worker package from bootstrap placeholder to executable poller, and verified the flow `submit -> pending result -> worker run_once -> completed result -> job events`.
- Prevention: Keep `CTX-20260412-035` open for retry and timeout hardening; the next worker pass should add retry counters, lease/heartbeat semantics, and timeout handling before introducing a production queue backend.

### 2026-04-14 20:25:08 +08:00 | Worker Reliability Started

- Stage: `CTX-20260412-035`, `CTX-20260414-012 ~ CTX-20260414-015`
- Event: Started worker reliability hardening for the SQL-backed Parse queue, focusing on retry budgets, lease ownership, heartbeat refresh, stale-lease recovery, and execution timeout handling.
- Cause: The previous async slice proved the API/worker control path, but production-grade worker behavior needs bounded retries and lease/timeout semantics before additional adapters increase the failure surface.
- Action: Added a dedicated reliability batch to `cortex-tasks.md` before coding and scoped the implementation to portable job metadata stored in existing standard-SQL columns.
- Prevention: Keep the reliability state encoded as explicit job metadata and events so a future Redis/SQS/Kafka queue backend can map the same semantics without changing REST contracts.

### 2026-04-14 20:34:00 +08:00 | Adapter Formatting Cleanup

- Stage: `CTX-20260414-014`
- Event: After adding the Jina Reader, MarkItDown, and Docling adapters, full validation failed on two long adapter lines and one unused import.
- Cause: The adapter implementations were intentionally lightweight and optional, but the first pass left a long timeout expression and a long Docling config-error line that exceeded repository style limits.
- Action: Split the long lines, removed the unused Jina adapter import, and reran full validation.
- Prevention: Run focused Ruff checks immediately after adding each optional adapter module, especially when adapter code includes long provider names or MIME types.

### 2026-04-14 20:40:25 +08:00 | Worker Reliability And Adapter Slice Completed

- Stage: `CTX-20260412-030`, `CTX-20260412-032`, `CTX-20260412-033`, `CTX-20260412-035`, `CTX-20260414-012 ~ CTX-20260414-015`
- Event: Worker reliability hardening and the next adapter slice are complete: SQL-backed parse jobs now carry retry/lease metadata, workers claim jobs with lease ownership, refresh heartbeat, recover stale leases, enforce execution timeout, and retry or fail with explicit job events; Jina Reader, MarkItDown, and Docling optional adapters are also registered through the parse bootstrap when available.
- Cause: Async Parse needed failure handling before broader adapter diversity increased error and timeout scenarios; the adapter backlog also needed a vendor-neutral optional-dependency pattern beyond Crawl4AI.
- Action: Extended job repository operations, added queue state management in `ParseJobControlService`, hardened `ParseWorker.run_once`, added adapter implementations and tests, and verified retry, timeout, stale lease recovery, and adapter conversion behavior.
- Prevention: LlamaParse remains the main parse adapter gap; before adding it, reuse the same optional-adapter pattern and add API-key/config validation tests so cloud-only parser behavior does not leak provider-specific assumptions into the core contracts.

### 2026-04-14 21:04:41 +08:00 | LlamaParse Adapter Started

- Stage: `CTX-20260412-031`, `CTX-20260414-016 ~ CTX-20260414-017`
- Event: Started the LlamaParse adapter continuation to fill the remaining high-fidelity document parsing slot in Phase H.
- Cause: Crawl4AI, Jina Reader, MarkItDown, and Docling are now covered; LlamaParse remains the last planned parser engine before the implementation can move cleanly into Knowledge/Cognee work.
- Action: Added a focused task batch and selected the same optional-dependency adapter pattern used by MarkItDown and Docling, with explicit API-key validation for the remote parser boundary.
- Prevention: Keep LlamaParse-specific API keys and parser kwargs inside `engine_options` / environment handling, never in core request contracts or domain persistence fields.

### 2026-04-14 21:07:55 +08:00 | LlamaParse Adapter Completed

- Stage: `CTX-20260412-031`, `CTX-20260414-016 ~ CTX-20260414-017`
- Event: The optional LlamaParse adapter is complete and registered through the parse bootstrap when the provider SDK is installed.
- Cause: Phase H still had one planned high-fidelity remote document parser, and completing it removes the last adapter backlog item except for deeper Crawl4AI artifact storage enhancement.
- Action: Added `LlamaParseEngine`, API-key/env validation, async/sync loader compatibility, multi-document Markdown merge, metadata/title normalization, focused fake-parser tests, and a full repository validation run.
- Prevention: Any future provider-specific LlamaParse options should stay in `engine_options.llama_parse` and continue to be covered with fake SDK tests before live-provider tests are introduced.

### 2026-04-14 21:29:56 +08:00 | Knowledge Foundation Started

- Stage: `CTX-20260412-037 ~ CTX-20260412-038`, `CTX-20260414-018 ~ CTX-20260414-020`
- Event: Started the first Knowledge/Cognee delivery slice, focusing on a vendor-neutral `cortex_knowledge` foundation plus dataset create/get control-plane endpoints.
- Cause: Parse foundation, sync/async API, worker reliability, and the planned parser adapters are now in place, so the next contract gap is the Knowledge domain entrypoint rather than more Parse surface area.
- Action: Added a new task batch before coding and scoped the slice to dataset DTO/domain alignment, an optional Cognee runtime abstraction, dataset service wiring, resource authorization, and targeted validation.
- Prevention: Keep Add/Cognify/Memify/Search execution for the next slice so the first Knowledge batch can stabilize contracts and authorization boundaries before background job orchestration is introduced.

### 2026-04-14 21:42:10 +08:00 | Knowledge Slice Validation Friction

- Stage: `CTX-20260414-018 ~ CTX-20260414-020`
- Event: Two small execution issues surfaced during the Knowledge foundation slice: I initially reached for non-existent test filenames based on memory, and the first full-repo check failed on Ruff import ordering in the new knowledge service module.
- Cause: The repository standardizes API integration test names as `test_api_<domain>.py`, and the new module was hand-written faster than the lint formatter was applied.
- Action: Switched to the repository's actual test files, added `tests/integration/test_api_knowledge.py`, ran focused contract/API validation first, then used Ruff auto-fix on the import block before rerunning the full repository check.
- Prevention: For future slices, inspect the existing `tests/integration/test_api_*` naming scheme before adding new tests, and run a focused `ruff check --fix <new file>` before the first full validation pass.

### 2026-04-14 21:47:35 +08:00 | Knowledge Foundation And Dataset API Slice Completed

- Stage: `CTX-20260414-018 ~ CTX-20260414-020`, `CTX-20260412-037 ~ CTX-20260412-038`
- Event: The first Knowledge slice is complete: dataset contracts, dataset persistence alignment, optional Cognee runtime bootstrap, `/v1/knowledge/datasets` create/get endpoints, resource authorization, and end-to-end test coverage all landed successfully.
- Cause: The project needed a stable knowledge control plane and dataset boundary before queuing Add/Cognify/Memify/Search work onto a dedicated Knowledge worker.
- Action: Added `cortex_contracts.knowledge`, extended dataset domain/repository mapping, introduced `cortex_knowledge` runtime/service/bootstrap modules, wired the API lifespan and runtime dependencies to a knowledge service, added knowledge router/service helpers plus integration coverage, and reran `scripts/dev/check.ps1` to completion.
- Prevention: Keep `CTX-20260412-037` and `CTX-20260412-038` open until the next slice adds knowledge run persistence and the queued Add/Cognify/Memify/Search execution path on top of the foundation added here.

### 2026-04-14 21:49:29 +08:00 | Knowledge Jobs And Search Started

- Stage: `CTX-20260412-039 ~ CTX-20260412-043`, `CTX-20260414-021 ~ CTX-20260414-026`
- Event: Started the next Knowledge slice, focusing on queued Add/Cognify/Memify execution, synchronous Search, knowledge run persistence, and a real Knowledge worker loop.
- Cause: Dataset create/get and the optional Cognee runtime boundary were already stable, so the next contract gap was the actual execution path behind the Knowledge APIs rather than more surface-only endpoints.
- Action: Added a dedicated task batch, expanded the domain/repository targets to cover `knowledge_runs`, `search_requests`, and `search_hits`, and scoped the implementation to a vendor-neutral DB-backed control plane that reuses the existing job table and API authorization stack.
- Prevention: Keep the runtime abstraction and worker semantics aligned with the Parse path so queue behavior, telemetry, and persistence stay portable when a non-SQL queue backend is introduced later.

### 2026-04-14 22:02:10 +08:00 | Parallel UV Validation Collision

- Stage: `CTX-20260414-026`
- Event: A focused validation pass failed on Windows because two `uv run` commands were launched in parallel and both tried to recreate `.venv`, causing an install-path error inside the virtualenv metadata directory.
- Cause: `uv run` eagerly provisions the shared environment, and parallel provisioning against the same workspace `.venv` is not safe on this platform.
- Action: Switched the remaining Ruff, Pyright, and pytest commands to serialized `uv run` execution and continued validation without changing application code.
- Prevention: Avoid parallel `uv run` commands in this repository; parallelize file reads and other independent shell work, but keep Python environment provisioning and test execution serialized.

### 2026-04-14 22:07:18 +08:00 | Shared Module Import Drift During Full Check

- Stage: `CTX-20260414-021 ~ CTX-20260414-026`
- Event: The first full-repository check after the Knowledge worker slice failed on one long validation message plus import-order drift in shared `contracts`, `db`, and `domain` modules that were touched indirectly by the new exports and repositories.
- Cause: Adding new knowledge records, repositories, and contract models widened several import blocks outside the immediate feature files, and the first pass only ran focused lint/type checks rather than the full repository style sweep.
- Action: Wrapped the long `KnowledgeInput` validation error message, ran Ruff auto-fix on the shared modules, and reran the complete `scripts/dev/check.ps1` suite.
- Prevention: After extending shared package exports or repository lists, run a full-repository Ruff pass before the final all-in-one check so import-order fallout is caught earlier.

### 2026-04-14 22:09:36 +08:00 | Knowledge Jobs, Search, And Worker Slice Completed

- Stage: `CTX-20260412-039 ~ CTX-20260412-043`, `CTX-20260414-021 ~ CTX-20260414-026`
- Event: The queued Knowledge execution slice is complete: Add/Cognify/Memify job submission, synchronous Search, knowledge run persistence, search audit trails, and the Knowledge worker `run_once` loop all landed and passed full validation.
- Cause: The project needed the actual execution backbone behind the Knowledge APIs so datasets can move from control-plane metadata into ingest, graph enrichment, and retrieval flows.
- Action: Expanded contracts/domain/ORM/UoW layers for `knowledge_runs` and search audit entities, implemented knowledge job control and execution/search services, exposed `/v1/knowledge/add/jobs`, `/v1/knowledge/cognify/jobs`, `/v1/knowledge/memify/jobs`, and `/v1/knowledge/search`, replaced the worker placeholder with a real poll/execute/heartbeat loop, added contract/integration coverage, and reran `scripts/dev/check.ps1` successfully.
- Prevention: The next Knowledge slice can build on this worker/job/search substrate for richer retry policy, deeper runtime adapters, and broader end-to-end flows without changing the REST contract or persistence model.

### 2026-04-14 22:16:28 +08:00 | OpenAPI Contract Continuation Started

- Stage: `CTX-20260412-045`, `CTX-20260414-027 ~ CTX-20260414-030`
- Event: Started the OpenAPI parity continuation, focusing on the missing `/metrics` endpoint, runtime route metadata drift, and automated contract tests against `specs/cortex-api.yaml`.
- Cause: The implemented REST surface had already covered most business flows, but the published API contract still had parity gaps in observability coverage, path-parameter naming, operation metadata, and DTO schema shape verification.
- Action: Added a dedicated Phase K batch to `specs/cortex-tasks.md` before coding and scoped the work to observability routing, OpenAPI metadata alignment, schema contract testing, and full validation closure.
- Prevention: Keep every new API slice tied to a task batch plus contract tests so runtime drift is detected before more routes or workers are added.

### 2026-04-14 22:22:10 +08:00 | Recurrent UV Managed Python Access Failure

- Stage: `CTX-20260414-029 ~ CTX-20260414-030`
- Event: A direct `uv run --all-packages ...` validation command failed again with `Failed to read Python installation directory: C:\Users\hy\AppData\Roaming\uv\python` and `os error 5`.
- Cause: This is a recurrence of the earlier managed-Python discovery problem recorded on `2026-04-12 21:38:00 +08:00` and `2026-04-13 09:03:00 +08:00`; on this Windows environment, ad hoc `uv run` still sometimes probes the user-scoped managed Python directory before stabilizing on the workspace environment.
- Action: Switched the focused lint/type/test commands to the repository-local `.venv\\Scripts\\ruff.exe`, `.venv\\Scripts\\pyright.exe`, and `.venv\\Scripts\\pytest.exe` entrypoints, then kept the final all-in-one verification on `scripts/dev/check.ps1`.
- Prevention: For manual focused checks in this repository, prefer the workspace `.venv` executables over ad hoc `uv run`; reserve `scripts/dev/check.ps1` for the final repository-wide validation pass.

### 2026-04-14 22:29:40 +08:00 | OpenAPI Schema Drift Exposed By Contract Tests

- Stage: `CTX-20260412-045`, `CTX-20260414-028 ~ CTX-20260414-030`
- Event: The first OpenAPI contract test pass surfaced several DTO/schema mismatches: `JobAccepted` returned top-level `request_id` and `trace_id` while the spec required nested `telemetry`, `StorageUploadSession.status` and `DownloadUrlResponse.method` were optional in generated schemas, `AddJobRequest.inputs` was not required, and `SearchResponse.context_items` plus `latency_ms` were modeled as optional defaults.
- Cause: Earlier feature slices optimized for runtime flow delivery and Pydantic convenience defaults, but those defaults made fields optional in generated JSON Schema even where `cortex-api.yaml` marked them as required.
- Action: Aligned the contract models with the published schema, updated Parse/Knowledge job acceptance payloads to emit `TelemetryContext`, and kept the runtime response shapes synchronized with the spec instead of weakening the contract test.
- Prevention: When introducing or revising contract DTOs, check whether a default value changes required-field semantics in the generated schema; if the OpenAPI document declares a field as required, avoid defaulting it in the Pydantic model unless the spec is updated in the same slice.

### 2026-04-14 22:34:55 +08:00 | OpenAPI Contract Test Resolver Gap

- Stage: `CTX-20260414-029`
- Event: The first schema-signature comparison treated documented `allOf` and `$ref` combinations as empty objects, which produced false negatives on composed schemas such as `ParseJobRequest`.
- Cause: The initial test helper compared only the top-level keys in each schema object and did not resolve OpenAPI composition primitives before extracting required fields and property names.
- Action: Added a small documented-schema resolver in `tests/contract/test_openapi_contract.py` that resolves local component `$ref` values and merges `allOf` object definitions before comparing signatures.
- Prevention: Future contract tests should normalize composed OpenAPI schemas before asserting parity so the test remains resilient as the spec uses more reuse and composition.

### 2026-04-14 22:38:00 +08:00 | OpenAPI Contract Continuation Completed

- Stage: `CTX-20260412-045`, `CTX-20260414-027 ~ CTX-20260414-030`
- Event: The OpenAPI parity slice is complete: `/metrics` is implemented, runtime route metadata now matches the published path and operation contract, selected DTO schemas are checked against `specs/cortex-api.yaml`, and both focused and full validation passed.
- Cause: The project needed a stronger contract boundary before moving deeper into later delivery phases such as broader integration, end-to-end workflows, and CI automation.
- Action: Added the observability router and Prometheus payload helper, aligned FastAPI route paths/operation IDs/summaries/version metadata, introduced contract coverage for paths and schemas, fixed the schema drifts revealed by the new tests, and reran `scripts/dev/check.ps1` successfully with `44 passed`.
- Prevention: Keep the new OpenAPI contract tests in the default validation path and update them alongside any future REST contract change so runtime behavior and `cortex-api.yaml` continue to move in lockstep.

### 2026-04-14 22:41:12 +08:00 | Docker Integration Continuation Started

- Stage: `CTX-20260412-046`, `CTX-20260412-049`, `CTX-20260414-031 ~ CTX-20260414-035`
- Event: Started the next Phase K slice, focusing on a local Docker dependency stack plus docker-backed integration coverage for PostgreSQL, MinIO, and the DB-backed Parse/Knowledge worker flows.
- Cause: The current test suite already validates the control plane heavily with SQLite and fake providers, but the next confidence gap is the real infrastructure boundary described in the specs: PostgreSQL for portable SQL execution and MinIO for S3-compatible storage behavior.
- Action: Added a dedicated task batch before coding and scoped the work to local compose orchestration, docker-backed integration helpers, and focused validation outside the default lightweight repository test path.
- Prevention: Keep stack-backed tests opt-in but first-class, so day-to-day validation stays fast while real dependency coverage remains easy to run before larger delivery milestones and CI expansion.

### 2026-04-14 22:50:30 +08:00 | Local Stack Definition Added

- Stage: `CTX-20260414-031`
- Event: Added a local compose stack, Prometheus scrape config, Grafana datasource provisioning, stack lifecycle PowerShell helpers, and a dedicated docker-backed integration test module for PostgreSQL + MinIO + worker flows.
- Cause: The repository already had OTLP and observability specs, but no runnable local infrastructure bundle or real dependency tests to exercise those boundaries.
- Action: Added `compose.local.yaml`, `scripts/dev/stack.ps1`, `scripts/dev/check-runtime-stack.ps1`, local Prometheus/Grafana config, updated `tests/integration/README.md`, registered a `runtime_stack` pytest marker, and added `tests/integration/test_runtime_stack.py`.
- Prevention: Keep heavy integration tests behind a stable marker and helper scripts so the stack can be invoked consistently without slowing the default inner loop.

### 2026-04-14 22:54:40 +08:00 | Docker Daemon Access Blocked

- Stage: `CTX-20260414-032 ~ CTX-20260414-035`
- Event: `docker compose -f compose.local.yaml config` succeeded, but both `scripts/dev/stack.ps1 ps` and direct Docker commands failed to reach the daemon with `open //./pipe/docker_engine` while `com.docker.service` was stopped; an attempted `Start-Service com.docker.service` also failed because the service could not be opened from this session.
- Cause: The local Docker Desktop client binaries are present, but the Windows Docker service is not available to the current process context, so containers cannot be started from the workspace shell.
- Action: Kept the compose and runtime-test assets in place, verified the stack file renders correctly, ran static lint/type validation plus the default repository suite, and marked the docker-backed execution tasks as `blocked` pending a working daemon.
- Prevention: Before rerunning the runtime-stack slice, confirm Docker Desktop is fully started and the current shell can reach the daemon; once `docker compose ps` succeeds, rerun `powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 up` followed by `scripts\dev\check-runtime-stack.ps1`.

### 2026-04-14 22:56:10 +08:00 | Docker Integration Slice Partially Validated

- Stage: `CTX-20260414-031 ~ CTX-20260414-035`
- Event: The code path for the local stack slice passed repository validation, and the new runtime-stack test module was successfully linted, type-checked, and skipped by default in the full suite, but the real docker-backed execution remains blocked by the daemon issue above.
- Cause: Static and default test validation can proceed without containers, while the actual PostgreSQL/MinIO execution path requires a reachable Docker runtime.
- Action: Ran Ruff and Pyright on `tests/integration/test_runtime_stack.py`, verified `docker compose config`, and reran `scripts/dev/check.ps1` successfully with `44 passed, 1 skipped`.
- Prevention: Keep the runtime-stack tests opt-in until CI or the local environment can guarantee Docker availability, then promote the blocked tasks to done after one successful end-to-end stack-backed run.

### 2026-04-15 09:46:45 +08:00 | CI And Validation Continuation Started

- Stage: `CTX-20260412-048`, `CTX-20260415-001 ~ CTX-20260415-004`
- Event: Started the next continuation slice to close the still-planned CI baseline with reusable validation scripts, a GitHub Actions workflow, and an optional docker-backed runtime-stack job.
- Cause: The REST surface, workers, and local dependency stack now exist, but the repository still lacked a portable CI entrypoint and automated YAML/OpenAPI validation outside the PowerShell-only local check wrapper.
- Action: Added a new Phase K task batch before coding, rechecked the Docker state, and confirmed the local daemon is still unavailable (`docker ps` permission denied, `com.docker.service` stopped), so the implementation is being scoped first to unblocked CI and validation work that can later execute the runtime stack in CI where Docker is available.
- Prevention: Keep future delivery slices tied to both local scripts and CI automation so contract drift, config regressions, and infrastructure readiness failures are surfaced early even when the current workstation cannot start containers.

### 2026-04-15 09:51:20 +08:00 | GitHub Workflow YAML Needed `on` Key Normalization

- Stage: `CTX-20260415-001 ~ CTX-20260415-003`
- Event: The first pass of the new YAML validator could parse `.github/workflows/ci.yaml`, but the `on:` trigger block was not reachable through the usual `"on"` key lookup.
- Cause: `yaml.safe_load` follows YAML 1.1 implicit boolean resolution, so GitHub Actions' literal `on:` key can be loaded as boolean `True` instead of the string `"on"`.
- Action: Normalized workflow parsing in `scripts/ci/validate_yaml.py` to accept either `"on"` or `True`, then added structural assertions for `workflow_dispatch` inputs plus the required `quality` and `runtime-stack` job commands.
- Prevention: Any future tooling that parses GitHub workflow YAML in this repository should account for YAML 1.1 boolean coercion or use a parser mode that preserves `on` as a literal key.

### 2026-04-15 09:52:05 +08:00 | Recurrent Ruff Non-Python Path Misparse

- Stage: `CTX-20260415-001 ~ CTX-20260415-004`
- Event: A focused Ruff invocation produced a large burst of syntax errors after `.github/workflows/ci.yaml` and `scripts/dev/check.ps1` were passed directly on the command line.
- Cause: This repeats the same class of issue seen in earlier ad hoc checks: Ruff auto-discovers Python files safely when pointed at the repository or Python directories, but explicit non-Python file arguments make it try to parse YAML and PowerShell as Python source.
- Action: Moved workflow verification into `scripts/ci/validate_yaml.py`, limited focused Ruff checks to Python paths, and reran targeted plus full validation successfully.
- Prevention: For focused linting in this repository, pass only Python files or directories to Ruff; use dedicated validators for YAML, PowerShell, and other config assets.

### 2026-04-15 09:53:40 +08:00 | CI And Validation Continuation Completed

- Stage: `CTX-20260412-048`, `CTX-20260412-049`, `CTX-20260415-001 ~ CTX-20260415-004`
- Event: The CI baseline is now in place with a reusable cross-platform validation entrypoint, YAML/OpenAPI config validation, a GitHub Actions quality workflow, and an optional runtime-stack CI job.
- Cause: The repository had already reached a meaningful REST and worker milestone, so the next leverage point was to turn the documented contracts and local stack into a repeatable automation path instead of relying only on manual checks.
- Action: Added `scripts/ci/check.py`, `scripts/ci/validate_yaml.py`, `scripts/ci/wait_for_runtime_stack.py`, `.github/workflows/ci.yaml`, refreshed `scripts/ci/README.md`, wired `scripts/dev/check.ps1` into YAML/OpenAPI validation, and reran targeted checks plus `powershell -ExecutionPolicy Bypass -File scripts\dev\check.ps1` successfully (`44 passed, 1 skipped`).
- Prevention: Keep `scripts/ci/check.py` and `scripts/ci/validate_yaml.py` as the shared contract for local and CI validation so new API slices extend one verification path instead of creating parallel check logic.

### 2026-04-15 09:57:17 +08:00 | Docker Availability Differs Between Local Shell And Codex Session

- Stage: `CTX-20260414-032 ~ CTX-20260414-035`
- Event: After the operator confirmed Docker works in their own Git Bash / PowerShell sessions, this Codex-controlled shell still could not reach the daemon: `docker version` and `docker ps` both failed on `npipe:////./pipe/docker_engine`, and `com.docker.service` remained `Stopped` from the session's perspective.
- Cause: The workstation may now have a usable Docker context for the operator, but the current Codex execution context still has a session-level permission or service-visibility mismatch around the Windows Docker pipe and `C:\Users\hy\.docker\config.json`.
- Action: Kept the docker-backed validation tasks blocked for this session, recorded the environment mismatch explicitly, and pivoted to the next unblocked testing slice instead of repeatedly retrying daemon-dependent commands.
- Prevention: When a tool-run context differs from the user's interactive shell on Windows, validate daemon reachability inside the Codex session itself before planning stack-backed execution; if the mismatch persists, continue with non-daemon work and resume stack validation once the agent context can access Docker.

### 2026-04-15 10:04:10 +08:00 | Temp Directory Fixtures Fail In This Workspace Context

- Stage: `CTX-20260415-005 ~ CTX-20260415-007`
- Event: The first unit-test pass failed when new parse-profile tests used `tmp_path` and then `TemporaryDirectory()`: pytest could not initialize the disabled `tmpdir` plugin path, and direct writes under `C:\Users\hy\AppData\Local\Temp` raised `PermissionError`.
- Cause: This repository intentionally disables pytest's `tmpdir` plugin in `pyproject.toml`, and the current Codex workspace context does not reliably allow scratch writes under the user temp directory.
- Action: Reworked the parse-profile unit tests to create isolated case directories under the repository-local `runtime-test-data` tree, which already matches the rest of the test suite's Windows-safe scratch pattern.
- Prevention: In this workspace, prefer repository-local scratch directories over `tmp_path`, `tmpdir`, or system temp locations when adding tests that write fixtures or ephemeral files.

### 2026-04-15 10:06:00 +08:00 | Unit Coverage Continuation Completed

- Stage: `CTX-20260412-044`, `CTX-20260415-005 ~ CTX-20260415-007`
- Event: The package-level unit coverage slice is complete for `common`, `auth`, `storage`, `parse`, and `knowledge`, closing the remaining non-Docker unit-testing gap.
- Cause: After the Docker-backed validation remained blocked in this agent context, the next highest-value path was to strengthen package-level confidence around pure settings, token, storage, profile, and knowledge helper logic.
- Action: Added focused unit tests under `tests/unit` for settings cache/boolean normalization, auth token parsing and fallback chains, S3 bucket provisioning decisions, parse profile loading and registry filtering, and optional knowledge runtime/search/helper normalization; then reran focused checks plus `powershell -ExecutionPolicy Bypass -File scripts\dev\check.ps1` successfully (`62 passed, 1 skipped`).
- Prevention: Keep expanding test coverage with pure unit slices before reaching for heavier integration paths so package behavior stays fast to validate even when external runtimes are unavailable from the current session.

### 2026-04-15 10:44:36 +08:00 | Unified Runtime Config Continuation Started

- Stage: `CTX-20260415-008 ~ CTX-20260415-011`
- Event: Started a dedicated continuation slice to centralize provider runtime configuration for Crawl4AI, Jina Reader, LlamaParse, MarkItDown, Docling, and Cognee into one Cortex-owned runtime YAML plus loader.
- Cause: The current implementation still splits runtime intent across env-driven `settings`, adapter-local defaults, and per-request/profile overrides, which makes real deployment setup harder to audit and reason about.
- Action: Added a new Phase L task batch before coding, re-audited the adapter/bootstrap entry points, and scoped the implementation to a checked-in runtime config file, secret-reference resolution, parse/knowledge bootstrap wiring, and focused unit coverage.
- Prevention: Keep provider defaults and deployment-specific behavior in one versioned runtime config contract, and reserve `.env` for secret material or coarse path overrides instead of scattering engine behavior across unrelated files.

### 2026-04-15 11:04:20 +08:00 | Unified Runtime Config Continuation Completed

- Stage: `CTX-20260415-008 ~ CTX-20260415-011`
- Event: The runtime-config unification slice is complete: parse engines and Cognee now read from one checked-in `configs/cortex.runtime.yaml`, `.env` only holds secret/path inputs, and both API/worker bootstraps consume the same loader.
- Cause: Real deployment setup needed a single operational source of truth for provider defaults and secret references, instead of splitting those knobs across adapter-local defaults and scattered environment variables.
- Action: Added `cortex_common.runtime_config`, wired `RuntimeConfigSettings` into global settings, created `configs/cortex.runtime.yaml`, updated `.env.example`, connected Parse bootstrap plus Crawl4AI/Jina/LlamaParse/MarkItDown/Docling adapters to central defaults, mapped Cognee runtime config into `cognee.config.*`, refreshed `specs/cortex-tech.md`, and added focused unit/integration coverage for loader, bootstrap, and adapter wiring. Validation passed with `14` focused tests and `powershell -ExecutionPolicy Bypass -File scripts\dev\check.ps1` (`65 passed, 1 skipped`).
- Prevention: Keep future provider additions behind the same runtime-config contract, and treat `.env` as a secret/reference layer only; if a new adapter needs its own knobs, add them to `configs/cortex.runtime.yaml` plus loader/tests in the same change.

### 2026-04-15 11:31:02 +08:00 | Runtime Overlay Configs Continuation Started

- Stage: `CTX-20260415-012 ~ CTX-20260415-013`
- Event: Started a small follow-up slice to materialize the unified runtime-config model into three operator-facing files for `local`, `staging`, and `prod`.
- Cause: The shared baseline file proved the config contract, but real integration testing needs environment-specific files that can be switched with `CORTEX_RUNTIME_CONFIG_PATH` instead of manual in-place edits.
- Action: Added a dedicated task batch before editing, scoped the work to three complete runtime YAML files plus path/example refresh, and kept the provider choices aligned with the just-confirmed plan: LlamaParse via cloud API, Kuzu-first graph storage.
- Prevention: Prefer explicit environment files over ad hoc last-minute edits to one config so promotion from local to staging to prod remains reviewable and repeatable.

### 2026-04-15 11:34:10 +08:00 | Runtime Overlay Configs Continuation Completed

- Stage: `CTX-20260415-012 ~ CTX-20260415-013`
- Event: Added explicit `local`, `staging`, and `prod` runtime config files under `configs/`, switched the default runtime-config path to `configs/cortex.runtime.local.yaml`, and aligned the examples with Kuzu-first graph storage plus LlamaParse cloud mode.
- Cause: The operator needed ready-to-fill environment files for real integration testing instead of editing one shared YAML by hand before each run.
- Action: Created `configs/cortex.runtime.local.yaml`, `configs/cortex.runtime.staging.yaml`, and `configs/cortex.runtime.prod.yaml`; kept local on `kuzu`, moved staging/prod to `kuzu-remote`, set staging/prod vector storage to `pgvector`, refreshed `.env.example` and `specs/cortex-tech.md`, added unit coverage that loads all three files, and reran focused validation plus `powershell -ExecutionPolicy Bypass -File scripts\dev\check.ps1` successfully (`68 passed, 1 skipped`).
- Prevention: When introducing new runtime environments, clone one of the explicit overlay files and keep all environment-specific endpoints and secrets behind `_ref` fields so promotion stays diffable and the loader behavior remains consistent.

### 2026-04-15 12:12:26 +08:00 | Local Runtime Stack Validation Continuation Started

- Stage: `CTX-20260415-014 ~ CTX-20260415-017`
- Event: Started the next phase to resume the previously blocked docker-backed local runtime validation path after the operator filled `.env` and `cortex.runtime.local.yaml`.
- Cause: The repository-level contract and provider wiring are in place, but the remaining confidence gap is still the real local environment boundary: PostgreSQL, MinIO, Redis, OTel, the populated runtime config, and live REST + worker execution.
- Action: Added a dedicated Phase M task batch before execution, scoped the work to daemon reachability, compose startup, docker-backed tests, live API/worker exercise, and validation/log closure.
- Prevention: Treat environment-backed validation as its own tracked phase with explicit startup, test, runtime, and closure tasks so blocked infrastructure issues do not get mixed into pure code-delivery slices.

### 2026-04-15 14:16:18 +08:00 | Docker Daemon Reachability Still Diverges Inside Codex Session

- Stage: `CTX-20260415-014`
- Event: Rechecked Docker from the current Codex-controlled shell and it still could not reach `npipe:////./pipe/docker_engine`; `docker version` and `docker ps` both failed, even after redirecting `DOCKER_CONFIG` into a workspace-local directory to avoid the `C:\\Users\\hy\\.docker\\config.json` access warning.
- Cause: The operator's interactive shell may have a working Docker context, but this agent session still sees a Windows pipe/service visibility or permission mismatch around the Docker daemon endpoint.
- Action: Kept the docker-backed stack startup and MinIO/PostgreSQL/Redis validation blocked for this session, recorded the recurrence, and continued with non-docker live validation that can still exercise the configured API and worker paths.
- Prevention: On this workstation, always validate Docker daemon access from the active Codex session itself before scheduling compose-backed work; if the pipe is unreachable here, treat daemon-dependent tasks as blocked even when the user's own terminal works.

### 2026-04-15 14:16:18 +08:00 | Optional Provider Runtime Sync Blocked By Temp Or Build Artifact Permissions

- Stage: `CTX-20260415-014`
- Event: Tried to install live provider extras for Parse and Knowledge using `uv sync --all-packages --all-groups --extra runtime` and narrower package-scoped syncs, but the runs failed while building wheels for transitive dependencies such as `langdetect` and `pylatexenc`; even `ensurepip` hit `PermissionError` in temporary wheel extraction paths.
- Cause: The current Codex workspace context still has a broader permission problem around temporary build directories and wheel artifacts, which affects source-build dependency installation even when the temporary directory is redirected into the workspace.
- Action: Added optional `runtime` dependency groups to the Parse and Knowledge packages to formalize provider installation, documented the intended sync command, and then deferred full live provider installation once the permission issue blocked the build path.
- Prevention: For this workspace context, prefer validating providers that do not need local binary/source installs first, and treat heavy optional runtime setup as a separate environment-readiness step until temporary build paths are writable end to end.

### 2026-04-15 14:29:43 +08:00 | SQLite Runtime Path Was Not Prepared Before First Live Migration

- Stage: `CTX-20260415-016`
- Event: The first live API validation attempt failed before startup because Alembic could not open `sqlite:///./.data/cortex.db`; the configured file-backed SQLite parent directory did not exist yet.
- Cause: Both the migration CLI and async engine bootstrap assumed the parent directory for file-backed SQLite DSNs already existed, which is not guaranteed in a fresh local environment.
- Action: Added `ensure_sqlite_database_path(...)` to the DB engine layer, invoked it from both `create_database_engine(...)` and `build_alembic_config(...)`, added focused unit coverage, and reran the live validation successfully past migration/startup.
- Prevention: Treat file-backed SQLite DSNs as real filesystem resources that need parent-directory preparation at the shared DB bootstrap layer instead of expecting operators to create directories by hand.

### 2026-04-15 14:29:43 +08:00 | Live Runtime Validation Exposed Provider-Readiness And Error-Mapping Gaps

- Stage: `CTX-20260415-016`
- Event: The local API and worker stack was launched successfully against the populated `.env` and `configs/cortex.runtime.local.yaml`, and a real HTTP validation run was recorded at `runtime-test-data/live-runtime-compact-1776234366955494500/summary.json`.
- Cause: The code path was ready for real execution, so the remaining failures came from provider readiness and runtime observability boundaries instead of missing API implementation.
- Action: Verified `/metrics`, `/openapi.json`, `/v1/health/live`, `/v1/health/ready`, Parse engine/profile catalog endpoints, Knowledge dataset creation, and worker/job-event execution on the live stack; then fixed two runtime-debugging gaps uncovered by the run: Parse failures now surface per-engine attempt details (for example the Jina Reader `401 Unauthorized`), and storage connectivity failures now return `storage_endpoint_unreachable` (`503`) instead of collapsing into an opaque internal `500`.
- Findings:
  - Parse runtime currently exposes only `jina_reader` as active, and live Parse requests fail because the configured Jina Reader call returns `401 Unauthorized`, which strongly indicates a missing or invalid Reader credential in the local runtime config / secret reference path.
  - Knowledge control-plane endpoints and queued Add jobs run, but live Knowledge execution and Search fail with `config_error: Cognee runtime module is unavailable`, which matches the earlier optional-provider installation block in this Codex session.
  - Storage upload-session creation now fails explicitly with `storage_endpoint_unreachable` for `http://127.0.0.1:9000`, confirming that the local S3-compatible endpoint is not reachable from this session while Docker-backed MinIO remains blocked.
  - OTLP export remained configured and the API stayed healthy, but the process logged connection-refused export warnings for `http://127.0.0.1:4318/v1/traces`, confirming that an OTel collector is not currently reachable from the Codex session.
  - Because the live run used the configured shared SQLite database, the Parse worker picked up an older queued Parse job before the newly submitted one; this is expected queue behavior on a reused local DB but means worker validation is cleaner against an isolated DB or an emptied queue.
- Prevention: Keep real-environment validation outcomes split into code fixes versus provider-readiness blockers, and prefer explicit, provider-specific failure surfaces so operators can map a failing live request directly back to the missing credential, package, or endpoint.

### 2026-04-15 14:29:43 +08:00 | Phase M Validation Closure Completed

- Stage: `CTX-20260415-017`
- Event: The repository-wide validation pass succeeded after the runtime fixes and log updates.
- Cause: The code changes from this phase were limited to DB bootstrap hardening, Parse failure diagnostics, Storage error mapping, and their focused tests.
- Action: Reran `powershell -ExecutionPolicy Bypass -File scripts\\dev\\check.ps1` successfully, including YAML/OpenAPI validation, Ruff, Pyright, and pytest (`73 passed, 1 skipped`), then marked the task batch with Docker-specific steps still blocked and live API/runtime validation completed.
- Prevention: After each live-runtime debugging slice, rerun the full repository validation before closing the batch so local environment discoveries do not leave hidden type, lint, or contract regressions behind.

### 2026-04-15 17:18:17 +08:00 | PowerShell `$Host` Name Collision Broke Runtime Stack Wait Script

- Stage: `CTX-20260415-014`
- Event: The operator successfully started all Docker containers with `scripts\\dev\\stack.ps1 up`, but the script then failed while entering the readiness checks with `Cannot overwrite variable Host because that variable is read-only or constant.`
- Cause: `Wait-TcpReady` declared a parameter named `Host`, which collides with PowerShell's built-in read-only `$Host` variable.
- Action: Renamed the helper parameter to `HostName` in `scripts\\dev\\stack.ps1`, leaving the runtime stack startup logic unchanged while removing the PowerShell variable collision.
- Prevention: Avoid parameter or local-variable names that shadow PowerShell automatic or built-in variables (`$Host`, `$PID`, `$Error`, etc.) in operator scripts, especially in shared helper functions reused across startup flows.

### 2026-04-15 17:27:28 +08:00 | Docker-Backed Runtime Tests Exposed Hidden Postgres Referential Assumptions

- Stage: `CTX-20260415-015`
- Event: Once the operator-provided localhost stack was ready, `tests/integration/test_runtime_stack.py` initially failed on PostgreSQL foreign keys for `tenant_id` and `created_by` while the same flows had previously passed under SQLite-centric validation.
- Cause: The runtime-stack tests were exercising service/worker layers directly, bypassing the API auth path that auto-provisions tenant/actor records in `dev` mode; SQLite had also masked some of these assumptions during earlier non-Postgres validation.
- Action: Updated the docker-backed runtime tests to provision tenant and actor fixtures explicitly before direct storage/parse/knowledge writes, and adjusted Knowledge Add counter handling so provider-reported counters are honored instead of relying only on local item-type heuristics.
- Prevention: When service-level tests bypass auth/bootstrap layers, seed every referential prerequisite explicitly; also keep Postgres-backed tests in the loop because they surface integrity assumptions that SQLite can hide.

### 2026-04-15 17:27:28 +08:00 | Live Docker-Backed API Validation Passed Storage And Core Health, With Parse Or Knowledge Provider Gaps Remaining

- Stage: `CTX-20260415-016`
- Event: Ran a full live API/worker verification against the operator-started localhost stack and recorded the result at `runtime-test-data/live-runtime-postgres-1776245158854128000/summary.json`.
- Cause: Docker-backed infrastructure was now reachable from the Codex session through localhost even though direct Docker daemon control in the session remains blocked.
- Action: Verified successful `/metrics`, `/openapi.json`, `/v1/health/live`, `/v1/health/ready`, storage upload/complete/metadata/download, parse job submission/worker retry flow, knowledge dataset creation, and knowledge job submission/worker/job-event persistence against PostgreSQL + MinIO + Redis + OTel Collector.
- Findings:
  - Storage is fully healthy on the live stack: presigned upload, object completion, metadata retrieval, and presigned download all succeeded against MinIO.
  - Readiness stayed healthy throughout the live run, and OTLP export no longer emitted the earlier connection-refused warnings once the collector was available on `http://127.0.0.1:4318`.
  - Parse still fails at the provider layer because the active Jina Reader request returns `401 Unauthorized`, which strongly indicates a missing or invalid `JINA_API_KEY` for the current runtime config.
  - Knowledge control-plane endpoints and queued job persistence are healthy, but execution/search remain blocked by `config_error: Cognee runtime module is unavailable`, which matches the still-missing optional provider installation in this Codex session.
- Prevention: Keep infrastructure validation separate from provider-readiness validation so a healthy stack can be distinguished cleanly from missing third-party credentials or optional Python runtime packages.

### 2026-04-15 17:27:28 +08:00 | Runtime Validation Closure Updated After Docker-Backed Pass

- Stage: `CTX-20260415-017`
- Event: Closed the current runtime-validation slice with both standard repository validation and docker-backed runtime-stack tests passing.
- Cause: The only remaining blockers after the Docker-backed pass are provider-specific readiness issues (Jina credential and Cognee runtime package), not the REST API, worker queueing, or core infrastructure stack.
- Action: Reran `powershell -ExecutionPolicy Bypass -File scripts\\dev\\check.ps1` successfully, reran `tests/integration/test_runtime_stack.py` successfully with `CORTEX_RUNTIME_STACK=1`, updated task status so `CTX-20260415-015` is now done, and left only the direct Docker-daemon control task blocked for this session.
- Prevention: After an operator assists with a blocked infrastructure dependency, rerun both the normal repo checks and the dedicated infrastructure-backed tests so task state reflects the real remaining gap instead of the original blocker.

### 2026-04-15 17:46:59 +08:00 | Provider Revalidation Continuation Started

- Stage: `CTX-20260415-018 ~ CTX-20260415-020`
- Event: Started a focused provider revalidation slice after the operator confirmed `JINA_API_KEY` is correct in `.env` and installed the optional `cognee` dependency into the active `.venv`.
- Cause: The previous live runtime pass showed healthy infrastructure but still failed specifically at the Jina Reader provider boundary (`401 Unauthorized`) and the optional Cognee runtime boundary (`module is unavailable`), so the next step is to re-check those exact assumptions instead of reworking the general stack.
- Action: Added a targeted follow-up batch in `specs/cortex-tasks.md`, avoided the full `scripts\\dev\\check.ps1` path until provider verification is finished to prevent accidental `.venv` recreation, and started direct provider/runtime visibility checks before re-running the live API + worker flows.
- Prevention: When an operator changes credentials or optional-package state out of band, perform a narrow provider/runtime retest first so the result isolates configuration propagation from unrelated infrastructure or repository-wide validation noise.

### 2026-04-15 18:09:17 +08:00 | Jina Reader And Cognee Module Visibility Recovered In The Current Session

- Stage: `CTX-20260415-018`
- Event: Re-ran direct provider visibility checks inside the active Codex session using `.venv-codex`.
- Cause: The previous provider failure could have come either from stale runtime caching or from the optional provider environment still not being visible in the current Python process.
- Action: Confirmed `tests/unit/test_runtime_config.py` and `tests/unit/test_cognee_runtime_adapter.py` both pass in `.venv-codex`; then verified Jina Reader directly against `https://r.jina.ai/https://example.com/` with `200 OK`, and confirmed `build_cognee_runtime(...)` now reports `descriptor.status == active` with version `0.5.8`.
- Prevention: When `.venv` provenance is uncertain, run provider-level direct calls in the same Python environment that will execute the API and workers before assuming the remaining failures are in application code.

### 2026-04-15 18:12:15 +08:00 | TestClient Worker Revalidation Initially Mixed Event Loops

- Stage: `CTX-20260415-019`
- Event: The first live provider revalidation script reached successful `/v1/health/*`, `/metrics`, `/v1/parse/engines`, `/v1/parse/profiles`, and `POST /v1/parse/sync`, but failed on the first `ParseWorker.run_once()` call with `RuntimeError: ... got Future ... attached to a different loop`.
- Cause: The revalidation harness was calling `asyncio.run(...)` from outside FastAPI `TestClient`'s own anyio loop, so the worker attempted to reuse an async SQLAlchemy session factory that had been created on a different event loop.
- Action: Switched the harness to execute async worker calls via `TestClient.portal.call(...)`, keeping worker execution on the same loop as the API lifespan-managed async engine and session factory.
- Prevention: When an in-process live validation script mixes `TestClient` with async workers, use the client's blocking portal or an all-async ASGI test harness; do not wrap worker calls in a separate `asyncio.run(...)`.

### 2026-04-15 18:14:39 +08:00 | Cognee 0.5.8 Exposed Monitoring And Memify Compatibility Gaps

- Stage: `CTX-20260415-019`
- Event: After the loop issue was removed, live Knowledge Add/Cognify/Search immediately failed because the runtime config used `monitoring_tool: noop`, while `cognee 0.5.8` only accepts `none` or `langfuse`; Memify also failed because `create_triplet_embeddings(...)` and `persist_sessions_in_knowledge_graph_pipeline(...)` require a `user` argument.
- Cause: The Cortex-owned vendor-neutral config surface and the initial Cognee adapter implementation had not yet translated those current Cognee 0.5.8 API expectations.
- Action: Updated `packages/knowledge/src/cortex_knowledge/runtime.py` so vendor-neutral monitoring values like `noop` are normalized to `none`, memify pipeline calls resolve and inject Cognee's default user automatically when the callable accepts `user`, and added focused coverage in `tests/unit/test_runtime_config.py` and `tests/unit/test_cognee_runtime_adapter.py`.
- Prevention: Keep the runtime adapter as the only compatibility boundary between Cortex-owned config semantics and provider-specific APIs, and add focused tests whenever a live provider run reveals a concrete signature or enum mismatch.

### 2026-04-15 18:21:04 +08:00 | Provider Revalidation Closed With Parse Restored And Knowledge Blocked By Upstream OpenAI Quota

- Stage: `CTX-20260415-019 ~ CTX-20260415-020`
- Event: Re-ran the live provider validation end to end and recorded the result at `runtime-test-data/live-provider-retest-1776248213840440500/summary.json`.
- Cause: The local Docker-backed infrastructure, Jina Reader credential path, and Cognee module wiring were now healthy enough to execute real provider calls; the remaining failures came from the upstream LLM account state used by Cognee.
- Action: Verified `GET /v1/health/live`, `GET /v1/health/ready`, `GET /metrics`, `GET /v1/parse/engines`, `GET /v1/parse/profiles`, `POST /v1/parse/sync`, `POST /v1/parse/jobs`, and `ParseWorker.run_once()` all succeeded against the live PostgreSQL/Redis/OTel-backed stack with `jina_reader`; then re-ran `tests/integration/test_api_knowledge.py` successfully after the adapter patch. The same live run showed all current Knowledge executions fail for upstream reasons:
  - Add now reaches Cognee's real LLM connection flow, but fails with repeated `RateLimitError` / quota exhaustion from the configured OpenAI account.
  - Cognify and Memify no longer fail on adapter/config mismatches, but still cannot complete because the LLM connection check times out after the upstream quota/connectivity problem.
  - Search reaches the real provider path but aborts with an `InstructorRetryException` rooted in the same upstream OpenAI quota exhaustion, so the in-process test harness records a fatal provider exception before a JSON HTTP error body can be captured.
- Prevention: Separate provider compatibility fixes from provider-account readiness; once the adapter is healthy, capture the exact upstream quota/timeout failure and stop changing application code unless the failure surface itself is misleading.

### 2026-04-15 18:31:42 +08:00 | IDE Import Resolution Failed Because Pyright Targeted A Sparse `.venv`

- Stage: `CTX-20260415-021`
- Event: Investigated the local IDE error `Import "cortex_contracts" could not be resolved` and reproduced it directly with `.venv\\Scripts\\python.exe` and `.venv\\Scripts\\pyright.exe`.
- Cause: The repository already pointed Pyright at `.venv`, but earlier live-provider work had installed the full editable workspace into `.venv-codex` instead, leaving `.venv` present but missing all workspace-owned packages such as `cortex_common` and `cortex_contracts`.
- Action: Verified that `.venv-codex` could import the workspace packages while `.venv` could not, then selected `.venv` as the canonical environment to repair instead of changing the repository-wide Pyright target to a one-off alternate venv name.
- Prevention: Keep one canonical project environment named `.venv` for editor tooling, and avoid leaving the full editable workspace installed only in an alternate venv when repo config and IDE analyzers are pinned to `.venv`.

### 2026-04-15 18:33:18 +08:00 | Canonical `.venv` Was Re-Synced With The Full `uv workspace`

- Stage: `CTX-20260415-022`
- Event: Rebuilt the canonical `.venv` as a complete editable workspace environment.
- Cause: Fixing the IDE import errors required the actual interpreter behind `.venv` to contain the workspace package `.pth` entries for every local package/app/worker, not just third-party dependencies.
- Action: Ran `uv sync --all-groups --all-packages` with `UV_PROJECT_ENVIRONMENT=.venv`, which installed editable entries for `cortex-api`, `cortex-common`, `cortex-contracts`, `cortex-db`, `cortex-parse`, `cortex-knowledge`, both workers, and the other local packages; then verified direct imports from `.venv\\Scripts\\python.exe`.
- Prevention: When bootstrapping or repairing the project environment, use `uv sync --all-groups --all-packages` against `.venv` so the entire workspace is installed consistently for both runtime execution and IDE analysis.

### 2026-04-15 18:35:44 +08:00 | Local IDE Settings Were Anchored To The Canonical `.venv`

- Stage: `CTX-20260415-023`
- Event: Added a local workspace IDE configuration file at `.vscode\\settings.json`.
- Cause: Even after `.venv` was repaired, VS Code / Pylance could still remember a previously selected interpreter or miss some `src` roots during analysis until the workspace was nudged back to the canonical environment.
- Action: Configured the default interpreter path to `${workspaceFolder}\\.venv\\Scripts\\python.exe`, enabled terminal auto-activation, and added all workspace `src` directories to `python.analysis.extraPaths` so editor analysis resolves the `cortex_*` packages deterministically.
- Prevention: In multi-package `src`-layout Python workspaces, keep a workspace-local IDE setting that pins the interpreter and analysis roots, even if the repository also carries Pyright settings in `pyproject.toml`.

### 2026-04-15 18:37:53 +08:00 | Import And Type-Check Validation Passed On The Repaired `.venv`

- Stage: `CTX-20260415-024`
- Event: Validation completed successfully after repairing `.venv`.
- Cause: The import-resolution problem was environmental rather than a systemic packaging design flaw, so once the correct venv contents and interpreter target were restored, editor/static-analysis behavior stabilized.
- Action: Verified direct imports for all workspace packages from `.venv\\Scripts\\python.exe`, reran full `pyright` with `0 errors`, and reran the focused Cognee/runtime unit tests successfully. Also fixed one genuine type-check issue in `packages\\knowledge\\src\\cortex_knowledge\\runtime.py` that surfaced once imports were resolving cleanly again.
- Prevention: Use full-environment validation after fixing IDE resolution issues, because a missing-import problem can mask real type errors that only become visible once the analyzer is looking at the right environment.
