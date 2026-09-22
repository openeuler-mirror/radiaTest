<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0010：流水线类型注册——数据驱动 vs 代码驱动

## 状态

已接受(Accepted)。

## 背景

[ADR 0033](./0033-update-pipeline-execution-model.md) 决策 10 把流水线表/模型/API 去掉 `update_` 前缀并引入 `pipeline_type` 字段，但 `pipeline_type` 实际上仍是**代码注册**概念：`PIPELINE_STRATEGIES = {"update": UpdatePipelineStrategy()}` 硬编码在 `registry.py`，新增类型必须写 strategy 类 + 注册。前端 dropdown 里虽然有 `release` 选项，但后端 `get_pipeline_strategy("release")` 触发时抛 `ValueError`——release 在后端从未真正可用。

现需支持前端增删流水线类型（用户诉求：新增类型不应每次走开发路径）。但 update 类型的 strategy 包含真实领域逻辑（repodata 包匹配 + env_type_split 拆分 + no_case SKIPPED 占位 + 5 个 seed 模板），把这些塞进"数据驱动通用模板"会污染通用层。

同时存在两个相关的未决问题：

1. `PipelineConfig.dist` / `image_round` 当前都是顶层字段，但 `image_round` 默认空字符串对 VM 自动安装是**会失败的默认值**（`vms/schemas.py:46-47` 强制 auto install 必填）。
2. release 类型的 `image_round` 是"当前 RC 构建轮次"，每次触发都变——不应绑死在配置上。

## 决策

### 1. 类型驱动的 A/B 拆分

区分两类流水线类型：

- **A 类（代码驱动）**：含复杂编排逻辑（如 update 的模块矩阵 + repodata 包筛选 + env_type_split）。每个 A 类类型对应一个 `PipelineStrategy` 子类，注册在 `PIPELINE_STRATEGIES`。前端不能新增/删除 A 类。
- **B 类（数据驱动，"直接跑用例"）**：编排逻辑同构——选 framework → 选若干 suite → 每个 suite 顺序跑全部 case → 收集结果。所有 B 类共享一个 `DirectRunPipelineStrategy`，由 `pipeline_types` 表驱动。前端可增删 B 类。

### 2. `pipeline_types` 表

新增 `pipeline_types` 表：

| 字段 | 用途 |
|---|---|
| `id` | UUID PK |
| `name` | 唯一标识，如 `update` / `release`；`pipeline_configs.pipeline_type` 逻辑引用此字段 |
| `display_name` | 前端展示 |
| `strategy_kind` | 枚举：`update_strategy` \| `direct_run`；dispatch key，决定用哪个 strategy 类 |
| `test_framework` | 关联代码注册的 framework（如 `mugen`），不是 mugen_suite |
| `is_system` | `True` = seeded 系统类型，不可删；`False` = 用户创建，可删 |
| `default_config` | JSON，类型级默认值（如 direct_run 类型的 `default_suites`） |

`pipeline_configs.pipeline_type` 保持 String(64) 字符串字段，**逻辑 FK** 到 `pipeline_types.name`，不加物理 FK 约束——避免删 type 时 cascade 历史配置。`get_pipeline_strategy` 改成查 `pipeline_types.strategy_kind` 后 dispatch。

### 3. `test_framework` 保持代码注册

`FRAMEWORK_EXECUTORS` 继续硬编码在 `registry.py`。framework executor 包含真实部署/执行/解析代码（mugen 部署路径、`mugen.sh` 命令、`parse_mugen_results_dir` 解析器），不是用户填字段就能生成的。加新 framework 是开发行为，不是用户配置行为。

前端新建 pipeline_type 时，`test_framework` 字段是只读下拉，从后端 `GET /pipelines/frameworks` 接口拿（接口返回当前代码注册的 framework 列表）。

### 4. Seed 两条系统类型

- `update` (strategy_kind=update_strategy, framework=mugen, is_system=True) ← 替换前端硬编码的 update 选项
- `release` (strategy_kind=direct_run, framework=mugen, is_system=True) ← 替换前端硬编码的 release 选项，让它真正可触发

`is_system=True` 的类型由 seed 脚本管理，前端 DELETE 接口返回 403。

### 5. 删除策略：有引用拒删

用户创建的 B 类类型（`is_system=False`）可删，但 `DELETE /pipelines/types/{id}` 接口先查 `pipeline_configs` 是否有 `pipeline_type = this.name` 的记录，有则返回 409 Conflict + 引用数量。用户必须先清理所有该类型的 pipeline_configs 才能删 type。无引用时硬删。

### 6. 筛选用例粒度：suite 级

B 类（direct_run）类型的 pipeline_config 选 case 走 suite 级筛选：选 framework → 选若干 suite → 跑每个 suite 全部 case。沿用当前 release 模式（`config_data.suites = ["smoke", "ltp"]` + `find_or_create_suite_template`），扩展到所有 direct_run 类型。不做 case 级筛选（避免 `find_or_create_suite_template` 一套一模板爆炸或模板模型被 case 列表污染）。未来需要 case 级筛选时，在 `config_data` 加可选 `case_overrides: {suite_name: [case_names]}` 字段，默认全跑。（release 此后由 [ADR 0039](0039-release-case-selection-and-kernel-variant.md) 采纳了 case 级筛选，以 `config_data.case_selections = [{suite_name, case_names}]` 落地，取代此处预留的 `case_overrides` 设计。）

### 7. `dist` / `image_round` 双层归属

- `dist`：保留 `PipelineConfig` 顶层字段，默认 `openEuler`。所有类型共享，配置期间不变。
- `image_round`：**双层模型**。
  - `PipelineConfig.image_round`：配置级，用于 update 等配置期间基础镜像稳定的场景。
  - `PipelineTriggerRequest.image_round`（新增可选参数）：触发级覆盖，用于 release 等每次触发都换 RC 轮次的场景。触发时如果传了 trigger 级值，覆盖 config 级；否则用 config 级。
  - 前端 release 触发弹窗加必填 `image_round` 输入；update 触发弹窗不加（用 config 级值）。
  - 修复了"`image_round` 默认空字符串对 VM 自动安装是会失败的默认值"的潜在 bug——update 配置跑 VM 必须填 `image_round`；release 触发必须填 `image_round`。

### 8. 一套看板条件渲染

`execution-detail.vue` 和 `run-job-detail.vue` 不拆分，按 `strategy_kind` 条件渲染：

- 矩阵列分组：update 显示模块 `display_name`（如 "Docker Update Test"），direct_run 显示 suite 名（如 "smoke"）——只是标签差异。
- `run-job-detail.vue` 的"模块脚本"区域（pre_env_script / post_env_script / mugen_exec_command）只在 `strategy_kind=update_strategy` 显示，direct_run 隐藏。
- 矩阵形状（version × column × arch + 下钻 case + 子用例 + 日志）完全复用。

## 考虑过的方案

- **ALL 类型都数据驱动（含 update）**：要把 update 的 repodata / env_type_split / no_case SKIPPED 逻辑全部提成配置参数。工作量大，牺牲 update 的领域精确度。否决。
- **`test_framework` 也做成前端 CRUD**：会让用户能填名字 + 上传脚本"新建 framework"，催生半成品 framework 记录指向不存在的执行逻辑。framework executor 包含真实部署/执行/解析代码，不是数据驱动概念。否决。
- **`pipeline_configs.pipeline_type` 加物理 FK + ondelete**：会让删 type 时 cascade 历史配置，破坏历史记录可追溯性。逻辑 FK + 删除前检查引用更诚实。否决物理 FK。
- **筛选用例粒度 2/3（case 级筛选）**：会让 `config_data` 结构复杂化，跟 `find_or_create_suite_template` 的"一个 suite 一个模板"模式冲突。direct_run 语义是"跑某 suite 全部 case"，case 级筛选应走 update 那种模块模板 + case_filter 机制。否决。
- **软删除 type（加 `deleted_at` 字段）**：当前项目没有软删除范式，引入软删除会催生"已删除但历史 config 仍能引用"的混杂状态。强制清理引用更诚实。否决。
- **`image_round` 全挪到 trigger 级**：update 也每次触发都得传，UX 麻烦。配置级 + 触发级覆盖的双层模型更贴合实际语义。否决。
- **两套看板组件（update 独占一套，direct_run 共用一套）**：矩阵形状完全一致，只是字段展示与否的差别。两套组件会产生大量重复代码。否决。

## 影响

- 后端 `modules/pipelines`：
  - 新增 `PipelineType` 模型 + `pipeline_types` 表 + Alembic 迁移。
  - 新增 `DirectRunPipelineStrategy`（处理所有 `strategy_kind=direct_run` 类型）。
  - 修改 `registry.get_pipeline_strategy`：改成查 `pipeline_types.strategy_kind` 后 dispatch。
  - 新增 `GET /pipelines/types`、`POST /pipelines/types`、`DELETE /pipelines/types/{id}`、`GET /pipelines/frameworks` 接口。
  - 修改 `PipelineTriggerRequest` 加 `image_round: str | None` 字段；`trigger_pipeline` 把 trigger 级 `image_round` 覆盖到 config 级再构造 TestJob。
  - Seed 脚本加 `update` 和 `release` 两条 `pipeline_types` 记录。
- 前端 `views/pipelines/`：
  - 新增"流水线类型管理"页（CRUD UI，仅 `is_system=False` 可删）。（该前端页已被 [ADR 0045](0045-rc-version-management-package-compare.md) 移除，类型注册机制与后端 API 保留。）
  - 修改 `index.vue` 配置创建表单：`pipeline_type` 下拉从 `GET /pipelines/types` 拿；`test_framework` 字段只读展示。
  - 修改触发弹窗：release 类型加必填 `image_round` 输入。
  - `execution-detail.vue` / `run-job-detail.vue` 按 `strategy_kind` 条件渲染字段。
- `CONTEXT.md`：新增"测试流水线类型(Pipeline Type)"词条，明确数据驱动 B 类 vs 代码驱动 A 类的区分。
- 不改 spec 0003（产品行为另由 spec 变更承载，本 ADR 只记设计取舍）。
- 不改 ADR 0033 决策 10 的"release 等其他 pipeline_type 后续 additive 接入"——本 ADR 是其细化，把"additive"明确成"通过 `pipeline_types` 表数据驱动 additive"，而非"写代码加 strategy 类 additive"。
