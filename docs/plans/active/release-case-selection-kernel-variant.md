<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: Release 流水线 — Case 级用例选择与内核变体

## 状态

active

## 目标

在现有 `release` 流水线类型（B 类 `direct_run`）上增加：case 级 mugen 用例选择、单版本+单轮次配置、可选内核变体（dailybuild select XOR 手动 RPM URL）应用于全部 VM、重设计的"已选"用例选择器、默认日志收集——且不干扰 `update` 流水线。

## 范围和非目标

### 范围

- `config_data.case_selections`（case 级选择）+ `kernel_variant`/`kernel_rpm_url` 透传
- 单版本+单轮次约束（release 专属），轮次归配置级，触发无参数
- builder `none` 分支对 direct_run 读选择；env_set `node_num`=max(选中 case node_num)
- `_find_or_create_release_template` 默认 `post_env_script`（日志拷贝）
- `test_jobs` 加 `pipeline_extras` JSONB（release 存 `kernel_variant`/`kernel_rpm_url`），`create_env_node_vm` 透传 `VMRequestCreate`
- release 配置创建弹窗：cascading + 多架构 + 内核变体 + 重设计 case 选择器
- 复用 update 风格执行/统计/日志页（§9.4，direct_run 隐藏模块脚本）

### 非目标

- release 物理机 RunJob / ISO-PXE 安装（后续扩展）
- release `-64k` os_version 后缀路径（release 用 `kernel_variant` 字段）
- 多版本矩阵（update 专属）
- 手动日志上传（自动收集）
- `test_framework` 前端 CRUD（保持代码注册）

## 确认决策

见 [ADR 0039](../../adr/0039-release-case-selection-and-kernel-variant.md)。关键取舍：

1. 扩展 release 类型本身，不新建子类型。
2. case 选择走 `config_data.case_selections`，复用 builder `none` 分支 + `select_cases(case_names=...)`。
3. 单版本+单轮次，轮次配置级，触发无参数。
4. 内核变体快照到 `TestJob`，`create_env_node_vm` 透传既有 `VMRequestCreate` → `apply_custom_kernel`。
5. 默认 `post_env_script` 收集日志，**不改** §4.8 共享自汇集（update 字节级不变）。
6. `node_num`/`env_set_num` 由选中 case 推导，不硬编码。

## 数据模型

### 扩展现有表

```text
test_jobs
  pipeline_extras  JSONB NULL  -- 类型专属执行参数；release 存 kernel_variant/kernel_rpm_url
```

不新增表。`config_data` JSON 增字段：`case_selections`（`[{suite_name, case_names}]`）、`kernel_variant`、`kernel_rpm_url`。类型专属字段走 `pipeline_extras` JSONB，不为每个流水线类型给共享 `test_jobs` 加实列（避免后续列膨胀）。

## 模块边界

### 改动后端

```text
backend/app/modules/pipelines/
  pipeline_strategies/direct_run.py  -- 单版本约束 + per-arch RunJob + 单 release 模板
  builder.py                         -- none 分支汇总全部 case_selections（跨 suite）；node_num=max(全部)
  service.py                         -- release config 校验（单版本/内核 XOR/case 选择）
  seed.py                            -- _find_or_create_release_template 默认 post_env_script
  schemas.py                         -- config_data 结构标注
backend/app/modules/test_management/
  envs/vm.py                         -- create_env_node_vm 透传 kernel_variant/kernel_rpm_url
  models.py                          -- TestJob 加 pipeline_extras JSONB（release 存 kernel_variant/kernel_rpm_url）
```

### 改动前端

```text
frontend/apps/web-antd/src/views/pipelines/
  config-form (release)  -- cascading + 多架构 + 内核变体 + 重设计 case 选择器
  (execution/run-job-detail 复用，direct_run 隐藏模块脚本)
```

## 任务分解

### Task 1: 数据模型和迁移

- `TestJob` 加 `pipeline_extras`（JSONB nullable）
- Alembic 迁移
- 验证：迁移 up/down 成功，列存在

### Task 2: DirectRunPipelineStrategy + builder（case 选择，mock VM）

- `plan_run_jobs` 约束单版本，按 arch 建 RunJob（每架构一套环境跑全部 suite）
- builder `none` 分支 direct_run 读 `config_data.case_selections` 传 `case_names`；把 `config_data.kernel_variant`/`kernel_rpm_url` 快照入 `TestJob.pipeline_extras`
- env_set `node_num`=max(选中 case node_num)，`env_set_num=1`
- `_find_or_create_release_template` 默认 `post_env_script`
- 验证：unit — RunJob/TestJob 形状、CaseRun 集合、node_num、post_env 非空、pipeline_extras 含内核参数

### Task 3: create_env_node_vm 内核变体透传

- `create_env_node_vm` 从 `job.pipeline_extras` 读 `kernel_variant`/`kernel_rpm_url`，透传 `VMRequestCreate`
- builder 把 release 内核参数快照入 `TestJob.pipeline_extras`
- 验证：unit — payload 带参数；update 的 `pipeline_extras` 为 NULL 透传 NULL

### Task 4: 配置校验 API + 用例端点

- release config 校验：单版本、`kernel_variant` XOR `kernel_rpm_url`、`case_selections` 引用真实 suite/case
- `GET /pipelines/mugen-suites` + cases 供选择器
- 验证：API tests

### Task 5: 前端配置弹窗 + 重设计选择器

- cascading dist→os_version→round→多架构 checkbox→内核变体(select XOR URL)→case 选择器
- 选择器：左 suite 浏览、右"已选"视图（选 suite 默认全选 case、可展开精细取消、可整 suite 移除）
- 验证：组件测试（选 suite→全选；取消单 case；移除整 suite）

### Task 6: 前端执行复用验证

- release RunJob 详情复用（direct_run 隐藏模块脚本 + case 列表 + 日志）
- 验证：build/lint

### Task 7: 检查与文档

- `./scripts/check.sh all`
- 非干扰断言：update 既有 pipeline 测试不变绿
- SPEC §9 / ADR 0039 / 本 plan 同步

## 验证命令

```bash
./scripts/check.sh all
```

## 当前进度

- [x] Task 1: 数据模型和迁移（`pipeline_extras` JSONB）
- [x] Task 2: DirectRunPipelineStrategy + builder（case 选择 + node_num=max + 默认 post_env + pipeline_extras 内核快照）
- [x] Task 3: create_env_node_vm 内核变体透传（读 `job.pipeline_extras` → `VMRequestCreate`）
- [x] Task 4: 配置校验 API（单版本/内核 XOR/未知 suite）+ mugen cases 复用既有 `/test-cases`
- [x] Task 5: 前端 release-config-form.vue + 重设计选择器（左 suite 浏览、右"已选"视图）+ release-config-view.ts/test.ts
- [x] Task 6: 前端 typecheck/lint/vitest(74)/build 全通过
- [x] Task 7: `./scripts/check.sh all` — 后端 450 passed / 1 skipped / 0 failed；前端全绿

## 发现和未解决问题

- 顺带修复 pre-existing：`tests/test_vms.py::test_apply_custom_kernel_variant_success` 硬编码 `vm_dailybuild_repo_root` 未 monkeypatch——补 `monkeypatch.setattr(get_settings(), "vm_dailybuild_repo_root", ...)` 固定 dailybuild root（`get_settings` 为 lru_cache 单例，非 frozen，属性 patch 安全且自动回退）。全后端套件现 448 passed / 1 skipped / 0 failed。

## 审计与对齐结果

- **Audit（独立只读 sub-agent）**：无 blocker/major；4 个 minor 已处置——(1) release 必须有 `case_selections`（新增校验+测试，防 kernel_variant 单独提交的静默 no-op）；(2) 既有 release 模板 post_env 不回填是有意为之（不覆盖用户编辑）；(3) plan 措辞改为 `pipeline_extras` JSONB；(4) 内核变体交集逻辑提取为纯函数 `intersectKernelVariants` 并补测。
- **非干扰验证**：builder `none` 分支 update 回退原默认；`create_env_node_vm` update 透传 NULL；update seed 模板不受 `_find_or_create_release_template` 影响；release 校验仅对 `pipeline_type=="release"` 生效。
- **Reconcile（neat-freak）**：Spec §9 line 24 stale `suites`→`case_selections` 已修；ADR 0039 + plan 措辞同步 `pipeline_extras`；Serena memory `test-pipeline/vm-hang-false-positive` 的"流水线配置 case 选择器（独立）"deferred 项已更新为"已实现 release 级"。

## 剩余 DoD 门（未在本会话完成）

- 代码审查（AGENTS.md：合入 main 前必须经过代码审查）。
- 提交/合入（禁止自行 commit；待用户显式指令）。
