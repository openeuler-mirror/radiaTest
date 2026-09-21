<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: 配置删除与历史执行汇集

## 状态

active

## 目标

为流水线配置层补齐删除能力，并提供 per-config 历史执行页面作为"汇集"入口；全局执行列表 Tab 收敛为"近期执行" feed。解决"流水线多了之后找不到特定 config 的历史执行"的痛点。

## 范围和非目标

### 范围

- `DELETE /pipelines/configs/{id}`（硬删 + 有 executions 拒删 409）
- `DELETE /pipelines/executions/{id}`（删单条 execution）
- `DELETE /pipelines/configs/{id}/executions`（批量删该 config 所有 executions）
- `list_pipeline_executions` 加 `config_id` 过滤 + `limit` 参数
- 前端新页面 `/pipelines/configs/:id/executions` 单页上下结构
- 配置列表行加"历史"按钮跳转
- 全局"执行记录" Tab 改名"近期执行" + 限 20 条

### 非目标

- 软删除 / 归档（`deleted_at` / `archived` 字段，AGENTS.md 反对投机结构）
- 改 `pipeline_executions.config_id` FK 为 `ondelete=SET NULL`（保护历史 executions 在 config 删后仍可查）——历史 executions 失去 config 上下文价值有限
- 问题 5（测试模块模板按流水线划分 + Mugen suite 改名）

## 确认决策

见 [ADR 0011](../../adr/0011-pipeline-config-delete-and-execution-history.md)。

## 任务分解

### Task 1: 后端删除接口

- service.py 加 `PipelineConfigReferencedError` 错误类
- service.py 加 `delete_pipeline_config`、`delete_pipeline_execution`、`delete_pipeline_executions_by_config` 三个函数
- router.py 加 `DELETE /pipelines/configs/{id}`、`DELETE /pipelines/executions/{id}`、`DELETE /pipelines/configs/{id}/executions` 三个端点（admin only）
- 验证：`test_pipelines_api.py` 加测试覆盖 409/403/204/404

### Task 2: list_pipeline_executions 加过滤参数

- service.py `list_pipeline_executions` 加 `config_id: str | None = None` 和 `limit: int | None = None` 参数
- router.py `GET /pipelines/executions` 接受 query 参数
- 验证：`test_pipelines_api.py` 加测试覆盖 config_id 过滤和 limit 截断

### Task 3: 前端 API 客户端

- `api/core/pipelines.ts` 加 `deletePipelineConfigApi`、`deletePipelineExecutionApi`、`deletePipelineExecutionsByConfigApi`
- `getPipelineExecutionsApi` 接受可选 `config_id` / `limit` 参数

### Task 4: 前端 config-detail.vue 新页面

- 新建 `views/pipelines/config-detail.vue` 实现 L1 单页上下结构
- 上半：config 元信息卡片 + 操作按钮（触发/编辑/删 config）
- 下半：executions 表格按时间倒序分页 20/页 + 每行删 execution 按钮 + "全删 executions" 按钮
- 路由 `/pipelines/configs/:id/executions`

### Task 5: 前端 index.vue 改造

- 配置列表行加"历史"按钮跳到 config-detail.vue
- "执行记录" Tab 改名"近期执行"，调 API 时传 `limit=20`
- 路由 `router/routes/modules/pipelines.ts` 加 config-detail 路由

### Task 6: 全链路检查

- `./scripts/check.sh all`（后端 + 前端 typecheck/lint/vitest）

## 当前进度

- [x] Task 1: 后端删除接口（`PipelineConfigReferencedError` + `delete_pipeline_config` + `delete_pipeline_execution` + `delete_pipeline_executions_by_config` + 3 个 DELETE 路由 + 9 个 API 测试）
- [x] Task 2: `list_pipeline_executions` 加 `config_id` / `limit` 参数（GET /pipelines/executions 接受 query）
- [x] Task 3: 前端 API 客户端（`deletePipelineConfigApi` / `deletePipelineExecutionApi` / `deletePipelineExecutionsByConfigApi` + `getPipelineExecutionsApi` 加 `params`）
- [x] Task 4: 前端 `config-detail.vue` 新页面（L1 单页上下结构 + 触发弹窗 + 全删/单删 + 删 config）
- [x] Task 5: 前端 `index.vue` 改造（配置行加"历史"按钮跳转 + "执行记录" Tab 改名"近期执行" + `loadRuns` 传 `limit: 20`）+ 路由加 `config-detail`
- [x] Task 6: `./scripts/check.sh` 全检——后端 243 测试 + ruff + compileall 全过；前端 typecheck + lint + vitest（32 测试）全过

## 发现和未解决问题

- 无。问题 2 全部按 ADR 0011 落地。剩余问题 5（模板按类型划分 + Mugen suite 改名）待 grilling。
