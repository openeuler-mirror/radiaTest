<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: 测试模块模板按类型划分 + Mugen suite 改名

## 状态

active

## 目标

给 `TestModuleTemplate` 加 `pipeline_type` 字段用于 UI 按类型筛选/分组；把 `mugen_suite` 字段改名为 `suite_name`（跟 `MugenCase.suite_name` 对齐，框架无关）。

## 范围和非目标

### 范围

- `TestModuleTemplate` 加 `pipeline_type` 列（迁移 + 数据回填）
- `mugen_suite` → `suite_name`（迁移 rename column + 后端 + 前端 + 测试全改）
- `_find_or_create_suite_template` 接 `pipeline_type` 参数；模板 name 改为 `{pipeline_type}-{suite}`
- `list_module_templates` 加 `pipeline_type` 过滤参数
- 前端"测试模块模板" Tab 加 `templateTypeFilter` segmented control

### 非目标

- direct_run 类型支持用户管理的富模板（自定义 pre_env_script 等）——保持 direct_run 简单，要"自定义脚本"走 A 类代码 strategy
- 彻底隐藏 direct_run 模板——保留可观察性
- 其他改名（`list_mugen_suites` / `MugenCase.suite_name` 不动——前者是 mugen-specific API，后者已经叫 `suite_name`）

## 确认决策

见 [ADR 0012](../../adr/0012-test-module-template-pipeline-type-and-suite-rename.md)。

## 任务分解

### Task 1: 后端模型 + 迁移

- `models.py` `TestModuleTemplate` 加 `pipeline_type` 列 + `mugen_suite` → `suite_name`
- Alembic 迁移：rename column + add column + 数据回填（已有 `release-*` 模板设 `pipeline_type="release"`，其他默认 `"update"`）
- `seed.py` `DEFAULT_TEMPLATES` 加 `pipeline_type="update"` + 字段名改

### Task 2: 后端 service + builder + direct_run + router + schemas

- `direct_run.py` `_find_or_create_suite_template(db, suite, pipeline_type)` 改签名；模板 name 改为 `{pipeline_type}-{suite}`；新建模板时设 `pipeline_type`
- `builder.py` `template.mugen_suite` → `template.suite_name`
- `service.py` `list_module_templates` 加 `pipeline_type` 过滤参数；`update_module_template` 字段名改
- `router.py` `GET /pipelines/module-templates` 接 `pipeline_type` query 参数
- `schemas.py` `TestModuleTemplateCreate/Read/Update` 字段名改

### Task 3: 后端测试更新

- `test_pipeline_execution.py` / `test_pipelines.py` / `test_pipelines_api.py` / `test_seed.py` 所有 `mugen_suite=` 改名
- 加 `list_module_templates(pipeline_type=...)` 过滤测试
- 加 `_find_or_create_suite_template` 设置 `pipeline_type` 测试

### Task 4: 前端字段名改

- `api/core/pipelines.ts` `TestModuleTemplateRecord.mugen_suite` → `suite_name`；`createModuleTemplateApi` payload 字段改
- `views/pipelines/index.vue` form 字段名 + 表格列名 + 模板列表显示
- `views/pipelines/detail.vue` `record.template.mugen_suite` → `suite_name`

### Task 5: 前端 segmented filter

- `index.vue` 加 `templateTypeFilter` segmented control（跟 `configTypeFilter` 对称）
- `loadTemplates` 传 `pipeline_type` 参数
- 默认选 "update"

### Task 6: 全链路检查

- `./scripts/check.sh all`（后端 + 前端 typecheck/lint/vitest）

## 当前进度

- [x] Task 1: 后端模型 + 迁移 `20260721_0023`（rename `mugen_suite` → `suite_name` + add `pipeline_type` 列 + 数据回填 `release-*` 模板）+ seed 更新
- [x] Task 2: 后端 service/builder/direct_run/router/schemas 全改名 + `list_module_templates` 加 `pipeline_type` 过滤参数 + `_find_or_create_suite_template(db, suite, pipeline_type)` 签名 + `GET /pipelines/module-templates` 接 query
- [x] Task 3: 后端测试更新（244 测试全过）+ 加 `list_module_templates(pipeline_type=...)` 过滤测试 + `find_or_create_suite_template` 设置 `pipeline_type` 测试
- [x] Task 4: 前端字段名改（`pipelines.ts` / `index.vue` / `detail.vue` 全 `mugen_suite` → `suite_name`；`TestModuleTemplateRecord` 加 `pipeline_type` 字段；`createModuleTemplateApi` payload 加 `pipeline_type`）
- [x] Task 5: 前端 segmented filter（`templateTypeFilter` + `templateTypeOptions` + `loadTemplates` 传 `pipeline_type` + 模板 Tab UI 加 Segmented）
- [x] Task 6: `./scripts/check.sh` 全检——后端 244 测试 + ruff + compileall 全过；前端 typecheck + lint + vitest（32 测试）全过

## 发现和未解决问题

- 无。问题 5 全部按 ADR 0012 落地。所有 5 个问题已闭环。
