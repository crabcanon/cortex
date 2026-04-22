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

### 2026-04-15 19:08:00 +08:00 | Phase N End-To-End Main Path Continuation Started

- Stage: `CTX-20260415-025 ~ CTX-20260415-027`
- Event: Started the final planned E2E testing slice to close the still-open `upload -> parse -> add -> search` path.
- Cause: The repository already had focused storage, parse, knowledge, and docker-backed runtime coverage, but `CTX-20260412-046` / `CTX-20260412-047` were still open because the full REST + worker + persistence chain had not yet been exercised in one deterministic test.
- Action: Chose a deterministic strategy based on SQLite plus fake object-store / parse / knowledge runtimes while still using the real FastAPI routes, auth path, SQL persistence, and worker `run_once()` loops.
- Prevention: Keep “control-plane closure” tests separate from live-provider tests so E2E confidence does not depend on external quotas, credentials, or transient network behavior.

### 2026-04-15 19:19:00 +08:00 | TestClient Portal Optional Typing Gap Recurred During Worker-Backed E2E

- Stage: `CTX-20260415-027`
- Event: After the new E2E test passed under `pytest`, `pyright` still reported `client.portal.call(...)` as invalid because `portal` is typed as optional on `TestClient`.
- Cause: The runtime lifecycle inside `with TestClient(...)` guarantees the portal exists, but static analysis only sees the broader optional attribute contract.
- Action: Added an explicit `assert client.portal is not None` before invoking Parse and Knowledge worker runs through the in-process portal.
- Prevention: Whenever a test uses `TestClient.portal` to keep async workers on the same event loop as the app lifespan, add an explicit non-null guard so type-checking and runtime lifecycle assumptions stay aligned.

### 2026-04-15 19:23:00 +08:00 | Phase N End-To-End Main Path Validation Completed

- Stage: `CTX-20260412-046`, `CTX-20260412-047`, `CTX-20260415-025 ~ CTX-20260415-027`
- Event: The main-path integration flow is now covered end to end in `tests/integration/test_api_e2e.py`.
- Cause: The remaining gap was not missing API implementation, but missing one deterministic test that proved the storage control plane, async parse queue, knowledge add queue, and synchronous search all compose correctly.
- Action: Added a single API-level E2E test that verifies upload initialization/completion/download, async Parse job submission + `ParseWorker.run_once()`, dataset creation, Add job submission + `KnowledgeWorker.run_once()`, Search response content, and persisted object / parse-run / knowledge-run / search-request state. Validation passed with:
  - `.\.venv\Scripts\python.exe -m ruff check tests/integration/test_api_e2e.py`
  - `.\.venv\Scripts\pyright.exe`
  - `.\.venv\Scripts\python.exe -m pytest tests/integration/test_api_storage.py tests/integration/test_api_parse.py tests/integration/test_api_knowledge.py tests/integration/test_api_e2e.py -q`
- Prevention: For future workflow additions, extend this style of deterministic API-level chain test first, then keep live-provider validation as a separate readiness layer on top.

### 2026-04-15 19:34:00 +08:00 | Phase O Docker-Backed Test Closure Continuation Started

- Stage: `CTX-20260415-028 ~ CTX-20260415-030`
- Event: Started a cleanup pass for the stale docker-backed tasks that still showed `blocked` even though later runtime-stack work had already landed.
- Cause: The repository had accumulated two truths at once: direct Docker control from the Codex session was flaky, but localhost-backed runtime-stack tests and live runtime validation had already been passing with operator-started containers.
- Action: Added a dedicated reconciliation batch to re-check Docker reachability from the current session, rerun the runtime-stack test slice explicitly, and decide which historical blocked tasks could now be closed.
- Prevention: When a later batch effectively supersedes an earlier blocked task, add an explicit reconciliation step instead of leaving contradictory task states around indefinitely.

### 2026-04-15 19:36:00 +08:00 | Docker CLI Is Still Blocked In This Codex Session Even Though Localhost Stack Is Reachable

- Stage: `CTX-20260415-029`, `CTX-20260415-014`
- Event: Re-checking Docker from the current Codex session with `docker ps` still failed.
- Cause: The session cannot read `C:\Users\hy\.docker\config.json` and still receives `permission denied while trying to connect to the docker API at npipe:////./pipe/docker_engine`, so direct CLI/daemon control remains unavailable here.
- Action: Kept `CTX-20260415-014` in the `blocked` state, but proceeded with stack-backed testing against the already-running localhost services because the inability to drive the daemon directly does not prevent validation of PostgreSQL/MinIO-backed behavior once the stack is up.
- Prevention: Treat “docker daemon controllable from Codex” and “runtime stack reachable over localhost” as two separate readiness checks; only the first one should gate daemon-management tasks.

### 2026-04-15 19:42:00 +08:00 | Docker-Backed Runtime Stack Validation Reconfirmed On Canonical `.venv`

- Stage: `CTX-20260414-032 ~ CTX-20260414-035`, `CTX-20260415-030`
- Event: Re-ran the stack-backed integration slice against the current localhost stack from the canonical `.venv`.
- Cause: The stale `blocked` status on the historical docker-backed tasks needed fresh evidence in the current session before being cleared.
- Action: Validation passed with:
  - `$env:CORTEX_RUNTIME_STACK='1'; .\.venv\Scripts\python.exe -m pytest tests/integration/test_runtime_stack.py -q`
  - `.\.venv\Scripts\pyright.exe`
  - `.\.venv\Scripts\python.exe -m ruff check tests/integration/test_runtime_stack.py tests/integration/test_api_e2e.py`
  These runs re-confirmed coverage for PostgreSQL migration / repository round-trip, MinIO presigned upload/download, Parse worker execution on PostgreSQL, and Knowledge worker execution on PostgreSQL.
- Prevention: When a runtime-stack slice is healthy but daemon control is blocked, keep one explicit pytest entrypoint (`tests/integration/test_runtime_stack.py`) as the canonical proof that infrastructure-backed behaviors still work end to end.

### 2026-04-15 19:42:00 +08:00 | Historical Docker-Backed Testing Tasks Closed, Direct Daemon Task Still Blocked

- Stage: `CTX-20260414-032 ~ CTX-20260414-035`, `CTX-20260415-028 ~ CTX-20260415-030`
- Event: Closed the historical docker-backed testing tasks while leaving the direct daemon reachability task blocked.
- Cause: The evidence now cleanly separates two concerns: stack-backed integration coverage is present and passing, while direct Docker CLI/daemon control from this Codex session is still denied by the local user-profile permission boundary.
- Action: Marked `CTX-20260414-032`, `CTX-20260414-033`, `CTX-20260414-034`, and `CTX-20260414-035` as `done`, and kept `CTX-20260415-014` blocked as the only remaining runtime-stack access issue.
- Prevention: Keep task granularity aligned with the actual failure boundary so permission issues on Docker CLI access do not artificially keep already-validated infrastructure test work marked as incomplete.

### 2026-04-15 20:02:00 +08:00 | Phase P Crawl4AI And Observability Continuation Started

- Stage: `CTX-20260415-031 ~ CTX-20260415-034`
- Event: Started the next focused testing slice using the already-running localhost Collector, Jaeger, Prometheus, PostgreSQL, MinIO, and Redis endpoints supplied by the operator.
- Cause: After closing the main-path E2E and docker-backed runtime-stack tasks, the main remaining gaps were the still-open `CTX-20260412-029` Crawl4AI adapter coverage and the lack of an automated proof that Cortex exports telemetry all the way into Jaeger and Prometheus.
- Action: Added a dedicated batch to expand Crawl4AI edge-case coverage and build a reusable live observability probe against the active localhost stack.
- Prevention: Keep the next batch tightly scoped to the last genuinely-open behavior gaps rather than re-running already-green stack or E2E slices.

### 2026-04-15 20:09:00 +08:00 | Crawl4AI Source Validation Order Hid The Real Unsupported-Source Error

- Stage: `CTX-20260415-032`, `CTX-20260412-029`
- Event: The new object-source edge test for Crawl4AI initially failed with `Crawl4AI requires source.url or source.uri` instead of the more accurate unsupported-object-source error.
- Cause: `Crawl4AIParseEngine.execute(...)` validated the presence of `url/uri` before checking `ParseInputKind.OBJECT`, so object-backed requests tripped the generic missing-source validation first.
- Action: Reordered the validation checks in `packages\\parse\\src\\cortex_parse\\adapters\\crawl4ai.py` so object-backed sources now fail fast with the intended adapter-specific message.
- Prevention: For source-specific adapters, validate unsupported source kinds before generic field presence so callers receive the most actionable error surface.

### 2026-04-15 20:11:00 +08:00 | Crawl4AI Timing Extraction Assumed An Optional SDK Field Always Existed

- Stage: `CTX-20260415-032`, `CTX-20260412-029`
- Event: While adding a no-timings Crawl4AI result fixture, the adapter revealed a latent assumption that `result.dispatch_result` is always present.
- Cause: `_timings(...)` accessed `result.dispatch_result` directly instead of treating it as optional, which would raise `AttributeError` for valid SDK payloads that omit that field.
- Action: Switched the adapter to use `getattr(result, "dispatch_result", None)` and added focused tests covering missing timing payloads, crawl failures, unsupported object sources, citation-markdown fallback, and unresolved `storage_state_ref` warnings in `tests/integration/test_parse_crawl4ai_adapter.py`.
- Prevention: Treat optional provider SDK fields as optional at the adapter boundary and add explicit fixtures for sparse payload shapes, especially for advanced-feature adapters that aggregate many heterogeneous result fields.

### 2026-04-15 20:18:00 +08:00 | Live Observability Validation Exposed Missing OTLP Metric Export Wiring

- Stage: `CTX-20260415-033`
- Event: Probing the running Collector / Jaeger / Prometheus stack showed Jaeger already receiving Cortex traces, but the Collector Prometheus endpoint had no `cortex_*` metrics from the application side.
- Cause: `configure_telemetry(...)` only configured an OTLP trace exporter; the SDK `MeterProvider` had no OTLP metric reader/exporter attached, so application metrics recorded through `MetricsFacade` never left the process.
- Action: Updated `packages\\observability\\src\\cortex_observability\\bootstrap.py` to create an OTLP HTTP metric exporter plus `PeriodicExportingMetricReader`, reusing the configured OTLP endpoint and exporting metrics every second for deterministic validation.
- Prevention: Keep trace and metric export wiring paired in the same telemetry bootstrap layer so enabling OTLP does not silently cover only one signal type.

### 2026-04-15 20:23:00 +08:00 | Reusable Live Observability Probe Added Against The Localhost Stack

- Stage: `CTX-20260415-033`
- Event: Added a reusable live observability probe and corresponding runtime-stack test.
- Cause: Manual spot checks of Collector / Jaeger / Prometheus are useful once, but they do not leave behind a stable regression guard.
- Action: Added `scripts\\dev\\live_observability_probe.py` and `tests\\integration\\test_runtime_observability_stack.py`. The probe spins up a temporary SQLite-backed API instance with OTLP enabled, overrides Parse with a deterministic fake engine, forces telemetry flush, then validates:
  - Collector health on `http://127.0.0.1:13133/`
  - Jaeger trace lookup for the returned `x-trace-id`
  - Collector Prometheus exposition on `http://127.0.0.1:8889/metrics`
  - Prometheus metric-name discovery and `up{job="otel-collector"} == 1`
  The latest live summary was written to `runtime-test-data/live-observability-1776255711487484900/summary.json`.
- Prevention: For live-stack observability checks, prefer a self-contained probe that generates its own deterministic request/trace/metric payloads instead of relying on whichever runtime traffic happened to occur recently.

### 2026-04-15 20:26:00 +08:00 | Crawl4AI And Observability Validation Completed

- Stage: `CTX-20260412-029`, `CTX-20260415-031 ~ CTX-20260415-034`
- Event: The Crawl4AI adapter gap and live observability path are now both covered and validated.
- Cause: The remaining work was a mix of adapter edge-case coverage and a telemetry-export implementation gap rather than any broader REST-contract or stack-availability problem.
- Action: Completed validation with:
  - `.\.venv\Scripts\python.exe -m ruff check packages/observability/src/cortex_observability/bootstrap.py packages/parse/src/cortex_parse/adapters/crawl4ai.py tests/integration/test_parse_crawl4ai_adapter.py tests/integration/test_runtime_observability_stack.py scripts/dev/live_observability_probe.py`
  - `.\.venv\Scripts\pyright.exe`
  - `$env:CORTEX_RUNTIME_STACK='1'; .\.venv\Scripts\python.exe -m pytest tests/contract/test_foundation_models.py tests/integration/test_parse_crawl4ai_adapter.py tests/integration/test_runtime_stack.py tests/integration/test_runtime_observability_stack.py -q`
  and marked `CTX-20260412-029` done.
- Prevention: When a provider adapter and a cross-cutting platform capability both remain open, pair them in one validation slice only if the resulting checks stay deterministic and locally reproducible, as they do here with fake Parse input plus a real localhost telemetry stack.

### 2026-04-15 20:37:39 +08:00 | Phase Q Operator Runbook And README Completion Started

- Stage: `CTX-20260415-035 ~ CTX-20260415-037`
- Event: Started the operator-documentation closure pass after the implementation, E2E, runtime-stack, and observability slices had already landed.
- Cause: The functional API surface was in place, but the root README was still only a short bootstrap note and the local runtime-stack helper still contained a PowerShell parameter collision that made it unsafe to treat as the canonical operator entrypoint.
- Action: Scoped the batch to two deliverables: repair the local stack helper first, then rewrite the repository README into a Chinese runbook that accurately reflects the current API surface, runtime config overlays, testing layers, and deployment paths.
- Prevention: Before promoting a local script into official operator guidance, always verify that the script itself is free of shell-specific binding issues; otherwise the documentation can become the fastest path to reproducing a known bug.

### 2026-04-15 20:39:00 +08:00 | PowerShell `$Host` Collision In The Local Stack Helper Was Fixed At The Source

- Stage: `CTX-20260415-035`
- Event: `scripts/dev/stack.ps1` still called `Wait-TcpReady -Host ...`, which collides with PowerShell's built-in read-only `$Host` variable and reproduces the exact startup error seen earlier by the operator.
- Cause: The helper function parameter is named `HostName`, but the call sites in both the `up` and `restart` branches still used the shorthand `-Host`, which PowerShell binds as the built-in variable instead of the function parameter.
- Action: Updated every `Wait-TcpReady` invocation in `scripts/dev/stack.ps1` to use the explicit `-HostName` parameter and expanded `scripts/dev/check-runtime-stack.ps1` so the canonical runtime-stack validation now runs both `tests/integration/test_runtime_stack.py` and `tests/integration/test_runtime_observability_stack.py`.
- Prevention: In PowerShell helpers, avoid shorthand parameter names that shadow built-in automatic variables; use the declared parameter name verbatim in scripts that are meant to be copied into operator runbooks.

### 2026-04-15 20:42:00 +08:00 | Root README Was Rewritten Into An Operator-Facing Chinese Runbook

- Stage: `CTX-20260415-036`
- Event: Replaced the previous minimal README with a comprehensive Chinese project guide and aligned the surrounding operator/testing docs.
- Cause: The repository had already accumulated enough implementation depth that a short English bootstrap note was no longer sufficient for onboarding, local verification, or production deployment planning.
- Action: Rewrote `README.md` to cover project positioning, implemented REST API groups, architecture, repository layout, unified runtime config, auth/scope model, minimal local startup, full docker-backed startup, verification samples, observability checks, and vendor-neutral production deployment guidance. Also aligned `scripts/ci/README.md`, `tests/integration/README.md`, and `tests/e2e/README.md` with the now-current runtime-stack and E2E behavior.
- Prevention: Once the public REST surface, runtime overlays, and validation flows stabilize, keep the root README at the same maturity level as the implementation so operators do not need to reverse-engineer behavior from tests and specs.

### 2026-04-15 20:49:00 +08:00 | Phase Q Validation Completed With A Non-Blocking Third-Party Warning Note

- Stage: `CTX-20260415-037`
- Event: The repaired runtime-stack helper and refreshed runbook were validated successfully.
- Cause: The documentation phase still needed hard evidence that the canonical operator commands and published REST contract remained valid after the script and README updates.
- Action: Completed validation with:
  - `powershell -ExecutionPolicy Bypass -File scripts\dev\check-runtime-stack.ps1`
  - `.\.venv\Scripts\python.exe -m pytest tests/contract/test_openapi_contract.py -q`
  - `Select-String -Path scripts\dev\stack.ps1 -Pattern "Wait-TcpReady -Host "`
  The runtime-stack script passed both the infrastructure-backed slice and the live observability probe (`4 passed` + `1 passed`), the OpenAPI contract tests passed (`3 passed`), and the grep-style check confirmed the old `-Host` call sites were gone.
- Prevention: For operator-facing documentation changes, validate the exact commands you publish instead of only running nearby unit tests. During this pass, `pytest` surfaced deprecation warnings from third-party `cognee` dependencies, but they are currently non-blocking and do not affect Cortex's own contract or runtime behavior.

### 2026-04-15 21:25:00 +08:00 | Phase R Repo-Pinned Python And Dual-Shell Worker Entrypoints Started

- Stage: `CTX-20260415-038 ~ CTX-20260415-040`
- Event: The operator hit a recurring local-environment failure mode: a PowerShell worker loop was pasted into Git Bash, `Start-Sleep` / `while ($true)` failed at the shell layer, and repeated `uv run` usage landed on an already unhealthy `.venv`, which made uv attempt to repair or recreate the environment while files under `.venv\Scripts` were still locked.
- Cause: Two separate issues were interacting: shell-specific command syntax was being mixed across PowerShell and Bash, and the repository did not yet provide a canonical wrapper that pinned uv's managed Python and project virtualenv into repository-owned paths before every `uv` invocation.
- Action: Added repo-local environment helpers plus wrappers in `scripts\dev\_uv-env.ps1`, `scripts\dev\_uv-env.sh`, `scripts\dev\uv.ps1`, and `scripts\dev\uv.sh`; added repair entrypoints in `scripts\dev\repair-venv.ps1` and `scripts\dev\repair-venv.sh`; added dual-shell worker launchers in `scripts\dev\run-parse-worker.*` and `scripts\dev\run-knowledge-worker.*`; pinned `.python-version` to `3.12.12`; and refreshed the README guidance so operators use the wrapper/launcher layer instead of looping `uv run` manually.
- Prevention: Keep managed Python and the project environment under the repository (`.uv-python` + `.venv`), and for long-running workers call the generated executables from the canonical `.venv` instead of wrapping `uv run` inside an infinite shell loop.

### 2026-04-15 21:32:00 +08:00 | Repo-Local uv Wrapper Validation Surfaced And Fixed A PowerShell Output Swallowing Bug

- Stage: `CTX-20260415-038`, `CTX-20260415-040`
- Event: During validation, `powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 --version` exited with code `0` but printed nothing, making the wrapper look broken even though the underlying `uv` command was succeeding.
- Cause: `scripts\dev\uv.ps1` used `exit (Invoke-CortexUv @Args)`, which evaluated the wrapper function in an expression context and suppressed the native `uv` stdout that operators expect to see from commands like `uv --version` and `uv python dir`.
- Action: Reworked `scripts\dev\uv.ps1` to set the repo-local uv environment, invoke `uv` directly, preserve stdout/stderr, and then exit with the captured `$LASTEXITCODE`. Also tightened `scripts\dev\bootstrap.ps1` and `scripts\dev\check-runtime-stack.ps1` so they propagate exit codes explicitly.
- Prevention: When a PowerShell wrapper is meant to behave like a transparent pass-through for a native CLI, avoid wrapping the native call inside an `exit (...)` expression; invoke the command directly, then exit with the recorded exit code.

### 2026-04-15 21:36:00 +08:00 | Phase R Validation Completed With Repo-Local Python Provenance And A Bash-Host Caveat

- Stage: `CTX-20260415-040`
- Event: The repo-pinned Python and dual-shell launcher slice now validates cleanly on the canonical PowerShell path.
- Cause: The remaining work was verification rather than feature implementation once the wrapper and launcher layer landed.
- Action: Completed validation with:
  - `powershell -ExecutionPolicy Bypass -File scripts\dev\repair-venv.ps1`
  - `Get-Content .venv\pyvenv.cfg`
  - `powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 --version`
  - `powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run --no-sync python -c "import os,sys; ..."`
  - `powershell -ExecutionPolicy Bypass -File scripts\dev\run-parse-worker.ps1 -Once`
  - `powershell -ExecutionPolicy Bypass -File scripts\dev\run-knowledge-worker.ps1 -Once`
  - `powershell -ExecutionPolicy Bypass -File scripts\dev\check-runtime-stack.ps1`
  Validation confirmed `.venv\pyvenv.cfg` now points to `D:\code\codex\cortex\.uv-python\cpython-3.12.12-windows-x86_64-none`, the wrapper exposes `UV_PYTHON_INSTALL_DIR=D:\code\codex\cortex\.uv-python` and `UV_PROJECT_ENVIRONMENT=D:\code\codex\cortex\.venv`, both worker one-shot launchers reported `bootstrap ready: idle`, and the runtime-stack validation still passed (`4 passed` + `1 passed`).
- Prevention: Validate both the repo-local interpreter provenance (`pyvenv.cfg`) and the user-facing wrapper UX (`uv.ps1 --version`, worker one-shot launchers) so an environment fix is proven at both the file-system and operator-command layers. A residual caveat remains in this Codex host: invoking `bash.exe` for live validation still returns `Bash/Service/CreateInstance/E_ACCESSDENIED`, so the Bash launchers were implemented and documented but not executed end-to-end inside this session. During the same validation pass, `cortex-knowledge-worker` surfaced non-blocking third-party Cognee warnings about a missing log-file handler path and upcoming access-control defaults; they do not block the Cortex worker bootstrap path but should be kept in mind for real provider deployments.

### 2026-04-15 21:40:00 +08:00 | Phase S Hardened Active-Venv Repair Guards After A Real Git Bash Failure

- Stage: `CTX-20260415-041`, `CTX-20260415-042`
- Event: A real Git Bash run still reproduced an awkward failure mode: the operator sourced `.venv/Scripts/activate`, then launched `bash scripts/dev/run-parse-worker.sh`; the worker script correctly noticed a missing entrypoint and tried to repair the environment, but Windows refused to mutate `.venv\Scripts` because the target environment was already activated and later because `cortex-api.exe` was still holding files in the same directory.
- Cause: The original hardening pass handled repo-local uv pinning, but it still treated "currently activated target `.venv`" and "currently running repo executables from `.venv`" as ordinary repairable states. On Windows, both states commonly produce file-lock failures (`os error 32`) before the operator sees an actionable explanation.
- Action: Tightened `scripts\dev\_uv-env.ps1` and `scripts\dev\_uv-env.sh` so `.venv` health now also requires `pyvenv.cfg` to point at the repo-local `.uv-python` root, repair now fails fast when the target `.venv` is already activated, and force-recreate emits a clear message when a running `cortex-api` / worker / Python / uv process is still locking the environment. Also updated both PowerShell and Bash worker launchers to stop before attempting in-place repair on an activated project `.venv`, and refreshed the README to explicitly tell operators not to pre-activate `.venv` before using the wrapper scripts.
- Validation: Verified the new guardrails with:
  - `$env:VIRTUAL_ENV = (Resolve-Path .venv).Path; powershell -ExecutionPolicy Bypass -File scripts\dev\repair-venv.ps1 -ForceRecreate`
  - `Remove-Item Env:VIRTUAL_ENV -ErrorAction SilentlyContinue; powershell -ExecutionPolicy Bypass -File scripts\dev\repair-venv.ps1 -ForceRecreate`
  - `Get-Process | Where-Object { $_.ProcessName -match 'cortex|python|uv' }`
  The first check now exits immediately with the intended "Run `deactivate` (or open a fresh terminal)" message; the second check now reports that a running `cortex-api` / worker / Python / uv process is still using `.venv` instead of leaking a raw `Remove-Item` stack trace; and process inspection confirmed an active `cortex-api` process in the local environment during validation.
- Prevention: For repo-managed Windows virtualenv tooling, treat "activated target env" and "running repo executables from that env" as first-class operator states with their own explicit guidance instead of falling through to generic file-lock errors. Also keep the docs opinionated: wrapper scripts should be run from a fresh shell, not from inside an already activated project `.venv`.

### 2026-04-15 22:05:00 +08:00 | Phase T Auth Mode Secret Model Clarified And An Optional Built-In Token Issuer Landed

- Stage: `CTX-20260415-043 ~ CTX-20260415-045`
- Event: The existing auth implementation could validate four modes (`dev`, `jwt`, `introspection`, `hybrid`) but did not yet explain, in operator terms, how each mode actually obtains its tokens or secrets. In practice, only tests were hand-crafting `dev:` tokens, which left no supported path for issuing per-user or per-service bearer tokens in local or self-hosted deployments without an external IdP.
- Cause: Cortex had been modeled primarily as an OAuth 2.0 / OIDC-compatible resource server, which is correct, but the design surface did not yet include a bounded bootstrap issuance story for deployments that are not wired to a full authorization server.
- Action: Added an optional built-in token issuance path:
  - New auth settings: `CORTEX_AUTH_TOKEN_ISSUER_ENABLED`, `CORTEX_AUTH_TOKEN_ISSUER_BOOTSTRAP_SECRET`, `CORTEX_AUTH_TOKEN_DEFAULT_TTL_SECONDS`, `CORTEX_AUTH_TOKEN_MAX_TTL_SECONDS`
  - New contracts: `TokenIssueRequest`, `TokenIssueResponse`
  - New auth router: `POST /v1/auth/token`
  - New security header: `X-Cortex-Issuer-Secret`
  - New auth service: `TokenIssuerService`
  The implementation keeps Cortex resource-server-first: `dev` issues Cortex `dev:` tokens, `jwt` / `hybrid` issue shared-secret JWTs, and `introspection` remains external-only. The docs were updated in `README.md`, `specs/cortex-api.yaml`, `specs/cortex-tech.md`, `specs/cortex-prd.md`, and `specs/cortex-schema.md` to spell out where secrets come from and when an external authorization server is still required.
- Validation: Completed focused validation with:
  - `.\.venv\Scripts\python.exe -m ruff check ...`
  - `.\.venv\Scripts\pyright.exe`
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_common_auth.py tests/integration/test_api_auth_token.py tests/contract/test_openapi_contract.py -q`
  Results: `ruff` passed, `pyright` passed (`0 errors`), and the focused pytest slice passed (`15 passed`). The new integration tests verify that `/v1/auth/token` can mint a token in both `dev` and `jwt` modes and that the issued bearer token can immediately access a protected endpoint (`/v1/health/live`). Contract tests also confirm that the runtime OpenAPI and the documented specification now agree on the new path and schemas.
- Prevention: Keep the boundary explicit in both code and docs: Cortex may optionally mint bootstrap tokens for local/self-hosted `dev` / `jwt` / `hybrid` environments, but it does not try to become a full user directory or opaque-token authorization server. During this validation pass, pytest still surfaced non-blocking third-party `cognee` / `pydantic` deprecation warnings that are outside the new auth path and do not block the token issuer or authorization flows.

### 2026-04-15 22:20:00 +08:00 | Phase U Swagger UI Ignored The Plain Authorization Header Parameter Until Bearer Security Was Wired Properly

- Stage: `CTX-20260415-046`, `CTX-20260415-047`
- Event: While validating protected APIs through `http://127.0.0.1:8080/docs`, entering the token into the generated `authorization` parameter did not result in an `Authorization` request header being sent.
- Cause: The runtime API dependency modeled authentication as a plain header parameter (`Header(...)`) instead of a proper OpenAPI security scheme. In OpenAPI / Swagger tooling, `Authorization` is a special header that should be described through `securitySchemes`, not an ordinary header parameter, so the UI did not provide a reliable bearer-token injection path.
- Action: Replaced the plain header dependency in `apps\api\src\cortex_api\dependencies\auth.py` with FastAPI `HTTPBearer`, which emits a runtime `BearerAuth` security scheme and drives Swagger UI's standard `Authorize` flow. Also updated `README.md` to tell operators to use the top-right `Authorize` button and added a focused runtime OpenAPI contract test in `tests\contract\test_openapi_contract.py` to verify that `BearerAuth` is present and attached to protected routes like `/v1/health/ready`.
- Validation: The currently running project `.venv` was again in a broken/locked state and could not be used safely for verification because `pyvenv.cfg` pointed back to the user-level managed Python and console-script entrypoints were missing. To avoid disrupting the already running local API, validation was executed in an isolated repo-local environment (`.venv-auth-verify`) created with `UV_PROJECT_ENVIRONMENT=.venv-auth-verify`. The following checks passed there:
  - `python -m ruff check apps/api/src/cortex_api/dependencies/auth.py tests/contract/test_openapi_contract.py`
  - `pyright apps/api/src/cortex_api/dependencies/auth.py tests/contract/test_openapi_contract.py`
  - `python -m pytest tests/integration/test_api_auth_token.py tests/contract/test_openapi_contract.py -q`
  Results: `ruff` passed, `pyright` passed (`0 errors`), and the focused pytest slice passed (`7 passed`). The new contract test confirms that runtime OpenAPI now emits `BearerAuth` and attaches it to protected routes.
- Prevention: For browser-facing API docs, always model bearer authentication with a real OpenAPI security scheme rather than a raw `Authorization` header parameter. Keep one regression test focused on runtime OpenAPI security metadata so the local Swagger UI remains usable even when the static contract and runtime implementation evolve independently.

### 2026-04-15 22:45:00 +08:00 | Phase V Request Examples And Parameter Guidance Completed

- Stage: `CTX-20260415-048 ~ CTX-20260415-050`
- Event: The Swagger and OpenAPI request documentation was still too abstract for direct operator use: write endpoints exposed large nested bodies with little inline guidance, and several routes had no copy-paste-ready request examples at all.
- Cause: Earlier implementation work prioritized functional contract coverage and runtime parity, but not yet the operator ergonomics of request construction. As a result, the static contract mostly exposed schema structure while the runtime Swagger UI left users guessing which optional fields mattered and what defaults were safest.
- Action: Added a request-documentation layer at three levels:
  - Runtime Swagger: route-level `Body(openapi_examples=...)` examples for Auth, Parse, Storage, Knowledge, plus clearer path/query/header descriptions and examples in the FastAPI routers.
  - Contract schemas: enriched request DTO fields in `cortex_contracts` with per-field meaning, examples, and recommended default behavior for optional fields, especially for nested Parse, Storage, AccessPolicy, and Knowledge inputs.
  - Static spec: updated `specs/cortex-api.yaml` with concrete request examples for every request-bearing public API plus parameter examples for common path/header/query inputs.
  A new shared module, `packages/contracts/src/cortex_contracts/openapi_examples.py`, now centralizes the reusable request payload examples used by runtime Swagger.
- Validation: Reused the isolated repo-local `.venv-auth-verify` environment because the primary `.venv` remained unsafe for mutation. The following checks passed:
  - `python -m ruff check apps/api/src/cortex_api/routers/auth.py apps/api/src/cortex_api/routers/jobs.py apps/api/src/cortex_api/routers/knowledge.py apps/api/src/cortex_api/routers/parse.py apps/api/src/cortex_api/routers/storage.py packages/contracts/src/cortex_contracts/auth.py packages/contracts/src/cortex_contracts/knowledge.py packages/contracts/src/cortex_contracts/openapi_examples.py packages/contracts/src/cortex_contracts/parse.py packages/contracts/src/cortex_contracts/resources.py packages/contracts/src/cortex_contracts/storage.py tests/contract/test_openapi_contract.py`
  - `pyright apps/api/src/cortex_api/routers/auth.py apps/api/src/cortex_api/routers/jobs.py apps/api/src/cortex_api/routers/knowledge.py apps/api/src/cortex_api/routers/parse.py apps/api/src/cortex_api/routers/storage.py packages/contracts/src/cortex_contracts/auth.py packages/contracts/src/cortex_contracts/knowledge.py packages/contracts/src/cortex_contracts/openapi_examples.py packages/contracts/src/cortex_contracts/parse.py packages/contracts/src/cortex_contracts/resources.py packages/contracts/src/cortex_contracts/storage.py tests/contract/test_openapi_contract.py`
  - `python -m pytest tests/contract/test_openapi_contract.py tests/integration/test_api_auth_token.py -q`
  Results: `ruff` passed, `pyright` passed (`0 errors`), and the focused pytest slice passed (`10 passed`). The contract tests now assert that every public request-bearing route exposes request examples in both the checked-in spec and the runtime OpenAPI output.
- Prevention: Treat request examples and parameter guidance as contract surface, not optional polish. Keep regression coverage over request-body examples and documented parameter examples so future route or DTO refactors do not silently degrade Swagger usability.

### 2026-04-16 10:35:00 +08:00 | Phase W Minimal Parse API Redesign Replaced Low-Level Public Parser Knobs With A Compiler Layer

- Stage: `CTX-20260415-051 ~ CTX-20260415-054`
- Event: The public Parse API had become too implementation-shaped: callers were still expected to understand `parser`, `crawl`, `output`, and other low-level structures even though the product goal had shifted to a simple user-facing contract.
- Cause: Earlier Parse work optimized for engine completeness and adapter flexibility, but the API surface still leaked internal execution details. That mismatch also made failures harder to reason about; for example, a user-supplied low-level selector could push a remote engine such as Jina Reader into an avoidable `422` path.
- Action: Introduced a dedicated `ParseRequestCompiler` that compiles the public request shape (`source + engine_id (+ scene)` for sync, plus optional `priority` / `webhook` for async) into the existing internal `ParseSyncRequest` / `ParseJobRequest`. The compiler now:
  - infers or resolves source kind from `source.uri` / `source.object_id`
  - resolves stored objects into signed engine-accessible sources
  - maps `engine_id + scene + source_kind + mime_type` onto internal profile refs
  - injects engine-scene presets for Crawl4AI, Jina Reader, LlamaParse, MarkItDown, and Docling
  - exposes `default_scene_id`, `supported_scene_ids`, and `default_profile_ref` through `/v1/parse/engines`
- Prevention: Keep the public Parse contract intent-focused and reserve provider-specific knobs for internal profiles, scene presets, and operator configuration. When a new adapter is added, first define its scene presets and compiler mapping instead of exposing raw provider parameters directly on the public API.

### 2026-04-16 10:55:00 +08:00 | Phase W Validation Closed The Remaining Parse Contract Drift In E2E And Static Docs

- Stage: `CTX-20260415-055`
- Event: After the compiler-based Parse redesign landed in code, the end-to-end test, README examples, and checked-in OpenAPI spec were still partially describing the legacy `parser/crawl/output` request body.
- Cause: Runtime route code and contract DTOs had moved to `ParseSubmitRequest` / `ParseJobSubmitRequest`, but the surrounding operator-facing artifacts had not yet been fully aligned.
- Action: Updated the E2E parse job flow to submit the minimal request shape, added focused unit coverage for scene compilation and Crawl4AI `deep_web` advanced features, refreshed README Parse examples and profile inventory, and aligned `specs/cortex-api.yaml` with the new public Parse schemas and examples.
- Validation: Completed focused validation in the repo-local `.venv-auth-verify` environment with:
  - `python -m ruff check apps/api/src/cortex_api/dependencies/runtime.py apps/api/src/cortex_api/lifespan.py apps/api/src/cortex_api/routers/parse.py apps/api/src/cortex_api/services/parse_requests.py packages/contracts/src/cortex_contracts/__init__.py packages/contracts/src/cortex_contracts/openapi_examples.py packages/contracts/src/cortex_contracts/parse.py packages/parse/src/cortex_parse/__init__.py packages/parse/src/cortex_parse/request_compiler.py packages/parse/src/cortex_parse/adapters/crawl4ai.py packages/parse/src/cortex_parse/adapters/docling.py packages/parse/src/cortex_parse/adapters/jina_reader.py packages/parse/src/cortex_parse/adapters/llama_parse.py packages/parse/src/cortex_parse/adapters/markitdown.py tests/unit/test_parse_request_compiler.py tests/unit/test_parse_profiles.py tests/contract/test_foundation_models.py tests/contract/test_openapi_contract.py tests/integration/test_api_parse.py tests/integration/test_api_e2e.py`
  - `pyright apps/api/src/cortex_api/dependencies/runtime.py apps/api/src/cortex_api/lifespan.py apps/api/src/cortex_api/routers/parse.py apps/api/src/cortex_api/services/parse_requests.py packages/contracts/src/cortex_contracts/__init__.py packages/contracts/src/cortex_contracts/openapi_examples.py packages/contracts/src/cortex_contracts/parse.py packages/parse/src/cortex_parse/__init__.py packages/parse/src/cortex_parse/request_compiler.py tests/unit/test_parse_request_compiler.py tests/contract/test_foundation_models.py tests/contract/test_openapi_contract.py tests/integration/test_api_parse.py tests/integration/test_api_e2e.py`
  - `python -m pytest tests/unit/test_parse_request_compiler.py tests/unit/test_parse_profiles.py tests/contract/test_foundation_models.py tests/contract/test_openapi_contract.py tests/integration/test_api_parse.py tests/integration/test_api_e2e.py -q`
- Prevention: Whenever a public contract is simplified, immediately update the static spec, README examples, E2E flow, and contract tests in the same batch so the runtime, documentation, and operator mental model do not drift apart.

### 2026-04-16 12:55:00 +08:00 | Phase X Parse Engine Catalog And Batch Locator Contract Closed The Remaining Public Parse Gaps

- Stage: `CTX-20260416-056 ~ CTX-20260416-059`
- Event: Operators still saw three user-facing Parse problems after the earlier redesign: `/v1/parse/engines` did not expose the full activated runtime catalog, explicit engines such as `crawl4ai` could be rejected as unavailable, and the public request body still drifted between multiple shapes instead of one `sources + engine_id (+ scene)` contract.
- Cause: The parse bootstrap still treated optional-provider import checks as activation gates, so runtime-config-enabled engines were omitted from the registry if the current environment lacked that adapter package. In parallel, the public request/compiler/docs/tests were only partially migrated off the earlier single-`source` object shape.
- Action: Closed the gap in four coordinated moves:
  - Changed the parse bootstrap/adapters so every runtime-config-enabled engine registers as `active` and appears in the catalog, while actual adapter execution still performs its own provider/config validation at runtime.
  - Promoted the major parse adapters (`crawl4ai`, `jina_reader`, `llama_parse`, `markitdown`, `docling`) into the parse package's core install path so a normal `uv sync --all-packages --all-groups` brings in the full selectable engine set instead of leaving it to an optional extra.
  - Refined `ParseRequestCompiler`, DTOs, route handlers, and request helpers around one public request shape: `sources`, `engine_id`, optional `scene`, plus async-only `priority` / `webhook`. The compiler now normalizes legacy payloads, infers source kind / filename / MIME from locator strings, compiles one internal request per source, and returns batch sync results or batch job acceptances.
  - Updated `specs/cortex-api.yaml`, `specs/cortex-tech.md`, `specs/cortex-prd.md`, `specs/cortex-dfd.md`, `specs/cortex-schema.md`, `README.md`, and the task ledger so the static contract, runtime docs, and operator guidance all describe the same batch-first, auto-routing Parse API.
- Validation: Completed focused validation in the repo-local `.venv-auth-verify` environment with:
  - `python -m ruff check apps/api/src/cortex_api/routers/parse.py apps/api/src/cortex_api/services/parse_requests.py packages/contracts/src/cortex_contracts/__init__.py packages/contracts/src/cortex_contracts/openapi_examples.py packages/contracts/src/cortex_contracts/parse.py packages/parse/src/cortex_parse/bootstrap.py packages/parse/src/cortex_parse/request_compiler.py packages/parse/src/cortex_parse/adapters/crawl4ai.py packages/parse/src/cortex_parse/adapters/docling.py packages/parse/src/cortex_parse/adapters/llama_parse.py packages/parse/src/cortex_parse/adapters/markitdown.py tests/unit/test_parse_request_compiler.py tests/contract/test_foundation_models.py tests/contract/test_openapi_contract.py tests/integration/test_api_parse.py tests/integration/test_api_e2e.py`
  - `python scripts/ci/validate_yaml.py`
  - `pyright apps/api/src/cortex_api/routers/parse.py apps/api/src/cortex_api/services/parse_requests.py packages/contracts/src/cortex_contracts/__init__.py packages/contracts/src/cortex_contracts/openapi_examples.py packages/contracts/src/cortex_contracts/parse.py packages/parse/src/cortex_parse/bootstrap.py packages/parse/src/cortex_parse/request_compiler.py tests/unit/test_parse_request_compiler.py tests/contract/test_foundation_models.py tests/contract/test_openapi_contract.py tests/integration/test_api_parse.py tests/integration/test_api_e2e.py`
  - `python -m pytest tests/unit/test_parse_request_compiler.py tests/unit/test_parse_profiles.py tests/contract/test_foundation_models.py tests/contract/test_openapi_contract.py tests/integration/test_api_parse.py tests/integration/test_api_e2e.py -q`
  - A runtime smoke check against `create_app()` with `GET /v1/parse/engines`, which returned HTTP `200` and the full activated catalog `['crawl4ai', 'jina_reader', 'llama_parse', 'markitdown', 'docling']`
- Prevention: Keep provider import/install concerns separate from catalog activation semantics. The runtime engine catalog should reflect the deployment's intended active engines from the checked-in runtime config, while execution-time adapter validation should explain missing SDKs, missing API keys, or provider-side failures without hiding the engine from discovery. When the public Parse contract changes again, update runtime routes, static OpenAPI, README examples, task history, and focused tests in the same patch set.

### 2026-04-16 13:15:00 +08:00 | Crawl4AI 0.8.6 Dropped `use_undetected_browser` From BrowserConfig But The Adapter Still Passed It

- Stage: `CTX-20260416-060`, `CTX-20260416-061`
- Event: A live `engine_id=crawl4ai` parse request failed with `BrowserConfig.__init__() got an unexpected keyword argument 'use_undetected_browser'`, surfacing as `parse_failed` from `/v1/parse/sync`.
- Cause: The Cortex Crawl4AI adapter still emitted an older BrowserConfig kwarg (`use_undetected_browser`) while the installed official SDK had already moved undetected-browser selection to `browser_type="undetected"`. Local validation confirmed the currently installed package was `crawl4ai==0.8.6`, whose `BrowserConfig.__init__` still accepts `enable_stealth` but no longer accepts `use_undetected_browser`.
- Action: Patched `packages\parse\src\cortex_parse\adapters\crawl4ai.py` to inspect the actual SDK signature before constructing `BrowserConfig`, drop unsupported kwargs, and compatibility-map `use_undetected_browser=True` onto `browser_type="undetected"` when the new signature is in use. Also aligned the emitted anti-bot diagnostic label to the documented values (`undetected`, `stealth_plus_undetected`) and restored the adapter's explicit object-source rejection path so the focused Crawl4AI regression suite stayed green.
- Validation:
  - `uv sync --all-packages --all-groups` now installs `crawl4ai==0.8.6` into the repo-managed `.venv`
  - Direct compatibility smoke check:
    - built Crawl4AI browser kwargs from a `BrowserProfile(enable_stealth=True, use_undetected_browser=True)`
    - verified they became `{'browser_type': 'undetected', ..., 'enable_stealth': True}` with no `use_undetected_browser`
    - successfully instantiated the real `crawl4ai.BrowserConfig(**kwargs)` without raising
  - `uv run python -m pytest tests/integration/test_parse_crawl4ai_adapter.py tests/unit/test_parse_request_compiler.py -q`
  - `uv run python -m ruff check packages/parse/src/cortex_parse/adapters/crawl4ai.py tests/integration/test_parse_crawl4ai_adapter.py`
- Prevention: For third-party adapters with fast-moving config surfaces, never pass a hardcoded provider kwarg list straight into the SDK constructor. Always normalize through a version-tolerant compatibility layer keyed off the installed signature, and keep at least one regression test that mimics a newer SDK removing a previously supported kwarg.

### 2026-04-16 15:20:00 +08:00 | Crawl4AI Advanced Parse Reached Real Browser Launch, Then Hit A Host-Level Playwright Permission Boundary

- Stage: `CTX-20260416-062`, `CTX-20260416-063`
- Event: After the BrowserConfig compatibility hotfix, a real `/v1/parse/sync` request with `engine_id=crawl4ai` progressed past adapter construction but still failed before content capture. The first failure was a write-permission error against the provider default cache directory (`C:\Users\hy\.crawl4ai\cache`). After redirecting Crawl4AI state into the repository, the request advanced again and then failed during Playwright driver launch with `PermissionError: [WinError 5]` while creating the Windows named pipe used by `asyncio.create_subprocess_exec`.
- Cause: Two separate runtime assumptions were being violated. First, Crawl4AI defaulted its cache/log/database state into the user home directory unless an explicit base directory was supplied. Second, the current Windows tool environment allowed the Cortex API process itself to run but denied the Playwright child-process / named-pipe setup that Crawl4AI needs for browser-backed crawling. That second blocker is a host-execution constraint rather than a Cortex request-contract or adapter-mapping bug.
- Action:
  - Extended the unified runtime config with `parse.engines.crawl4ai.base_directory_ref` and wired it through parse bootstrap into the Crawl4AI adapter.
  - Updated the adapter to initialize both `CRAWL4_AI_BASE_DIRECTORY` and `CRAWL4AI_BASE_DIRECTORY` before importing the SDK, create the target directory eagerly, and pass the resolved `base_directory` directly into `AsyncWebCrawler(...)` so provider state stays under a writable repo-managed path such as `.data/crawl4ai/local`.
  - Added focused regression coverage proving the adapter now defaults to a repo-local base directory when no explicit setting is supplied.
  - Re-ran live integration checks against the real FastAPI app with a dev bearer token: `GET /v1/parse/engines` returned HTTP `200` with the active catalog `crawl4ai`, `jina_reader`, `llama_parse`, `markitdown`, `docling`; `POST /v1/parse/sync` returned HTTP `200` for `jina_reader`, `markitdown`, and `docling` against `https://example.com`; `crawl4ai` reached the Playwright launch path and failed only at the host pipe/subprocess boundary.
- Validation:
  - `uv run python -m pytest tests/integration/test_parse_crawl4ai_adapter.py tests/unit/test_parse_request_compiler.py -q`
  - `uv run python -m ruff check packages/common/src/cortex_common/runtime_config.py packages/parse/src/cortex_parse/bootstrap.py packages/parse/src/cortex_parse/adapters/crawl4ai.py tests/integration/test_parse_crawl4ai_adapter.py`
  - `uv run pyright packages/common/src/cortex_common/runtime_config.py packages/parse/src/cortex_parse/bootstrap.py packages/parse/src/cortex_parse/adapters/crawl4ai.py tests/integration/test_parse_crawl4ai_adapter.py`
  - Live runtime checks through `create_app()` + `TestClient`:
    - `GET /v1/parse/engines` -> `200`
    - `POST /v1/parse/sync` with `engine_id=jina_reader` -> `200`
    - `POST /v1/parse/sync` with `engine_id=markitdown` -> `200`
    - `POST /v1/parse/sync` with `engine_id=docling` -> `200`
    - `POST /v1/parse/sync` with `engine_id=crawl4ai` -> adapter/runtime path reached Playwright startup, then failed with host-level `PermissionError: [WinError 5]`
- Prevention: Treat browser-backed adapters as having an additional host capability requirement: writable working directories plus permission to spawn Playwright child processes and named pipes. Keep that requirement explicit in runtime docs and deployment runbooks, and validate browser-engine availability in the target shell/host where the service actually runs instead of assuming parity with pure-HTTP or pure-local file adapters.
### 2026-04-16 17:05:00 +08:00 | Crawl4AI Host Runtime Failure Was Folded Into A Formal Automation Layer

- Stage: `CTX-20260416-064 ~ CTX-20260416-066`
- Event: The remaining Crawl4AI issue was no longer a parser-contract defect but an operator problem: browser binaries and host child-process permissions were still too easy to discover only after the service had already started. The runtime-prep helper also surfaced raw third-party stack traces that were difficult to act on.
- Cause: Browser-backed parsing had not yet been promoted to a first-class deployment concern. The code could now route and execute Crawl4AI correctly, but browser installation, system dependencies, startup probing, failure categorization, and production entrypoints were still partially manual.
- Action:
  - Extended `cortex_parse.playwright_runtime` with stable failure classification (`browser_binary_missing`, `host_process_policy_blocked`, `host_browser_dependencies_missing`, `browser_download_tls_failed`, `playwright_runtime_preflight_failed`) and captured installer / probe subprocess output so operator tooling can reason about the true root cause instead of only a nonzero exit code.
  - Changed the Playwright probe to run in an isolated subprocess, which avoids leaking Playwright internal future / event-loop noise into the parent startup process and more closely matches real deployment preflight behavior.
  - Added production-facing entrypoint scripts:
    - `scripts/runtime/start-api.sh`
    - `scripts/runtime/start-parse-worker.sh`
    - `scripts/runtime/start-knowledge-worker.sh`
    These scripts make Crawl4AI preflight explicit for API and Parse Worker startup, while keeping worker loops fail-fast on nonzero process exits.
  - Added a multi-target `Dockerfile` (`api`, `parse-worker`, `knowledge-worker`) plus `.dockerignore`. The image build now preinstalls Playwright with `prepare_crawl4ai_runtime.py --install-if-missing --with-deps --no-probe`, pushing the “browser missing” class of failures into build time instead of first-request time.
  - Updated `README.md` and `specs/cortex-tech.md` with the new runtime-automation model, startup environment variables, Docker targets, and production guidance.
- Validation:
  - Focused code validation passed:
    - `python -m ruff check packages/parse/src/cortex_parse/__init__.py packages/parse/src/cortex_parse/playwright_runtime.py scripts/runtime/prepare_crawl4ai_runtime.py tests/unit/test_playwright_runtime.py tests/unit/test_runtime_config.py apps/api/src/cortex_api/lifespan.py workers/parse-worker/src/cortex_worker_parse/bootstrap.py`
    - `pyright packages/parse/src/cortex_parse/__init__.py packages/parse/src/cortex_parse/playwright_runtime.py scripts/runtime/prepare_crawl4ai_runtime.py tests/unit/test_playwright_runtime.py tests/unit/test_runtime_config.py apps/api/src/cortex_api/lifespan.py workers/parse-worker/src/cortex_worker_parse/bootstrap.py`
    - `python -m pytest tests/unit/test_playwright_runtime.py tests/unit/test_runtime_config.py tests/integration/test_parse_crawl4ai_adapter.py tests/unit/test_parse_request_compiler.py -q`
  - Runtime-prep verification passed in two modes:
    - `python scripts/runtime/prepare_crawl4ai_runtime.py --runtime-config configs/cortex.runtime.local.yaml --no-probe --json`
      -> returned `status=ok` with repo-local `base_directory` and `playwright_browsers_path`
    - `python scripts/runtime/prepare_crawl4ai_runtime.py --runtime-config configs/cortex.runtime.local.yaml --install-if-missing --json`
      -> returned structured `status=error`, `error_code=host_process_policy_blocked`, and remediation hints instead of an opaque stack trace, because the current Codex Windows session still blocks Playwright / Node child-process creation (`spawn EPERM`)
  - Docker image build was not executed inside this Codex session because the local `docker` client remained unable to reach the daemon here (`permission denied while trying to connect to the docker API at npipe:////./pipe/docker_engine`). The repository nevertheless now contains the concrete build recipe and runtime entrypoints for operator-side validation in a native shell.
- Prevention: Browser-backed parsers must be treated as part of deployment automation, not as a best-effort library detail. Keep browser install, system dependencies, startup probe, and host-policy diagnostics in a single explicit path (`prepare_crawl4ai_runtime.py` + runtime entrypoints + Dockerfile), and prefer Linux container deployment whenever the host cannot reliably permit Playwright child processes.

### 2026-04-17 09:20:00 +08:00 | Docker Build Failed On A Transient TLS EOF While Downloading `opencv-python`

- Stage: `CTX-20260417-067`, `CTX-20260417-068`
- Event: The new Docker build progressed past Python selection but then failed during `uv sync` when downloading `opencv-python`, with `peer closed connection without sending TLS close_notify`. The failure surfaced while resolving the API image, even though the actual heavyweight dependency came from `docling -> rapidocr -> opencv-python`.
- Cause: Two build-time issues were amplifying each other:
  - The Dockerfile still synced `--all-packages --all-groups`, which meant production image builds were downloading many packages unrelated to the final runtime role, increasing network pressure and build fragility.
  - The uv Docker invocation used no cache mount and no explicit network hardening, so a transient TLS EOF while fetching a large binary wheel caused the whole build to fail immediately.
- Action:
  - Refactored the Dockerfile so each target syncs only its own workspace package:
    - `cortex-api`
    - `cortex-worker-parse`
    - `cortex-worker-knowledge`
  - Removed `--all-groups` from production image syncs and switched to `--no-default-groups`, so lint / test / docs dependencies are no longer dragged into release builds.
  - Added uv Docker hardening:
    - `UV_CACHE_DIR=/root/.cache/uv`
    - `UV_HTTP_RETRIES=8`
    - `UV_HTTP_TIMEOUT=120`
    - `UV_NATIVE_TLS=true`
    - `UV_CONCURRENT_DOWNLOADS=1`
    - `RUN --mount=type=cache,target=/root/.cache/uv uv sync ...`
  These changes align with uv's official Docker guidance around cache mounts and reduce the probability that a single transient wheel-download interruption kills the whole image build.
- Validation:
  - Local command-shape validation passed with:
    - `uv sync --package cortex-api --no-default-groups --frozen --dry-run`
    - `uv sync --package cortex-worker-parse --no-default-groups --frozen --dry-run`
    - `uv sync --package cortex-worker-knowledge --no-default-groups --frozen --dry-run`
  - A full Docker image rebuild was not executed inside this Codex session because the Docker daemon remains inaccessible here, but the new Dockerfile is syntactically aligned with uv's official workspace/Docker integration patterns.
- Prevention: Production images should never be built with workspace-wide dev/test/docs dependency groups unless the image explicitly needs them. For binary-heavy Python stacks, always prefer cache-mounted package downloads, a stable TLS/certificate strategy, and lower parallel download pressure inside Docker builds.

### 2026-04-17 14:10:00 +08:00 | Docker Compose Was Promoted From Dependency Stack To Full Local Runtime, With Production Composition Split Out Explicitly

- Stage: `CTX-20260417-069 ~ CTX-20260417-071`
- Event: The repository previously had only a dependency-oriented `compose.local.yaml`, which meant operators still had to start the Cortex API and workers separately after Docker brought up PostgreSQL / MinIO / Redis / OTel. That was good enough for infrastructure checks but not for a true one-command local runtime or a reusable delivery story.
- Cause: Local developer ergonomics and production deployment safety pull in different directions. A single Compose file that always bundles Postgres, MinIO, Grafana, Jaeger, and Cortex services together is convenient for laptops, but it becomes the wrong abstraction for production where those dependencies are often managed services or separate infrastructure layers.
- Action:
  - Reworked `compose.local.yaml` into a batteries-included stack that now starts:
    - `postgres`
    - `minio`
    - `redis`
    - `otel-collector`
    - `jaeger-all-in-one`
    - `prometheus`
    - `grafana`
    - `cortex-migrate`
    - `cortex-api`
    - `cortex-parse-worker`
    - `cortex-knowledge-worker`
  - Added `compose.prod.yaml` as a separate production-oriented template that only orchestrates Cortex core containers against externally supplied Postgres / S3 / Redis / OTel endpoints, instead of baking local infra assumptions into production.
  - Updated local container wiring so Cortex services use container-safe defaults (`0.0.0.0`, service-name DNS such as `postgres`, `minio`, `redis`, `otel-collector`) while the checked-in runtime overlays remain vendor-neutral.
  - Added a one-shot `cortex-migrate` service so schema upgrades happen inside the same Compose topology before the API and workers start.
  - Updated `workers/knowledge-worker/pyproject.toml` to depend on `cortex-knowledge[runtime]`, ensuring the Docker knowledge-worker target resolves the Cognee runtime dependency instead of silently building a worker image without its primary runtime.
  - Extended `scripts/dev/stack.ps1` with service-aware readiness waits plus a `-Build` switch so local operators can do `stack.ps1 up -Build` when they want Compose to rebuild Cortex images from the current workspace before launch.
  - Updated `tests/integration/README.md` to reflect that the local Compose stack now includes the Cortex API and workers in addition to the supporting infrastructure.
- Validation:
  - `docker compose -p cortex-local -f compose.local.yaml config`
  - `docker compose -f compose.prod.yaml config`
  - `powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 sync --package cortex-api --no-default-groups --frozen --dry-run`
  - `powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 sync --package cortex-worker-parse --no-default-groups --frozen --dry-run`
  - `powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 sync --package cortex-worker-knowledge --no-default-groups --frozen --dry-run`
  - `powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run python scripts/ci/validate_yaml.py compose.local.yaml compose.prod.yaml`
- Notes:
  - In this Codex session, `docker compose config` succeeded but still emitted warnings about an unreadable Docker CLI config file under `C:\Users\hy\.docker\config.json`. That warning did not block Compose rendering, but actual `up/build/ps` execution still depends on the user shell having normal Docker Desktop / daemon access.
  - Because the Docker daemon is not reliably reachable from this Codex session, the full `docker compose up --build` path was validated structurally and through package-resolution dry-runs, not by running the live containers here.
- Prevention: Keep local and production Compose concerns separate. The local stack should optimize for fast all-in-one validation, while production Compose should stay narrowly focused on Cortex containers and assume managed or independently operated infrastructure. This prevents the common failure mode where a convenient laptop topology quietly becomes an accidental production architecture.

### 2026-04-19 11:20:00 +08:00 | Local Compose Was Too Eager To Preinstall Crawl4AI Browser Dependencies During Image Build

- Stage: `CTX-20260419-072 ~ CTX-20260419-074`
- Event: `powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 up -Build` failed before any meaningful local runtime validation could begin. The API image build ran `prepare_crawl4ai_runtime.py --install-if-missing --with-deps`, which delegated to `python -m playwright install --with-deps chromium`; that in turn hit transient Debian mirror `502 Bad Gateway` responses while fetching Linux packages. After the compose build failed, `stack.ps1` still continued into readiness waits and eventually reported a misleading PostgreSQL timeout.
- Cause:
  - The Dockerfile treated local and production image builds identically, always preinstalling Crawl4AI browser/system dependencies at build time.
  - Local compose is often used for broad API validation, not specifically for browser-backed parsing, so forcing Crawl4AI preinstallation into every local build made the whole stack fragile.
  - `scripts/dev/stack.ps1` did not exit immediately when `docker compose up` failed, so the first actionable error was buried under a later port-wait timeout.
- Action:
  - Added an optional Docker build argument `CORTEX_PREPARE_CRAWL4AI_RUNTIME` and guarded the API / Parse Worker build-time runtime-prep step with it.
  - Updated `compose.local.yaml` to:
    - pass `CORTEX_RUNTIME_CONFIG_PATH=configs/cortex.runtime.local.yaml` as a build arg
    - set `CORTEX_PREPARE_CRAWL4AI_RUNTIME=0` for local API / Parse Worker image builds
    - set `CORTEX_CRAWL4AI_SKIP_PROBE=1` in local container runtime env so the local stack can start without forcing immediate browser startup validation
  - Updated `scripts/dev/stack.ps1` to exit immediately when `docker compose up`, `down`, `ps`, `logs`, or `restart` returns a non-zero exit code instead of continuing into unrelated readiness waits.
- Validation:
  - `docker compose -p cortex-local -f compose.local.yaml config`
  - `powershell -NoProfile -Command "[void][ScriptBlock]::Create((Get-Content 'scripts/dev/stack.ps1' -Raw)); Write-Output 'stack.ps1 syntax ok'"`
  - `powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run python scripts/ci/validate_yaml.py compose.local.yaml`
- Operator guidance:
  - For local API testing, rerun `powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 up -Build`. The stack will now skip Crawl4AI browser preinstall during image build and should no longer be blocked by transient Debian mirror failures.
  - If the goal is specifically to validate `crawl4ai` inside containers, treat that as a separate browser-runtime preparation step and prefer a Linux environment or a stable mirror/proxy path for Playwright system packages.

### 2026-04-19 14:40:00 +08:00 | Containerized Crawl4AI Was Switched From Lazy-Avoidance To A Real Playwright Runtime Path

- Stage: `CTX-20260419-075 ~ CTX-20260419-077`
- Event: After the earlier local-compose resilience patch, the remaining gap was that local Docker validation could start the stack but still did not prove `crawl4ai` itself worked inside the shipped containers. The user explicitly asked to “把 crawl4ai 容器内也打通”.
- Cause:
  - The first workaround solved only the mirror-instability problem by skipping browser preparation, not the actual in-container browser-runtime path.
  - The runtime config still resolved Playwright browsers into repo-local `.data/...` paths, which is correct for host-mode execution but wrong once the container already ships browsers under `/ms-playwright`.
  - The API / Parse Worker containers also lacked explicit `init` / shared-memory tuning for Chromium.
- Action:
  - Reworked `Dockerfile` so `api` and `parse-worker` now build from Playwright's official Python image `mcr.microsoft.com/playwright/python:v1.58.0-noble`, while `knowledge-worker` stays on the slim Python base image.
  - Removed build-time `playwright install --with-deps` from the Cortex image flow. The official image already contains browser binaries and Linux system dependencies, so image builds no longer depend on live Debian mirror health.
  - Kept build-time runtime preparation in `--no-probe` mode to validate config wiring without forcing a browser launch during Docker build, and left the real browser preflight to container startup.
  - Extended `cortex_parse.playwright_runtime.resolve_crawl4ai_playwright_runtime()` to respect container-specific overrides:
    - `CORTEX_PLAYWRIGHT_BROWSERS_PATH`
    - `CORTEX_CRAWL4AI_BASE_DIRECTORY`
    This preserves vendor-neutral runtime YAML while allowing Docker to bind the browser path to `/ms-playwright`.
  - Updated `compose.local.yaml` and `compose.prod.yaml` to set `CORTEX_PLAYWRIGHT_BROWSERS_PATH=/ms-playwright`, re-enable Crawl4AI startup probing, and add `init: true` plus `shm_size: 1gb` for `cortex-api` and `cortex-parse-worker`.
  - Updated `.env.example`, `.env.prod.example`, `README.md`, and `specs/cortex-tech.md` so operators can see the new container runtime contract directly in the repo.
  - Added a focused unit regression test proving the runtime resolver prefers container env overrides over the host-oriented runtime YAML browser path.
- Validation:
  - `docker compose -p cortex-local -f compose.local.yaml config`
  - `docker compose -f compose.prod.yaml config`
  - `powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run python scripts/ci/validate_yaml.py compose.local.yaml compose.prod.yaml`
  - `powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run python -m pytest tests/unit/test_playwright_runtime.py -q`
  - `powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run python -m ruff check packages/parse/src/cortex_parse/playwright_runtime.py tests/unit/test_playwright_runtime.py`
- Notes:
  - In this Codex session the Docker daemon is still not directly callable, so the live `docker compose up -Build` browser launch could not be executed here. The repository was instead updated to the documented Playwright container pattern from the official docs, and the Compose/rendered-config path plus focused runtime tests were revalidated locally.
  - Official references used for this correction:
    - Playwright Docker docs: https://playwright.dev/python/docs/docker
    - Crawl4AI installation/runtime docs: https://docs.crawl4ai.com/core/installation/
- Prevention: For browser-backed parsers, treat the browser runtime as part of the image contract, not an optional runtime side effect. Host-mode overlays may still point to repo-local directories, but container deployments should always override the browser path explicitly and rely on prebuilt browser images instead of first-boot installation.

### 2026-04-19 15:05:00 +08:00 | Focused Validation Exposed Two Corrupted `.venv` Packages

- Stage: `CTX-20260419-077`
- Event: Focused validation initially failed during import, first on `python-dotenv` and then on `google.protobuf`, even though both packages appeared in `.venv` metadata.
- Cause:
  - The active `.venv` contained stale / partial installs where only `.dist-info` remained but the importable module packages were missing.
  - `cortex-common` also relied on `python-dotenv` transitively through `pydantic-settings` without declaring it as a direct runtime dependency, which made the missing package harder to reason about in minimal-sync environments.
- Action:
  - Declared `python-dotenv>=1.1,<2` explicitly in `packages/common/pyproject.toml`.
  - Re-locked the workspace and re-synced the repo-managed `.venv`.
  - Reinstalled the corrupted local packages in place for validation:
    - `python-dotenv==1.2.2`
    - `protobuf==6.33.6`
- Validation:
  - `powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run python -c "import dotenv; print(dotenv.__file__)"`
  - `powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run python -c "import google.protobuf; print(google.protobuf.__file__)"`
  - `powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run python -m pytest tests/unit/test_playwright_runtime.py -q`
  - `powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run pyright packages/parse/src/cortex_parse/playwright_runtime.py tests/unit/test_playwright_runtime.py`
  - `powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run python -m ruff check packages/parse/src/cortex_parse/playwright_runtime.py tests/unit/test_playwright_runtime.py`
- Prevention: When a package shows up in `pip show` but import still fails, inspect `.venv\\Lib\\site-packages` directly before assuming the repo dependency graph is wrong. For Cortex itself, keep transitive imports like `python-dotenv` declared in the owning runtime package instead of relying on toolchain or dev-group coincidence.

### 2026-04-20 10:05:00 +08:00 | Docker Build Failed Because `.python-version` Was More Specific Than The Container Python

- Stage: `CTX-20260420-078`
- Event: Docker image builds for `cortex-api` and `cortex-parse-worker` failed during `uv sync` with `error: No interpreter found for Python 3.12.12 in search path`.
- Cause:
  - The repository pins local development Python with `.python-version=3.12.12`.
  - `uv` treats `.python-version` as an explicit Python version request.
  - The Playwright Python base image ships a compatible Python 3.12 interpreter, but not necessarily patch `3.12.12`.
  - Because the Docker build also sets `UV_PYTHON_PREFERENCE=only-system` and `UV_PYTHON_DOWNLOADS=never`, `uv` cannot download a matching managed interpreter and therefore fails fast.
- Action:
  - Updated each Docker `uv sync` invocation to pass `--python "$(command -v python)"`, forcing `uv` to use the container's active system interpreter path instead of resolving against `.python-version`.
  - Applied the same fix consistently to `api`, `parse-worker`, and `knowledge-worker` targets so all build targets follow one rule.
- Validation:
  - Structural validation only in this Codex session: the Dockerfile now resolves the interpreter from the running image shell instead of relying on version-file discovery.
  - Recommended operator recheck:
    - `powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 up -Build`
    - or `docker compose -p cortex-local -f compose.local.yaml build --no-cache cortex-api cortex-parse-worker`
- Prevention: Keep `.python-version` as the local developer pin, but do not let container builds discover Python indirectly from project files when the image already provides a system interpreter. In Docker, prefer explicit interpreter binding (`--python <path>`) over version-file discovery.

### 2026-04-21 09:35:00 +08:00 | Crawl4AI Adapter Overrode Container Browser Path Back To `.data`

- Stage: `CTX-20260421-079`
- Event: Docker started successfully, but live `crawl4ai` parse failed with `BrowserType.launch: Executable doesn't exist at /app/.data/playwright/local/chromium-1208/chrome-linux64/chrome`.
- Cause:
  - The container had `CORTEX_PLAYWRIGHT_BROWSERS_PATH=/ms-playwright`, and runtime preflight resolution already understood that override.
  - During actual parse execution, `Crawl4AIParseEngine._ensure_playwright_browsers_path()` independently preferred `self._config["playwright_browsers_path"]` over `PLAYWRIGHT_BROWSERS_PATH`.
  - `_crawl4ai_config()` populated that config from `configs/cortex.runtime.local.yaml`, so the adapter reset Playwright back to `/app/.data/playwright/local`, where no browser exists in the container.
- Action:
  - Changed the adapter precedence to:
    - `CORTEX_PLAYWRIGHT_BROWSERS_PATH`
    - `PLAYWRIGHT_BROWSERS_PATH`
    - runtime config `playwright_browsers_path`
    - repo-local default
  - Applied the same environment-first pattern to Crawl4AI base-directory resolution through `CORTEX_CRAWL4AI_BASE_DIRECTORY`, `CRAWL4_AI_BASE_DIRECTORY`, and `CRAWL4AI_BASE_DIRECTORY`.
  - Added an integration regression test proving `CORTEX_PLAYWRIGHT_BROWSERS_PATH` wins over a conflicting runtime-config browser path.
- Validation:
  - `powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run python -m pytest tests/integration/test_parse_crawl4ai_adapter.py tests/unit/test_playwright_runtime.py -q`
  - `powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run python -m ruff check packages/parse/src/cortex_parse/adapters/crawl4ai.py tests/integration/test_parse_crawl4ai_adapter.py`
  - `powershell -ExecutionPolicy Bypass -File scripts\dev\uv.ps1 run pyright packages/parse/src/cortex_parse/adapters/crawl4ai.py tests/integration/test_parse_crawl4ai_adapter.py`
- Prevention: Runtime preflight and adapter execution must share the same precedence model. Container overrides must always win over host-oriented YAML paths, otherwise startup validation and request-time behavior can diverge.

### 2026-04-21 15:37:24 +08:00 | Crawl4AI Failed On Missing Optional `storage_state.json`

- Stage: `CTX-20260421-080`
- Event: After starting `cortex-api`, live `crawl4ai` parsing failed with `No such file or directory: ...secrets\\crawl4ai\\local\\storage_state.json`.
- Cause:
  - The local runtime overlay defines `parse.engines.crawl4ai.storage_state_ref` as a conventional path for authenticated crawling.
  - `LoadedRuntimeConfig.resolve_reference("path:...")` correctly resolves the path even if the file does not exist.
  - `_crawl4ai_config()` treated that optional path as an active `BrowserConfig.storage_state`, so Playwright tried to open a non-existent cookie/localStorage state file during ordinary public-page crawling.
- Action:
  - Added `_resolve_existing_storage_state()` to Crawl4AI parse bootstrap.
  - Runtime `storage_state_ref` now injects `browser_config.storage_state` only when the referenced file exists.
  - Existing authenticated crawling behavior is preserved: once the operator creates the JSON state file at the configured path, Cortex automatically passes it to Crawl4AI.
- Validation:
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 run python -m pytest tests/unit/test_runtime_config.py tests/integration/test_parse_crawl4ai_adapter.py -q`
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 run python -m ruff check packages/parse/src/cortex_parse/bootstrap.py tests/unit/test_runtime_config.py`
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 run pyright packages/parse/src/cortex_parse/bootstrap.py tests/unit/test_runtime_config.py`
- Prevention: Optional runtime references that point to operator-managed secrets must fail open when absent and fail closed only when an explicit API/profile request requires them. Default public crawling should never be blocked by a missing authentication-state placeholder.
- Prevention: The local compose path should optimize for “start the API and the platform around it” rather than “prove every optional browser dependency can be installed from the public internet right now.” Keep production images fail-fast, but make local builds resilient by deferring optional browser preparation until the operator actually needs browser-backed parsing.

### 2026-04-21 18:10:00 +08:00 | Docker Images Were Bloated By Docling/Torch Being On The Default Parse Path

- Stage: `CTX-20260421-081 ~ CTX-20260421-083`
- Event: Docker image builds failed while downloading `torch==2.11.0`, pulled through `cortex-api -> cortex-parse -> docling -> torch`. The same dependency path also made `cortex-api` and `cortex-parse-worker` images grow to roughly 12GB, and the build/deploy story was still not explicit enough about the `knowledge-worker` image.
- Cause:
  - `docling` was a hard runtime dependency of `cortex-parse`, so every API and Parse Worker image inherited the heaviest document/OCR/ML stack even when the deployment only needed Crawl4AI, Jina Reader, LlamaParse, or basic MarkItDown parsing.
  - `markitdown[all]` was also installed by default, pulling optional converters that are useful for document nodes but too broad for the default online API image.
  - Docker Compose already had a Knowledge Worker service/target, but the runbook did not clearly present it alongside the API / Parse Worker / optional heavy parser split.
- Action:
  - Moved `docling` out of `cortex-parse` base dependencies and into optional extras.
  - Split parse extras into `default-engines`, `document-engines`, `markitdown-all`, and `all-engines`.
  - Changed `cortex-api` and default `cortex-worker-parse` to depend on `cortex-parse[default-engines]`, which keeps `crawl4ai`, `llama_parse`, and base `markitdown` without installing `docling` or `torch`.
  - Made the Docling adapter mark itself disabled when the optional dependency is absent, instead of failing at import time.
  - Added a dedicated Docker target `parse-worker-docling` and local/production Compose profile service `cortex-parse-worker-docling`.
  - Kept `knowledge-worker` as a first-class Docker target and Compose service, with documentation updated to show it in the standard topology.
- Validation:
  - Default API package-plan validation used a clean temporary uv environment and confirmed `docling=False`, `torch=False`, `markitdown=True`, `speech_recognition=False`, `crawl4ai=True`, and `llama_parse=True`.
  - Docling worker package-plan dry-run confirmed the heavy dependencies are isolated behind the optional Docling worker profile, including `docling==2.88.0`, `torch==2.11.0`, and `opencv-python==4.13.0.92`.
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 lock`
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 run python -m pytest tests\\integration\\test_parse_additional_adapters.py tests\\unit\\test_runtime_config.py -q`
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 run python -m ruff check packages\\parse\\src\\cortex_parse\\adapters\\docling.py tests\\integration\\test_parse_additional_adapters.py`
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 run pyright packages\\parse\\src\\cortex_parse\\adapters\\docling.py tests\\integration\\test_parse_additional_adapters.py`
  - `docker compose -p cortex-local -f compose.local.yaml config`
  - `docker compose -p cortex-local -f compose.local.yaml --profile docling config --services`
  - `docker compose -f compose.prod.yaml config`
  - `docker compose -f compose.prod.yaml --profile docling config --services`
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 run python scripts\\ci\\validate_yaml.py compose.local.yaml compose.prod.yaml`
- Notes:
  - The Compose config commands still emitted a local Docker CLI warning about `C:\\Users\\hy\\.docker\\config.json` access. Config rendering succeeded; the warning belongs to the operator shell's Docker config permissions, not Cortex YAML.
  - The validation intentionally avoided building the Docling image in this session because it is expected to download the large Docling/Torch stack; the important invariant is that the default API / Parse Worker images no longer do so.
- Prevention: Heavy parser runtimes must be opt-in deployment units. Keep the default API image focused on the control plane and common online parsers, and scale ML/OCR-heavy document parsing through dedicated worker images, profiles, queues, and release cadence.

### 2026-04-21 19:05:00 +08:00 | Knowledge Worker Build Still Depended On Docker Hub Python Base

- Stage: `CTX-20260421-084`
- Event: `docker compose up -Build` failed while resolving the `knowledge-worker` base image: `python:3.12.12-slim: failed to do request ... EOF`.
- Cause:
  - API and Parse Worker images had already moved to the MCR Playwright Python base, but `knowledge-worker` still used Docker Hub `python:3.12.12-slim`.
  - The Dockerfile also installed `uv` with `pip install`, adding another runtime network dependency during image build.
- Action:
  - Changed the default non-browser Python base to `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`.
  - Added an explicit `uv-bin` stage from `ghcr.io/astral-sh/uv:0.7.22` and copied `/uv` plus `/uvx` into both Python and Playwright bases.
  - Removed `pip install "uv>=0.7,<0.8"` from image builds.
  - Exposed local Compose build-arg overrides:
    - `CORTEX_PYTHON_BASE_IMAGE`
    - `CORTEX_UV_IMAGE`
    - `CORTEX_PLAYWRIGHT_PYTHON_BASE_IMAGE`
  - Updated README and technical design with the new image-source strategy and mirror override guidance.
- Validation:
  - `docker manifest inspect ghcr.io/astral-sh/uv:0.7.22`
  - `docker manifest inspect ghcr.io/astral-sh/uv:python3.12-bookworm-slim`
  - `docker compose -p cortex-local -f compose.local.yaml config --quiet`
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 run python scripts\\ci\\validate_yaml.py compose.local.yaml compose.prod.yaml`
- Notes:
  - A live `docker build --target knowledge-worker` could not be executed from this Codex process because the Docker daemon pipe returned `Access is denied`. Retrying with a repo-local `DOCKER_CONFIG` bypassed the CLI config read issue but still could not connect to the daemon from this process.
  - The operator shell that can already run Docker should retry the build directly; the rendered Compose config and remote manifests now avoid the failing Docker Hub Python base.
- Prevention: Every build-stage network dependency should be an explicit, overrideable artifact source. For local and CI reliability, avoid mixing Docker Hub, PyPI bootstrap installs, and runtime package syncs when a pinned official image can provide the same toolchain baseline.

### 2026-04-21 21:05:00 +08:00 | Parse Job Submission Failed Because `jobs.target_id` Was UUID-Sized

- Stage: `CTX-20260421-085`
- Event: Calling `/v1/parse/jobs` with `https://docs.cognee.ai/core-concepts/overview` failed in PostgreSQL with `asyncpg.exceptions.StringDataRightTruncationError: value too long for type character varying(36)`.
- Cause:
  - `jobs.target_id` was modeled as `VARCHAR(36)`, which only fits UUID-like object IDs.
  - Parse jobs store a human-readable target locator in that field, and URL/S3/file locators routinely exceed 36 characters.
  - The full request was already preserved in `jobs.request_json`, but the indexed target summary column still needed to support real-world locator lengths.
- Action:
  - Changed ORM metadata `JobModel.target_id` from `String(36)` to `String(2048)`.
  - Updated `specs/cortex-init.sql` so fresh databases create `jobs.target_id VARCHAR(2048)`.
  - Added Alembic migration `20260421_191500_widen_jobs_target_id.py` to widen existing databases.
  - Updated `specs/cortex-schema.md` to document that `target_id` may contain URL, S3 locator, object ID, or file URI summaries.
  - Added a schema regression test and changed the async Parse Job integration test to submit a long URL target.
- Validation:
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 run python -m pytest tests\\unit\\test_db_schema.py tests\\integration\\test_api_parse.py::test_async_parse_job_submit_worker_and_result -q`
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 run python -m pytest tests\\integration\\test_api_parse.py -q`
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 run python -m ruff check packages\\db\\src\\cortex_db\\models.py packages\\db\\migrations\\versions\\20260421_191500_widen_jobs_target_id.py tests\\unit\\test_db_schema.py tests\\integration\\test_api_parse.py`
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 run pyright packages\\db\\src\\cortex_db\\models.py packages\\db\\migrations\\versions\\20260421_191500_widen_jobs_target_id.py tests\\unit\\test_db_schema.py tests\\integration\\test_api_parse.py`
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 run python scripts\\ci\\validate_yaml.py specs\\cortex-api.yaml specs\\cortex-init.sql specs\\cortex-schema.md compose.local.yaml compose.prod.yaml`
- Notes:
  - The focused integration test confirmed Alembic applies the new migration after the baseline schema before submitting the long-URL Parse Job.
  - Test startup had to bypass live Crawl4AI browser probing because this regression targets database/job-control behavior rather than Playwright host availability.
- Prevention: Any job target summary column must be sized for the public API locator contract, not for internal UUIDs only. Keep canonical request state in JSON, but make indexed summary columns tolerant of URL/S3/file locator lengths.

### 2026-04-22 10:20:00 +08:00 | Swagger Storage Upload Rejected Minimal Single-Part Requests

- Stage: `CTX-20260422-086`
- Event: Calling `POST /v1/storage/uploads` from Swagger UI with a minimal single-part body failed with `422 validation_error` because `body.size_bytes` was required.
- Cause:
  - `StorageUploadCreateRequest.size_bytes` was modeled as mandatory for every upload, even though single-part uploads only need a signed PUT URL and can discover the final object size later.
  - Swagger examples and route descriptions reinforced that stricter contract, so users were pushed toward unnecessary bookkeeping before they could even start a basic upload.
- Action:
  - Made `size_bytes` optional for `single_part` uploads while keeping it mandatory for explicit `multipart` initialization.
  - Added a targeted business-validation error for `upload_mode=multipart` without `size_bytes`, including a `body.size_bytes` field error with operator-friendly guidance.
  - Completed single-part uploads now issue an object-store `head_object` call to recover the final `ContentLength`, `ETag`, and `ContentType` when available before committing object metadata.
  - Updated Swagger/OpenAPI examples, the storage route description, schema notes, README examples, and regression coverage so the recommended single-part flow is minimal and directly reusable.
- Validation:
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 run python -m pytest tests\\contract\\test_foundation_models.py tests\\integration\\test_api_storage.py tests\\integration\\test_api_e2e.py tests\\contract\\test_openapi_contract.py -q`
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 run python -m ruff check apps\\api\\src\\cortex_api\\lifespan.py apps\\api\\src\\cortex_api\\routers\\storage.py packages\\contracts\\src\\cortex_contracts\\storage.py packages\\contracts\\src\\cortex_contracts\\openapi_examples.py packages\\storage\\src\\cortex_storage\\client.py packages\\storage\\src\\cortex_storage\\service.py tests\\contract\\test_foundation_models.py tests\\integration\\test_api_storage.py tests\\integration\\test_api_e2e.py tests\\contract\\test_openapi_contract.py`
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 run pyright apps\\api\\src\\cortex_api\\lifespan.py apps\\api\\src\\cortex_api\\routers\\storage.py packages\\contracts\\src\\cortex_contracts\\storage.py packages\\contracts\\src\\cortex_contracts\\openapi_examples.py packages\\storage\\src\\cortex_storage\\client.py packages\\storage\\src\\cortex_storage\\service.py tests\\contract\\test_foundation_models.py tests\\integration\\test_api_storage.py tests\\integration\\test_api_e2e.py tests\\contract\\test_openapi_contract.py`
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 run python scripts\\ci\\validate_yaml.py specs\\cortex-api.yaml`
- Prevention: Keep the public upload contract aligned with the actual transfer primitive. Single-part signed PUT flows should optimize for minimal required input, while multipart flows should fail with explicit, field-level guidance only when the server genuinely needs precomputed size information.

### 2026-04-22 14:40:00 +08:00 | Auth Surface Simplified, Idempotency Scoped, Storage Init Minimized

- Stage: `CTX-20260422-087`, `CTX-20260422-088`, `CTX-20260422-089`
- Event: Reviewed whether `BootstrapIssuerSecret`, broad `Idempotency-Key` exposure, and the current Storage upload-init contract were actually necessary for the public API.
- Analysis:
  - The built-in bootstrap issuer made Cortex look like a token-minting service even though the platform is intentionally designed as a resource server; the extra secret and endpoint added operator burden without being required for the core product workflow.
  - `Idempotency-Key` only had real deduplication semantics on async job submission (`jobs` rows are uniquely keyed by tenant/job type/idempotency key). On synchronous parse, dataset creation, and storage upload-init it was merely documented, then ignored.
  - `completeUploadSession` is still required because bytes move directly to object storage; Cortex needs an explicit finalize step to verify object visibility, recover provider metadata, and commit durable object/version state.
  - For `createUploadSession`, `upload_mode`, `part_size_bytes`, `bucket_ref`, and `object_prefix` are server-owned routing knobs rather than caller-owned business inputs. `content_type` is inferable from `filename` and can be reconciled again during completion.
- Action:
  - Removed the public `/v1/auth/token` route, bootstrap issuer models, Bootstrap issuer secret header/scheme, and the related runtime/config examples from code, OpenAPI, README, compose, and `.env` templates.
  - Kept bearer-token authentication support in `dev`, `jwt`, `introspection`, and `hybrid` modes, but clarified that tokens now come from local dev tooling, CI secret injection, or external IdPs rather than a Cortex-owned minting API.
  - Removed `Idempotency-Key` from sync parse, dataset creation, and storage upload-init routes; kept it only on async Parse / Add / Cognify / Memify job submission APIs where the repository layer actually enforces deduplication.
  - Simplified `StorageUploadCreateRequest` so callers send only filename, optional known size, and business metadata. Cortex now infers `content_type`, decides single-part vs multipart from the known size, and owns bucket/object-key routing and multipart part sizing.
  - Added regression coverage proving filename-based `content_type` inference and the default single-part behavior when upload size is unknown.
  - Fixed a repeated test-harness pitfall by setting `CORTEX_CRAWL4AI_SKIP_PROBE=1` in the knowledge API integration client, preventing unrelated Playwright browser preflight failures from masking business/API regressions.
- Validation:
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 run python -m pytest tests\\unit\\test_common_auth.py tests\\contract\\test_foundation_models.py tests\\contract\\test_openapi_contract.py tests\\integration\\test_api_storage.py tests\\integration\\test_api_e2e.py tests\\integration\\test_api_parse.py tests\\integration\\test_api_knowledge.py -q`
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 run python -m ruff check apps\\api\\src\\cortex_api\\main.py apps\\api\\src\\cortex_api\\lifespan.py apps\\api\\src\\cortex_api\\dependencies\\auth.py apps\\api\\src\\cortex_api\\dependencies\\runtime.py apps\\api\\src\\cortex_api\\routers\\parse.py apps\\api\\src\\cortex_api\\routers\\knowledge.py apps\\api\\src\\cortex_api\\routers\\storage.py packages\\auth\\src\\cortex_auth\\__init__.py packages\\common\\src\\cortex_common\\settings.py packages\\contracts\\src\\cortex_contracts\\__init__.py packages\\contracts\\src\\cortex_contracts\\headers.py packages\\contracts\\src\\cortex_contracts\\openapi_examples.py packages\\contracts\\src\\cortex_contracts\\storage.py packages\\storage\\src\\cortex_storage\\service.py tests\\contract\\test_foundation_models.py tests\\contract\\test_openapi_contract.py tests\\integration\\test_api_storage.py tests\\integration\\test_api_e2e.py tests\\integration\\test_api_knowledge.py tests\\unit\\test_common_auth.py`
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 run pyright apps\\api\\src\\cortex_api\\main.py apps\\api\\src\\cortex_api\\lifespan.py apps\\api\\src\\cortex_api\\dependencies\\auth.py apps\\api\\src\\cortex_api\\dependencies\\runtime.py apps\\api\\src\\cortex_api\\routers\\parse.py apps\\api\\src\\cortex_api\\routers\\knowledge.py apps\\api\\src\\cortex_api\\routers\\storage.py packages\\auth\\src\\cortex_auth\\__init__.py packages\\common\\src\\cortex_common\\settings.py packages\\contracts\\src\\cortex_contracts\\__init__.py packages\\contracts\\src\\cortex_contracts\\headers.py packages\\contracts\\src\\cortex_contracts\\openapi_examples.py packages\\contracts\\src\\cortex_contracts\\storage.py packages\\storage\\src\\cortex_storage\\service.py tests\\contract\\test_foundation_models.py tests\\contract\\test_openapi_contract.py tests\\integration\\test_api_storage.py tests\\integration\\test_api_e2e.py tests\\integration\\test_api_knowledge.py tests\\unit\\test_common_auth.py`
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 run python scripts\\ci\\validate_yaml.py specs\\cortex-api.yaml`
  - `git diff --check` (passed; CRLF normalization warnings only)
- Prevention: Keep public APIs aligned with real server semantics. If a feature has no durable state transition or no repository-backed deduplication behind it, do not expose it as a first-class public contract just because it feels “enterprise”. Let the server own routing policy, and reserve public fields for caller-owned intent.

### 2026-04-22 15:35:00 +08:00 | Suppressed Known Upstream Cognee/Pydantic Deprecation Noise

- Stage: `CTX-20260422-090`
- Event: Even after the auth/storage contract cleanup passed, pytest still printed a small set of third-party deprecation warnings from `cognee==0.5.8` and its Pydantic v2 integration, which polluted local verification output.
- Cause:
  - Importing `cognee` currently triggers three known upstream deprecations: the deprecated FastAPI status constant `HTTP_422_UNPROCESSABLE_ENTITY`, a `Field(..., env=...)` Pydantic warning, and repeated `json_encoders` deprecation warnings from Pydantic schema generation.
  - These warnings are upstream package hygiene issues rather than Cortex behavior regressions, but they still make test output noisier and harder to scan.
- Action:
  - Added a narrow warning-suppression context inside `cortex_knowledge.runtime` so optional `cognee` imports ignore only those known upstream deprecations.
  - Wrapped Cognee submodule imports used by memify/user helpers with the same suppression helper so follow-on imports stay clean.
  - Added `tests/conftest.py` with pytest-only warning filters for the same three patterns, keeping the test runner quiet without muting unrelated deprecations.
  - Added a focused regression test proving `_load_cognee_module()` can import a warning-emitting module without leaking those known warnings.
- Validation:
  - `.\\.venv\\Scripts\\python.exe -m pytest tests\\unit\\test_cognee_runtime_adapter.py tests\\contract\\test_openapi_contract.py::test_metrics_endpoint_returns_prometheus_text -q -W always`
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 run python -m pytest tests\\unit\\test_cognee_runtime_adapter.py tests\\unit\\test_knowledge_helpers.py tests\\unit\\test_runtime_config.py tests\\contract\\test_openapi_contract.py -q`
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 run python -m ruff check packages\\knowledge\\src\\cortex_knowledge\\runtime.py tests\\conftest.py tests\\unit\\test_cognee_runtime_adapter.py`
  - `powershell -ExecutionPolicy Bypass -File scripts\\dev\\uv.ps1 run pyright packages\\knowledge\\src\\cortex_knowledge\\runtime.py tests\\conftest.py tests\\unit\\test_cognee_runtime_adapter.py`
  - `git diff --check` (passed; CRLF normalization warnings only)
- Prevention: Treat noisy upstream deprecations as a test-hygiene problem, not a reason to globally mute warnings. Keep suppression patterns message- and module-specific, and delete them once Cognee/Pydantic upstreams ship compatible releases.
