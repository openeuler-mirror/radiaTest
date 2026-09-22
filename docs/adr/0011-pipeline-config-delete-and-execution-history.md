<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0011：流水线配置删除与历史执行汇集

## 状态

已接受(Accepted)。

## 背景

[ADR 0033](./0033-update-pipeline-execution-model.md) 决策 10 把流水线表/模型/API 通用化，[ADR 0010](./0010-pipeline-type-registration-data-vs-code.md) 把类型注册做成数据驱动。但配置层仍只有 create/update 接口，没有 delete；执行记录在全局 `/pipelines/executions` 列表里混在一起，配置多起来后用户找不到特定配置的历史执行结果。

本 ADR 决定配置删除策略、历史执行的浏览形态、全局执行列表 Tab 的语义收敛。

## 决策

### 1. 删除策略：硬删 + 有 executions 引用时 409

`DELETE /pipelines/configs/{id}` 接口先查 `pipeline_executions` 是否有 `config_id = this.id` 的引用，有则返回 409 + 引用数量；无引用时硬删（级联清掉该 config 的 executions/Runs/RunJobs，按既有 `ondelete=CASCADE` FK）。

不引入 `deleted_at` / `archived` 字段做软删除——AGENTS.md 反对投机结构；不软删的另一个原因是历史 executions 在没有对应 config 的情况下查询价值有限（`config_name` 兜底显示"已删除"会催生混杂状态）。

### 2. 删 execution 接口：单条 + 批量两个

为了清理引用以释放删除路径，提供：

- `DELETE /pipelines/executions/{id}` —— 删单个 execution（级联 runs/run_jobs）。
- `DELETE /pipelines/configs/{id}/executions` —— 批量删该 config 所有 executions。一次性事务，要么全成功要么回滚，避免前端循环调用中途失败留下半成品。

不采用 `DELETE /pipelines/configs/{id}?force=true` 隐藏批量语义——一个接口承担两种语义易误用。

### 3. 历史执行 UX：新页面 `/pipelines/configs/:id/executions`

配置列表每行加"历史"按钮，跳到新页面 `/pipelines/configs/:id/executions`。页面单页上下结构：

- 上半：config 元信息卡片（name / type / dist / image_round / versions / archs / framework / config_data 摘要）+ 操作按钮区（触发新执行 / 编辑配置 / 删除配置）。
- 下半：该 config 的 executions 表格（triggered_at / status / versions / archs / triggered_by / actions），按时间倒序，分页 20/页。

后端 `list_pipeline_executions` 加可选 `config_id` 过滤参数 + `limit` 参数。

### 4. 全局"执行记录" Tab 改名"近期执行" + 限 20 条

`index.vue` 现有"执行记录" Tab 是全局所有流水线的 executions 混在一起——这正是用户痛点。改名"近期执行"，只展示最新 20 条作为全局活动 feed；找特定 config 历史走 per-config 页面。

不彻底删掉该 Tab——"看最新动态"是真实需求，admin 早上扫一眼昨晚跑了啥。

### 5. 权限：admin only

`DELETE /pipelines/configs/{id}`、`DELETE /pipelines/executions/{id}`、`DELETE /pipelines/configs/{id}/executions` 都 `AdminUser` only，跟现有 `POST /configs`、`PUT /configs/{id}`、`POST /trigger`、`POST /executions/{id}/destroy-envs` 一致。

## 考虑过的方案

- **硬删 + SET NULL executions**：改 `pipeline_executions.config_id` FK 为 `ondelete=SET NULL`。删 config 后 executions 保留但 `config_id=NULL`，`execution_config_name` 兜底显示"已删除配置"。需要迁移改 FK + 兜底逻辑。否决——历史 executions 在没有 config 上下文的情况下查询价值有限，且增加一层混杂状态。
- **软删 / 归档**：加 `deleted_at` 字段。config 列表默认隐藏已归档。否决——投机结构，AGENTS.md 反对"为了体验更完整"加字段。用户真要"归档"可以改名加 `[ archived ]` 前缀 + 前端搜索过滤。
- **抽屉（Drawer）展示历史**：配置列表行加"历史"按钮 → 打开抽屉。否决——抽屉空间有限，长列表（一个 config 跑半年可能上百条 execution）体验差；不可分享 URL。
- **全局 Tab 加 config 筛选下拉**：用户选某 config 后列表过滤。否决——两步交互反人类，用户先去配置列表找 config 名，再回执行记录 Tab 选。
- **`DELETE /pipelines/configs/{id}?force=true` 批量删**：单个接口承担两种语义。否决——隐藏批量删的破坏性，易误用。
- **双 Tab 页（配置 + 历史执行）**：把 executions 藏到第二个 Tab。否决——用户痛点就是看 executions，多一次点击违背"汇集"语义。

## 影响

- 后端 `modules/pipelines`：
  - 新增 `delete_pipeline_config`、`delete_pipeline_execution`、`delete_pipeline_executions_by_config` 三个 service 函数。
  - `list_pipeline_executions` 加 `config_id: str | None` 和 `limit: int | None` 参数。
  - 新增 `DELETE /pipelines/configs/{id}`、`DELETE /pipelines/executions/{id}`、`DELETE /pipelines/configs/{id}/executions` 三个路由。
  - 新增 `PipelineTypeConflictError` 同款的 `PipelineConfigReferencedError` 错误类。
- 前端 `views/pipelines/`：
  - 新增 `config-detail.vue` 实现 L1 layout。
  - `index.vue` 配置列表行加"历史"按钮跳转；"执行记录" Tab 改名"近期执行"，限 20 条。
  - `api/core/pipelines.ts` 加 `deletePipelineConfigApi`、`deletePipelineExecutionApi`、`deletePipelineExecutionsByConfigApi`、`getPipelineExecutionsApi` 加 config_id/limit 参数。
- `CONTEXT.md`：补充"流水线配置删除"和"历史执行汇集"语义说明。
- 不改 ADR 0033/0010——本 ADR 是配置层补充，不动通用化决策。
