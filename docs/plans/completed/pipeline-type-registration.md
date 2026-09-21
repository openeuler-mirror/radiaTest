<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: 流水线类型注册——数据驱动 vs 代码驱动

## 状态

active

## 目标

把"新增流水线类型"从代码路径改成数据路径：A 类（update，含复杂编排）保持代码 strategy；B 类（release 等直接跑用例）由 `pipeline_types` 表驱动，前端可增删。同时修复 `image_round` 默认空导致 VM 自动安装失败的潜在 bug。

## 范围和非目标

### 范围

- `pipeline_types` 表 + Alembic 迁移 + seed 两条系统类型（update / release）
- `DirectRunPipelineStrategy` + 修改 `registry.get_pipeline_strategy` 按 `strategy_kind` 分派
- `pipeline_types` CRUD API + `frameworks` 列表 API
- `PipelineTriggerRequest.image_round` 触发级覆盖
- 前端"流水线类型管理"页 + 配置表单下拉改用 API + 触发弹窗 image_round + 看板条件渲染

### 非目标

- `test_framework` 的前端 CRUD（保持代码注册）
- direct_run 类型的 case 级筛选（仅 suite 级）
- 问题 2（流水线删除 + 历史执行汇集）、问题 5（模块模板按类型划分 + mugen_suite 改名）

## 确认决策

见 [ADR 0010](../../adr/0010-pipeline-type-registration-data-vs-code.md)。

## 任务分解

### Task 1: 后端基础——`PipelineType` 模型 + 迁移 + seed

- 在 `models.py` 加 `PipelineType` 类
- 新建 Alembic 迁移 `20260721_0021_create_pipeline_types.py`
- 在 `seed.py` 加 `seed_pipeline_types(db)` 函数，seed `update` 和 `release` 两条
- 在 `cli.py` 或 startup hook 调用 `seed_pipeline_types`
- 验证：`test_seed.py` 加测试，断言 seed 创建两条 + 字段正确 + 幂等

### Task 2: DirectRunPipelineStrategy + registry 分派

- 新建 `pipeline_strategies/direct_run.py` 实现 `DirectRunPipelineStrategy`
- 修改 `registry.get_pipeline_strategy`：查 `pipeline_types.strategy_kind` 后 dispatch
- `DirectRunPipelineStrategy.plan_run_jobs`：为每个 `version × suite` 创建 RunJob（env_type 固定 `vm`）
- 复用 `find_or_create_suite_template` 按 `config_data.suites` 自动建模板
- 验证：`test_pipeline_execution.py` 加测试，触发 release 类型能正确产出 RunJob

### Task 3: pipeline_types CRUD API + frameworks API

- 在 `schemas.py` 加 `PipelineTypeCreate/Read/Update`
- 在 `service.py` 加 `list_pipeline_types`、`create_pipeline_type`、`delete_pipeline_type`、`list_frameworks`
- 在 `router.py` 加 `GET/POST/DELETE/PUT /pipelines/types` 和 `GET /pipelines/frameworks`
- `DELETE` 实现：`is_system=True` 返回 403；有 `pipeline_configs` 引用返回 409；无引用硬删
- 验证：`test_pipelines_api.py` 加 API 测试（含权限、409、403）

### Task 4: trigger 级 image_round 覆盖

- 在 `schemas.py` 的 `PipelineTriggerRequest` 加 `image_round: str | None = None`
- 在 `service.py` 的 `trigger_pipeline` 加 `image_round` 参数；构造 RunJob 前覆盖 `config.image_round`
- 验证：`test_pipelines.py` 加测试，trigger 传入 image_round 时覆盖 config 级

### Task 5: 前端流水线类型管理页

- 新建 `views/pipelines/types.vue` 实现 CRUD UI
- 在 `api/core/pipelines.ts` 加 `listPipelineTypes/createPipelineType/deletePipelineType/listFrameworks` 函数
- 在 `router/routes/modules/pipelines.ts` 加路由
- 修改 `index.vue` 配置创建表单：`pipeline_type` 下拉改用 `GET /pipelines/types`；`test_framework` 只读展示

### Task 6: 前端触发弹窗 image_round

- 修改 `index.vue` 触发部分：根据当前配置的 `pipeline_type` 查 `pipeline_types.strategy_kind`
- release 类型（`strategy_kind=direct_run`）触发弹窗加必填 `image_round` 输入
- update 类型不加点开 image_round 输入

### Task 7: 前端看板条件渲染

- 修改 `execution-detail.vue`：矩阵列名 update 用 `display_name`，direct_run 用 suite 名
- 修改 `run-job-detail.vue`：`strategy_kind=update_strategy` 显示模块脚本/exec_command；`direct_run` 隐藏
- 复用现有矩阵结构和下钻链路，不新建组件

### Task 8: 全链路检查

- `./scripts/check.sh all`
- 手动确认前端类型管理页可增删 release 之外的 direct_run 类型
- 手动确认 release 配置触发时 image_round 必填

## 当前进度

- [x] Task 1: PipelineType 模型 + Alembic 迁移 `20260721_0021` + seed `update`/`release`
- [x] Task 2: `DirectRunPipelineStrategy` + `registry.get_pipeline_strategy(db, type)` 按 `strategy_kind` 分派
- [x] Task 3: `pipeline_types` CRUD API（`GET/POST/DELETE`）+ `GET /pipelines/frameworks`
- [x] Task 4: `PipelineTriggerRequest.image_round` + `PipelineExecution.image_round` 列（迁移 `20260721_0022`）+ `trigger_pipeline` 覆盖 + builder 优先 `execution.image_round`
- [x] Task 5: 前端 `views/pipelines/types.vue` 类型管理页 + 路由 + API 客户端 + `index.vue` 配置表单下拉改用 API + `isDirectRunType()` 替代硬编码 `=== 'release'`
- [x] Task 6: 前端触发弹窗 release（`direct_run`）加必填 `image_round` 输入
- [x] Task 7: 前端看板条件渲染通过数据形状自然适配（`display_name` 字段差异），无需额外代码
- [x] Task 8: `./scripts/check.sh` 全检——后端 234 测试 + ruff + compileall 全过；前端 typecheck + lint + vitest（32 测试）全过；build 在远程 dev 环境跑

## 发现和未解决问题

- 无。问题 1 全部按 ADR 0010 落地。剩余问题 2（流水线删除+历史执行汇集）和问题 5（模板按类型划分+suite 改名）待 grilling。
