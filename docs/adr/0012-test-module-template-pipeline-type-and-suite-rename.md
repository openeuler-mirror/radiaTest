<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0012：测试模块模板按类型划分与 `mugen_suite` 改名

## 状态

已接受(Accepted)。

## 背景

[ADR 0010](./0010-pipeline-type-registration-data-vs-code.md) 把流水线类型做成数据驱动后，direct_run 类型（release 等）在触发时由 `find_or_create_suite_template` 自动创建空脚本模板（`name=release-{suite}`）并复用 update 的模板模型。但这些自动创建的模板跟 update 的 5 个 seed 模板混在 `test_module_templates` 表里无区分，前端"测试模块模板" Tab 全部一起显示，用户列表被 `release-smoke` / `release-ltp` 等自动创建的条目污染。

同时 `TestModuleTemplate.mugen_suite` 字段名把 mugen 框架细节泄露进了通用模型——未来加非 mugen 框架时这个字段名不合适。

本 ADR 决定给 `TestModuleTemplate` 加 `pipeline_type` 字段用于 UI 按类型筛选，并把 `mugen_suite` 改名为框架无关的 `suite_name`。

## 决策

### 1. `TestModuleTemplate.pipeline_type` 字段

加 `pipeline_type` 列（String(64), nullable=False, default="update", 逻辑 FK 到 `pipeline_types.name`，不加物理 FK）。

- update 的 5 个 seed 模板 `pipeline_type="update"`。
- direct_run 自动创建的模板 `pipeline_type` 从 `config.pipeline_type` 动态写入（`_find_or_create_suite_template(db, suite, pipeline_type=config.pipeline_type)`）。
- 用户手动新增模板时选 `pipeline_type`。
- 前端按 `pipeline_type` segmented filter 划分模板列表。

### 2. `mugen_suite` → `suite_name`

字段名改成 `suite_name`，跟 `MugenCase.suite_name` 字段名对齐，框架无关。mugen 框架下 `suite_name` 解释为 mugen suite 名；未来非 mugen 框架的 executor 自己解释。

API JSON 字段也跟着改名（破坏性变更，但前端同步改，不破前端）。

### 3. 自动创建模板命名

`_find_or_create_suite_template` 创建模板时 `name=f"{pipeline_type}-{suite}"`（如 `release-smoke`）。对不同 direct_run 类型（如 `smoke` 类型）创建的模板命名为 `smoke-{suite}`，避免不同类型共享同名模板。

### 4. UI 形态

`index.vue` 的"测试模块模板" Tab 加 `templateTypeFilter` segmented control，跟配置 Tab 的 `configTypeFilter` 范式对称。默认选 "update"（用户最常用编辑对象）。后端 `list_module_templates` 加可选 `pipeline_type` 过滤参数。

不区分"自动创建"vs"用户手动新增"——所有模板平等可编辑。`find_or_create_suite_template` 复用现有模板，用户编辑过的模板在下次触发时保留（有用的能力：能给 `release-smoke` 加个 `pre_env_script`）。（release 此后改走单模板模型，见 [ADR 0039](0039-release-case-selection-and-kernel-variant.md)；per-suite 自动模板命名机制仍适用于其他 direct_run 类型。）

### 5. 权限

模板 CRUD 权限不变：list 任意登录用户可读；create/update `AdminUser` only。`pipeline_type` 字段所有用户可设。

## 考虑过的方案

- **direct_run 支持自定义模板（Use case B）**：让 direct_run 类型也支持用户管理的富模板（自定义 `pre_env_script` 等），覆盖自动创建的空模板。否决——direct_run 语义是"直接跑用例"，要"自定义脚本"应该走 update 类那种 A 类代码 strategy，或新建一个 A 类。direct_run 保持简单。
- **彻底隐藏 direct_run 模板（Use case C）**：UI 只显示 update 的模板。否决——隐藏后用户无法看到自动创建的 `release-*` 模板的存在，缺乏可观察性；且 `find_or_create_suite_template` 复用模板的能力（用户能编辑后保留）有真实价值。
- **`suite` 字段名**：简短但跟其他 `suite` 变量冲突风险高。否决。
- **`test_suite` 字段名**：更描述性但跟 `MugenCase.suite_name` 不一致。否决。
- **表格加 `pipeline_type` 列按类型分组**：无 filter。否决——视觉上"按类型划分"不如 segmented 清晰，且类型多了列表会拥挤。
- **每个 pipeline_type 一个子 Tab**：类型多了 Tab 拥挤。否决。

## 影响

- 后端 `modules/pipelines`：
  - `models.py` `TestModuleTemplate` 加 `pipeline_type` 列 + `mugen_suite` 改名 `suite_name`。
  - `seed.py` `DEFAULT_TEMPLATES` 加 `pipeline_type="update"` + 字段名改。
  - `direct_run.py` `_find_or_create_suite_template` 接 `pipeline_type` 参数；模板 name 改为 `{pipeline_type}-{suite}`；新建模板时设 `pipeline_type`。
  - `builder.py` `template.mugen_suite` → `template.suite_name`。
  - `service.py` `list_module_templates` 加 `pipeline_type` 过滤参数；`update_module_template` 字段名改。
  - `router.py` `GET /pipelines/module-templates` 接 `pipeline_type` query 参数。
  - `schemas.py` `TestModuleTemplateCreate/Read/Update` 字段名改。
- 数据库：Alembic 迁移 rename `mugen_suite` → `suite_name` + add `pipeline_type` 列 + 数据迁移（已有的 `release-*` 模板设 `pipeline_type="release"`，其他保持默认 `"update"`）。
- 前端 `apps/web-antd`：
  - `api/core/pipelines.ts` `TestModuleTemplateRecord` + `createModuleTemplateApi` payload 字段名改。
  - `views/pipelines/index.vue` 加 `templateTypeFilter` segmented + 字段名改 + `loadTemplates` 传 `pipeline_type` 参数。
  - `views/pipelines/detail.vue` `record.template.mugen_suite` → `suite_name`。
- 测试：`test_pipeline_execution.py` / `test_pipelines.py` / `test_pipelines_api.py` / `test_seed.py` 所有 `mugen_suite=` 改名。
- `CONTEXT.md`：补充"测试模块模板"按类型划分的说明。
- 不改 ADR 0032/0033/0010/0011——本 ADR 是模板层补充，不动通用化决策。
