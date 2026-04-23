# Cortex PRD

## 1. 产品概述

### 1.1 产品名称

`Cortex`

### 1.2 产品定位

Cortex 是一套面向 AI 原生应用的基础能力 API，提供：

1. 网页到 LLM-ready Markdown 的标准化解析能力。
2. 面向任意文件格式的对象存储上传下载能力。
3. 面向知识图谱与混合检索的 Cognee 编排能力。

它的核心价值不是“多做一套爬虫/文件服务”，而是把**内容获取、内容存储、知识加工、知识检索**统一成一个可移植、可扩展、可审计的控制平面。

### 1.3 产品目标

- 把任意 URL、文件或文本快速纳入 AI 可消费的数据平面。
- 以厂商中立方式承接对象存储、关系库、向量库、图数据库。
- 同时支持同步交互场景和异步批量场景。
- 为上层 Agent、RAG、知识运营、审计系统提供统一 API。

### 1.4 非目标

- 不直接提供面向最终消费者的聊天 UI。
- 不在第一阶段自研图数据库或向量数据库。
- 不把工作重点放在单一云厂商专有能力上。

## 2. 背景与问题

当前 AI 应用在工程上通常面临四个断裂：

1. **内容入口断裂**：网页解析、文件上传、文本接入分散在不同系统里。
2. **知识加工断裂**：从抓取到 chunk、summary、graph、search 之间缺少统一对象模型。
3. **供应商断裂**：一旦绑定某家对象存储或数据库，迁移成本高。
4. **运行治理断裂**：长任务、重试、审计、回调、可观测性常常临时拼装。

Cortex 的产品目标就是消除这四个断裂。

## 3. 目标用户

### 3.1 AI 平台工程师

需要一个稳定 API，把外部内容和内部文件管道纳入统一数据面。

### 3.2 知识工程师

需要把 URL、文档和文本快速转成可检索、可追溯的知识图谱。

### 3.3 Agent / Workflow 开发者

需要同步拿结果，也需要异步批量跑作业，还要保留 provenance。

### 3.4 安全与审计团队

需要知道谁抓了什么、存了什么、索引了什么、答复引用了什么。

## 4. 典型场景

### 场景 A：网页情报采集

用户提交一批 URL，系统自动抓取、处理认证态页面、生成 Markdown、保存截图/PDF，并写入知识数据集。

### 场景 B：文件知识库构建

用户上传 PDF、DOCX、图片或结构化文件，系统存入对象存储，再触发 Add + Cognify，形成可搜索图谱。

### 场景 C：代码规范 / 业务规则沉淀

在 Cognify 完成后运行 Memify，把规则、三元组嵌入或会话记忆写回图谱。

### 场景 D：Agent 检索

Agent 对多个数据集发起混合搜索，返回答案、命中片段与引用来源。

## 5. 产品范围

### 5.1 Cortex Parse API

必须支持：

- 任意 URL 抓取
- 对象存储文件解析与外部文件 URI 解析
- 同步与异步两种调用模式
- 同步接口默认不超过 3 个顶层参数，异步作业接口不超过 5 个顶层参数
- LLM-ready Markdown 输出
- 标准元数据输出
- 分类标签与审计字段
- 多解析引擎可插拔接入
- 基于 `engine_id + scene -> profile/preset` 的自动策略切换
- 引擎 fallback 与标准化输出

重点能力：

- `sources` 统一承载 `url / cortex://objects/{object_id} / uri`，支持单条或批量
- `engine_id` 作为公开主选择器
- `scene` 作为高层场景意图，而不是暴露大量底层 adapter 参数
- `crawl4ai` 的 `balanced / deep_web / authenticated_web` 强配置 preset
- 文档引擎的 `document_fidelity / document_ai / lightweight` preset

### 5.2 Cortex Storage API

必须支持：

- 任意格式文件上传
- 任意格式文件下载
- 对象元数据关系化存储
- 小文件单段上传与大文件 multipart
- 预签名 URL 模式
- Swagger / 本地测试 / 小文件的一步上传模式
- 版本、哈希、审计信息

### 5.3 Cortex Cognee API

必须覆盖 Cognee 的四类主操作：

1. `Add`
2. `Cognify`
3. `Memify`
4. `Search`

并以 Cortex 风格提供：

- 数据集边界
- 作业状态
- webhook 回调
- 审计与 provenance

### 5.4 Cortex Authorization & Governance

必须支持：

- 基于 OAuth 2.0 / OIDC 的 API 认证
- 明确区分“Cortex 作为资源服务器验 token”与“外部 IdP 或可选内建 issuer 签发 token”的职责边界
- 功能权限与数据权限的分层治理
- 多租户默认隔离
- 角色绑定、资源级授权与策略审计
- 对 Search、Download URL、Job 查询这类高风险接口做二次资源授权

产品要求补充：

- 当部署接入外部 IdP 时，用户 token 获取流程应直接复用外部 OAuth 2.0 / OIDC 能力。
- 当部署处于本地、自托管或早期 bootstrap 阶段时，系统应支持一个可选的内建 token issuance API，为不同 actor / tenant / scope 组合签发 bearer token。
- 内建 issuance 只适用于 `dev` / `jwt` / `hybrid`；`introspection` 模式必须保持 external-only。

### 5.5 通用控制面

必须支持：

- 统一作业模型
- 统一错误模型
- 幂等键
- 健康检查
- 事件与日志跟踪

## 6. 功能需求

### FR-1 Parse 输入

系统必须接受：

- `sources`
- `engine_id`
- 可选 `scene`
- 异步场景下可选 `priority`
- 异步场景下可选 `webhook`

并满足：

- `sources` 统一覆盖 `url / cortex://objects/{object_id} / uri`
- 系统自动推断来源类型、文件名与 MIME，不要求调用方再传 `kind` 或 `mime_type`
- 当给出 `cortex://objects/{object_id}` 时，系统自动解析对象元数据并转换为引擎可消费的受控来源
- 公开 API 不要求调用方理解内部 `profile_ref`、`fallback_policy`、`engine_options`
- 引擎最优配置由平台根据 `engine_id + scene` 自动装配

### FR-2 Parse 输出

系统必须输出：

- Markdown 正文
- 标题、原始 URL、最终 URL、语言、格式、分类标签
- 标准化、结构化元数据对象
- 实际命中的解析引擎、scene、内部 profile 与 fallback 轨迹
- 产物引用（HTML、Markdown、截图、PDF、SSL 摘要）
- 诊断信息（时延、代理使用、反机器人策略）

### FR-2A Parse 引擎可插拔

系统必须以内置注册表或适配器机制支持多种解析引擎，并允许：

- 显式指定公开 `engine_id`
- 通过公开 `scene` 选择高层场景配置
- 由内部编译器自动映射到 `profile_ref`
- 按模板自动路由
- 引擎失败后按策略回退
- 将不同引擎输出归一为统一 Markdown 和标准化元数据

### FR-3 Storage 上传

系统必须先落元数据，再返回上传凭据，完成后才能进入可下载状态。

同时，系统应提供面向 Swagger UI、本地测试和小文件的 `POST /v1/storage/files`
便捷接口。该接口必须有明确大小上限，并复用同一套对象元数据、版本、权限和审计模型；
它不能替代生产大文件、批量上传、断点续传场景下的预签名上传会话。

### FR-4 Storage 下载

系统必须支持短期有效的下载地址生成，并可按 `inline / attachment` 控制 disposition。

### FR-5 Add

系统必须能 ingest：

- 已上传对象
- 已解析文档
- 原始文本
- 外部 URI

### FR-6 Cognify

系统必须支持：

- 增量处理
- chunk 策略
- graph prompt profile
- 作业化运行

### FR-7 Memify

系统必须支持至少四种内建 enrichment 管线：

- coding rules
- triplet embeddings
- session persistence
- entity consolidation

### FR-8 Search

系统必须支持：

- 语义检索
- 图检索
- 混合检索
- session 上下文
- provenance 返回

### FR-9 作业治理

系统必须提供：

- 查询作业状态
- 获取作业事件
- 取消作业
- webhook 回调

### FR-10 权限控制与审计

系统必须提供：

- 基于 scope 的功能权限控制
- 基于租户、角色绑定、资源策略和属性条件的数据权限控制
- 默认拒绝的跨租户访问策略
- 细粒度到 object / document / dataset / job 的资源授权
- 搜索结果级过滤，避免命中返回绕过权限
- 下载 URL 生成前的资源授权校验
- 授权决策审计，包括 actor、resource、reason_code、trace_id

## 7. 非功能需求

### NFR-1 厂商中立

- 对象存储仅依赖 S3 兼容接口。
- 关系库只使用可迁移的 SQL 子集。
- 向量库和图数据库通过适配器注入。
- 解析器通过插件 / adapter 契约接入。
- API 不暴露供应商特有字段作为主契约。

### NFR-2 性能

目标：

- 同步 Parse 在可控页面上 `P95 <= 10s`
- Search 在热路径上 `P95 <= 2s`
- 上传初始化接口 `P95 <= 500ms`

补充要求：

- 极简 Parse API 不因参数减少而牺牲性能，`Parse Request Compiler` 必须是常数级决策流程，除 `object_id` 解析为受控来源外不得引入额外外部网络跳转。
- `engine_id=crawl4ai, scene=deep_web` 等高保真模式允许更高时延，但必须能够平滑切换到异步作业路径。

### NFR-3 可用性

目标：

- 控制面高可用，单组件故障不导致全局不可用。
- Worker 可横向扩展，队列堆积可恢复。
- 所有长任务具备断点可见性。

### NFR-4 可靠性

- 幂等重试不产生重复对象或重复任务副作用。
- 作业失败后保留诊断与中间结果引用。
- 关键写路径具备一致性校验与补偿机制。

### NFR-5 可维护性

- Parse / Storage / Knowledge 共用统一资源命名。
- 文档、对象、数据集、作业的主语义稳定。
- 解析引擎切换不应破坏 Parse API 的主返回结构。
- 扩展新知识流水线不破坏现有 API。

### NFR-6 安全

- 凭据不明文入库。
- 下载默认最小权限、最短 TTL。
- 支持租户隔离与审计留痕。
- 权限模型应支持最小权限、职责分离与 deny-by-default。

### NFR-7 可观测性与发布治理

- 所有 API、异步任务和下游依赖调用均对齐 OpenTelemetry 标准。
- 统一支持 W3C Trace Context 与 `baggage`，保证跨 API、队列、Worker、Webhook 的链路可追踪。
- 默认可原生接入 Jaeger、Prometheus、Grafana，无需把业务代码绑定到特定厂商 SDK。
- 支持按环境、版本、部署环、实验桶观察错误率、时延、fallback 率和搜索命中率。
- 为蓝绿部署、金丝雀部署、A/B 测试提供可比较、可回滚、可审计的遥测基础。

## 8. 成功指标

### 北极星指标

- 进入 Cortex 后可被成功检索的内容占比

### 核心指标

- Parse 成功率
- 按解析引擎拆分的 Parse 成功率
- fallback 触发率
- 标准化元数据完整率
- Add / Cognify / Memify 成功率
- Search 有效命中率
- 内容进入数据集的端到端时延
- 下载成功率
- 重试后恢复成功率
- OpenTelemetry 链路覆盖率
- 可从错误响应定位到 trace 的比例
- 按发布环拆分的错误率 / P95 对比
- MTTR（平均修复时长）
- 授权拒绝误报率
- 关键资源越权访问事件数

## 9. 版本规划

### M1：基础能力闭环

- Parse Sync + Async
- Storage Upload / Download URL
- Dataset Create
- Add / Cognify / Search
- 通用 Job API
- 关系库与对象存储元数据闭环
- OpenTelemetry 基线埋点、`/metrics` 端点与标准 trace context 透传
- OAuth 2.0 / OIDC 认证接入与基础 scope 控制

### M2：高级抓取与增强知识

- 解析引擎注册表与 profile 模板
- Jina Reader / LlamaParse / MarkItDown / Docling 适配器
- Crawl4AI storage state
- stealth / undetected 策略分级
- PDF / Screenshot / SSL 产物
- Memify 内建管线
- Search session memory
- Jaeger / Prometheus / Grafana 预置 Dashboard 与引擎级观测面板
- 资源级 RBAC / ABAC 授权与权限审计

### M3：企业化治理

- 配额、限流、RBAC
- 数据保留与归档策略
- 多环境迁移工具
- 回放、评测、审计报表
- 金丝雀发布、蓝绿切换、A/B 实验观测与自动回滚门禁
- 策略引擎适配层与跨组织委托授权

## 10. 验收标准

### Parse 验收

- 同步 Parse 在 `sources + engine_id` 两参数下即可直接返回 Markdown 与标准元数据。
- 当调用方给出 `scene` 时，系统会自动命中对应内部 profile，而不是要求调用方理解 profile 细节。
- 给定公开网页 URL，可返回 Markdown 与元数据。
- 给定需要登录态的 URL，可通过 session 引用抓取成功。
- 给定复杂页面，可按配置返回 PDF / 截图 / SSL 摘要。
- 给定对象存储中的文件，可通过不同解析引擎输出统一 Markdown 与标准化元数据。
- 当首选引擎失败时，可依据 fallback policy 切换至备选引擎，并保留尝试轨迹。

### Storage 验收

- 上传任意文件后能生成对象记录。
- 通过 `POST /v1/storage/files` 上传小文件后能直接返回 `available` 对象记录。
- 下载 API 能返回可用的短期 URL。
- 哈希不匹配时拒绝完成上传。

### Cognee 验收

- Add 能 ingest 文档、对象和文本。
- Cognify 能构建 chunk、summary、graph、embedding。
- Memify 能运行至少一条内建 enrichment 管线。
- Search 能返回答案、上下文与可追溯引用。

### 平台验收

- 统一 Job API 可查询状态、事件与取消。
- 失败任务保留足够诊断信息。
- 全套接口与 schema 可在 SQLite / PostgreSQL + 任意 S3 兼容存储上工作。
- 任一 API 请求都可通过 `trace_id` 关联到 Jaeger 链路。
- Prometheus 可直接抓取或接收 Cortex 指标，Grafana 可同时查看指标与链路。
- 金丝雀 / 蓝绿 / A/B 流量可按部署环和实验桶拆分观察。
- 无 `parse:write`、`storage:write`、`knowledge:write` 等 scope 的调用无法执行对应写操作。
- 无对象 / 文档 / 数据集数据权限的调用，即使知道 ID 也无法读取、下载或搜索命中。

## 11. 风险与缓解

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| 目标站点强反爬 | Parse 成功率下降 | 分层启用 proxy / stealth / undetected，保留人工会话注入 |
| 单一解析引擎失效或质量波动 | Parse 链路不稳定 | 多引擎注册表 + profile 路由 + fallback policy |
| 大文件上传中断 | 对象状态不一致 | pending -> complete 双阶段提交 |
| 向量库或图库切换 | 知识链路中断 | 通过数据集和适配器隔离外部引擎 |
| 长任务堆积 | 延迟增大 | 队列限流、优先级、Worker 横向扩展 |
| JSON 扩展字段失控 | 维护困难 | 固定核心字段，JSON 仅承接扩展信息 |
| 遥测标签高基数失控 | Prometheus / Grafana 成本升高、查询变慢 | 对 URL、对象 key、用户输入做脱敏和维度白名单控制 |
| 权限配置漂移或角色膨胀 | 误授权、维护复杂度上升 | 固定 permission catalog、内置角色模板、周期性审计与策略回放 |

## 12. 结论

Cortex 的产品形态不是单一服务，而是一个稳定的 AI 数据基础设施入口。只要 URL、文件、文本和知识流水线都被纳入同一套对象模型，上层 Agent 和业务应用就能用统一方式接入、搜索、追溯和迁移。
