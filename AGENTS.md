<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# AGENTS.md

## 项目规则

本目录包含 radiaTest 测试资源管理平台。

在本项目工作的 AI Agent 必须：

- 开发前阅读 `CONTRIBUTING.md` 并遵循完整分支生命周期；本次任务交付到已授权范围，后续阶段保留，不提前执行或免除。
- 先从代码、文档和测试查证，常规细节按现有约定处理；仅对无法查证且影响范围、安全、兼容性或验收的事项澄清。必要假设须说明，明确审批要求不变。
- `AGENTS.md` 补充分支生命周期；两份文档无法同时满足时，说明冲突并由用户裁决，仅暂停依赖该裁决的工作。
- 只在当前 radiaTest Git 仓库内新增或修改项目代码。
- 除非用户明确要求，当前仓库之外的兄弟目录视为不相关目录。
- 应用、PostgreSQL 和浏览器联调只在远程 Linux `dev`/`prod` 环境运行；开发工作站只用于编辑、检查、提交并推送到 GitCode，部署命令在 radiaTest 服务器本机执行。
- 前端权限检查只用于用户体验；后端鉴权(Authorization)才是最终边界。
- 前端页面不使用任何 emoji 或装饰性 Unicode 符号(如 ✓ ✗ ⚠ ⏭)；状态和计数用文字标签或图标组件表达。
- 文档按产品事实和稳定约定编写，不使用版本序号式过程术语；需要表达范围时写“支持”“不支持”或“可扩展为”。
- 重要架构、安全或领域决策必须写入 ADR(Architecture Decision Record)。
- 代码与 ADR/Spec 冲突时，说明冲突并由用户确认依据；确认前暂停相关修改，不反向改写 ADR/Spec。
- 分支合入 main 前必须经过代码审查；审查未通过不得合入，审查记录写在合入 main 的 merge commit message 中。向上游提交 PR 时，审查记录写在 PR 描述中。审查完成时由 Agent 准备好完整的 merge commit message 草稿，经授权合入时直接使用，不事后补写。
- 禁止自行执行 `git commit`、`git push`、`git tag` 或发布部署；必须有用户显式指令。
- 本任务内，目标、操作、环境和范围未变且授权未撤回时，不重复确认。方案确认不替代提交、推送、合入、打标签或部署授权；工具审批照常执行。

## 上游 PR 同步

- 用户要求准备上游 PR 时，使用 `pr/without-kimariyb-files` 分支；main 本地合入完成并推送后，按授权运行 `./scripts/sync-pr-branch.sh`，再由用户自行推送并在浏览器中创建 PR，Agent 不代为创建 PR 或合并请求。
- 同步脚本会重置 PR 分支、删除 fork 专属文件并创建提交；运行授权须覆盖这些操作。
- fork 专属文件以脚本的 `EXCLUDE` 为准，新增时更新清单，不提交进 PR 分支；无需用户重复提供清单。

## 文档责任边界

- `README.md`：只写项目入口、运行方式和文档索引。
- `docs/plans/`：`active/` 写经 Grill 确认的高影响实现的范围、明确不做事项、实施步骤和验证标准，完成并本地合入 `main` 后即可移入 `completed/`，不要求等待推送；计划不替代 `docs/spec/` 的产品定义或 `docs/adr/` 的架构取舍。
- `docs/spec/`：写产品行为、页面、API、权限和验收标准。
- `docs/adr/`：写重要设计取舍和不采用方案，不重复 Spec 的字段级或页面级细节。
- `CONTEXT.md`：写领域语言和当前核心规则，避免成为完整规格副本。

## Skills 使用约定

- 按任务类型使用下表中的 Skills；首次使用前读取对应 `SKILL.md`，并向用户说明，不在每次任务中加载全部 Skills。
- 用户明确指令及本项目规则优先于通用 Skill 建议。Skills 不改变分支生命周期、提交与部署授权、远程联调边界、TDD 要求和最终 diff 审查约定，不额外增设确认步骤。
- `grill-me` 是 `grilling` 的兼容入口；需要 Grill 时调用 `grill-me` 或直接使用 `grilling`，两者执行同一需求对齐流程。两者均不可用时，按下文阻塞规则处理。
- 除 Grill 特例外，Skill 不可用时直接按表中“使用要求”执行，无需额外确认；不得虚构 Skill 或其文件。
- 因 Skill 暂停时，引用具体文件和条款，说明缺少的信息或授权。

| 触发场景 | Skill | 使用要求 |
| --- | --- | --- |
| 下文要求先 Grill 的改动 | `grill-me` / `grilling` | 编码前收敛范围、非目标和验收标准，并取得用户对方案的确认。 |
| 编写或修改业务代码 | `ponytail`、`test-driven-development` | 先确定最小改动边界，再按失败测试、最小实现、重构的顺序推进。 |
| 需要多 agent 或子代理并行协同的复杂任务 | `subagent-driven-development` | 先拆分为可独立验证的子任务，按依赖关系分波次派发；并行只用于互相独立的子任务；结果回收后由主线程统一整合与验证。 |
| 构建、修改或审查 Python/FastAPI 后端应用，或设计评审 REST API 端点 | `python-patterns`、`backend-patterns`、`fastapi-patterns` | Python 惯用法、类型标注和 PEP 8 以 `python-patterns` 为准；FastAPI 实现细节以 `fastapi-patterns` 为准(Pydantic v2 schema、依赖注入、事务型 Service 层，httpx 和 pytest 测试)；`backend-patterns` 面向 Node.js/Express，只取与框架无关的通用后端模式，冲突时以本项目 FastAPI 技术栈为准；REST API 的资源命名、状态码、分页、过滤和错误响应保持一致，产品行为以 `docs/spec/` 为准。 |
| Vue/TypeScript 前端组件、状态、路由改动及页面视觉交互设计 | `frontend-patterns`、`vue-best-practices`、`frontend-design` | 组件与状态组织只取与框架无关的通用模式；Vue 实现以 `vue-best-practices` 为准，遵循现有 Vben/Ant Design Vue 组件体系和类型约定；`frontend-patterns` 面向 React/Next.js，冲突时以本项目 Vue 技术栈为准；视觉与交互设计先用 `frontend-design` 做设计计划(配色、字体、布局、原则)，规避模板化默认样式，不因设计引入新依赖。 |
| 故障、测试失败或行为异常 | `systematic-debugging` | 先复现、收集证据并定位根因；仅排查则报告，已要求修复则按适用审批与 TDD 流程完成实现、验证和最终 diff 审查。 |
| PostgreSQL 表结构、迁移、查询、索引或锁问题 | `supabase-postgres-best-practices`、`database-migrations` | 数据库设计与查询使用适合现有 PostgreSQL 和 SQLAlchemy 架构的规则；schema 或数据迁移每次是独立迁移，DDL 与 DML 分离，生产只前进不回退；数据库验证遵循远程环境约定。 |
| 设计错误类型、重试、熔断或用户可见的失败提示 | `error-handling` | 使用类型化错误，不静默吞错；用户消息与开发日志分离。 |
| 涉及 Redis 的队列、锁、限流或发布订阅设计 | `redis-patterns` | 保持 Redis 只承担 Celery 队列和结果后端的定位，不借 skill 建议扩展缓存等新用途。 |
| 创建或评审 Dockerfile、Compose 服务与容器网络 | `docker-patterns` | 使用多阶段构建、最小镜像和明确的网络与卷配置。 |
| 出现重要架构取舍或被要求记录决策 | `architecture-decision-records` | 按项目 ADR 流程写入 `docs/adr/`，记录背景、备选方案和不采用理由。 |
| 改动完成后的最终审查或设计缺陷检查 | `requesting-code-review`、`code-review-checklist` | 审查最终 diff，修复后只复核相关项；按正确性、安全、设计、测试、可读性的优先级审查，重点识别耦合度、接口边界等设计缺陷；问题按阻塞、应修、建议分级。 |
| 声明实现完成、修复有效或检查通过前 | `verification-before-completion` | 以当前改动对应的实际验证结果为依据，明确通过项、未执行项及环境限制。 |
| 用户要求寻找或安装技能 | `find-skills`、`skill-installer` | 分别用于检索筛选和安装；安装操作需有用户授权。 |

## 需求对齐和 Grill 原则

为了保持简单优先，Agent 在改动前按以下规则判断是否需要先 grill：

- 小范围 bug 修复、文案修正、格式修正和明确的单点实现，可以先说明改动边界和不做事项，再直接修改；命中下条场景时仍须 Grill。
- 涉及数据模型、跨模块边界、权限规则、异步任务、迁移、部署脚本、外部依赖、后台自动化、交互流程、批量操作或 ADR/Spec 变化时，必须先调用 `grill-me` 或 `grilling` skill 对齐方案，再编码；两者均不可调用时，必须说明阻塞原因并等待用户决定，不得以自行分析替代。
- Grill 确认后，必须先在 `docs/plans/active/` 新建计划文档，再编写业务代码；计划内容以文档责任边界为准。
- 沿用本任务经 Grill 确认的方案和计划，仅对实质变更重新确认；只读排查和方案准备不受编码前确认限制。
- 未请求的增强先说明动机、收益、成本和替代方案，经用户确认后实施；仅暂停该增强，不阻塞原任务。
- 不得因为“体验更完整”而默认新增轮询、通知、缓存、定时器、后台 worker、新 API、新表字段或新依赖；能通过用户触发的读取、刷新或既有操作顺手收敛状态时，优先选择懒释放(Lazy Release)类设计，只有确实需要主动时效性时才考虑轮询、定时器或后台任务。
- Grill 目标是收敛方案，不是扩大范围；优先确认“做什么”和“明确不做什么”。

## 代码探索

radiaTest 由 Vue/TypeScript、Python 和 Shell 组成，本节约定探索源码的工具选择。

- 源码优先使用已索引且可用的 CodeGraph，其次使用已激活的 Serena；均不可用时用 `rg`、`sed` 和精确路径读取，不自动建索引。
- 符号工具可用时，大型源码先看概览再定向读取；使用 Serena 时用 `find_symbol` 定位。
- 修改公开 API、服务接口、仓储方法、组件 props 或跨模块调用前查引用；使用 Serena 时用 `find_referencing_symbols`。
- Shell 脚本、Compose/nginx/Dockerfile、配置、迁移脚本、文档、样例数据、日志和动态命令拼接，优先用 `rg` 与小范围文件阅读。
- CodeGraph 查询必须包含具体文件、符号或调用链；已知目标文件时不得进行宽泛探索。
- 子代理只接收完成任务所需的需求摘要、文件列表和固定比较点，不复制完整对话历史。

## 代码规范

- 公开服务、跨模块接口、异步任务入口，以及权限、幂等、并发、状态转换或临时兼容等非直观逻辑必须有注释；简单私有函数不强制添加注释。
- 命名、类型和函数边界应优先表达意图；Python 使用类型标注，TypeScript 不使用 `any` 规避类型设计。
- 注释遵循 Google 风格：Python 使用 Google-style docstring，TypeScript 使用 JSDoc/TSDoc。注释说明职责、业务原因和不可破坏的约束，不逐行复述实现。
- 函数保持单一职责；Router 只处理请求解析、鉴权入口和响应转换，业务规则放在 Service 或 Domain Module，Repository 只负责持久化读写。
- 模块只能通过公开的 Service、DTO、事件或明确接口协作；不得跨模块直接访问内部 Repository、ORM Model、Worker 实现或私有函数。
- 涉及重试、重跑或重新计算时，必须保留原始执行事实并建立来源关联，不得覆盖历史结果；具体产品语义以 Spec 为准。
- 改动完成后清理由本次改动产生的未使用代码和导入。

## 检查和测试输出

- 输出保持简洁，优先保留命令、首个失败、失败用例名、关键堆栈和变更文件。
- 项目检查入口仍是 `./scripts/check.sh`；不要为了使用其他工具绕过项目既有检查入口。
- 实现期间先运行定向测试、格式化、lint 和类型检查；改动稳定后运行 `./scripts/check.sh`。同一状态不重复完整检查；相关修复或改动使结果失效时重新验证，完整检查须覆盖最终改动。
- 无关基线问题阻断时，记录首个失败并运行受影响模块检查，不重复完整检查；不得报告为完整检查通过。
- 本地直接运行 `uv` 时必须设置仓库外可写缓存，例如 `UV_CACHE_DIR="${TMPDIR:-/tmp}/kronos-uv-cache"`（`./scripts/check.sh` 已设置该缓存，故优先使用它）。
- 本地 `uv sync`/`uv run` 若卡在 "Downloading ..." 不前进（默认 pypi 文件 CDN 在本网不可达），设 `UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/` 走阿里云镜像再试；不写入项目配置，仅作本次会话环境变量。
- 噪声较大的命令在 RTK 可用时可以用 RTK 包裹，例如 `rtk git status`、`rtk git diff --stat`、`rtk pytest`。
- RTK 不可用时直接运行原命令，并用更窄的检查范围控制输出。

## 完成定义(DoD)

交付时分别说明实现、验证、审查及合入状态；未满足 DoD 时列明待办，不宣称全部完成，不因后续阶段待授权而中止已授权工作。

功能或修复被判定为“完成”前，以下条件必须全部满足：

- 每个新增或修改的关键行为至少有一个测试先失败再通过；同一行为的补充断言和入口覆盖不要求分别观察失败。
- `./scripts/check.sh` 已通过，且通过后未发生需要重新验证的相关改动；无新增未使用代码和导入。
- 按 Grill 规则需要建立计划的改动，已在 `docs/plans/active/` 新建计划并完成。
- 架构、安全或领域取舍已写入 ADR；产品行为、API、权限或验收标准变更已同步到 Spec。
- 已通过代码审查，审查记录写在合入 main 的 merge commit message 中。

## 包管理器(Package Manager)

前端：

- Vben Admin 使用 pnpm。
- 不要在同一个前端目录混用 npm、yarn、bun 和 pnpm。
- 提交 `pnpm-lock.yaml`。
- 不提交 `package-lock.json`、`yarn.lock` 或 `bun.lock`。

后端：

- 使用 uv。
- 提交 `uv.lock`。

## 安全红线

- 不得把真实敏感信息(Secret)写入已跟踪文件、文档、测试、快照、日志或示例；`.env.example` 只能包含变量名和占位值，真实本地敏感信息放在 `.env` 或部署环境变量中。
- 不要向外部服务提交真实密码、私钥、令牌(Token)、API Key、机器凭据或未脱敏内网信息。
- 应用中的凭据(Credential)必须使用应用层加密(Application-Layer Encryption)保存。
- 凭据查看接口必须执行后端鉴权，但不记录查看行为；凭据修改必须写入审计日志(Audit Log)。
