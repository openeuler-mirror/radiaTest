<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0018：env_type=both 合并为单 RunJob + 动态 env_set + update_list 早展示 + suite 级折叠

日期: 2026-07-27

## 状态

已采纳。

## 背景

ADR 0015 将 env_type_split bool 改为 env_type(vm/physical/both)。但 both 模块在 update.py 里仍被拆成 2 个独立 RunJob(vm + physical)，导致总览矩阵 2 格、2 个 TestJob、2 套执行。用户要求：both 模块应为 1 个 RunJob，内部含 VM + 物理机 2 个 env_set 并行执行。

此外，update_list（待测包列表）应在任务启动后立即展示（不等 pre_env + self-collect），用例列表应按 suite 级折叠（不摊开），执行结果只展示 suite 级汇总。

## 决策

### 1. both → 1 RunJob，2 env_set 并行

update.py：env_type=both → 1 个 RunJob（env_type=null）。builder 建 1 个 TestJob，含最多 2 个 env_set（VM + physical），ThreadPoolExecutor 并行。总览矩阵 1 格。

不采用：2 个 RunJob（现状）——总览 2 格、用户看着混乱。

### 2. env_set 动态建（不写死 env_set_num）

builder 在 plan_cases 后按用例实际需求建 env_set：
- 有 vm_cases → 建 VM env_set，node_num = max(vm_cases 的 node_num)。
- 有 physical_cases → 建 physical env_set，node_num = max(physical_cases 的 node_num)。
- 没有 physical_cases → 不建 physical env_set（不浪费物理机）。
- no_case_packages → `NO_CASE` case_run，挂在第一个 env_set（ADR 0037 取代了早期的 `SKIPPED` 标记）。

模板的 env_set_num 不再用于 both 模块（动态决定）。vm/physical 模块仍用 env_set_num。

### 3. TestEnvSet 加 env_type 字段

execute_env_set 改为看 env_set.env_type（不是 job.env_type）决定 create_env_node_vm / physical。

### 4. update_list 早展示

builder 的 packages（fetch_update_packages 已有）存到 TestJob.update_packages（JSON list）→ API 立刻返回 → 前端任务启动后第一个展示。去掉 PKGCMD_PRE_ENV 里的 dnf list（builder 的列表够用）。

### 5. 用例列表 suite 级折叠

> **已变更（ADR 0021）**：pkgcmd 模块右栏已隐藏，"执行结果只展示 suite 级汇总"不再适用于 pkgcmd。用例列表 suite 折叠保留。

前端 case list 按 suite_name 分组，默认折叠。suite 行显示：名 + 状态色 + ✓N ✗N。副标题标环境（全 VM→"VM"、全 physical→"物理机"、混合→"VM + 物理机"）。点 suite 展开 case。执行结果只展示 suite 级汇总。

## 影响

- `TestEnvSet` 加 `env_type`(str, nullable) + 迁移。
- `TestJob` 加 `update_packages`(JSON list) + 迁移。
- update.py：both → 1 RunJob(env_type=null)。
- builder：plan_cases 后动态建 env_set + 存 update_packages。
- execution.py：execute_env_set 看 env_set.env_type。
- service.py：RunJob detail API 返回 update_packages。
- run-job-detail.vue：update_list 先展示 + suite 折叠 + 环境副标题。
- PKGCMD_PRE_ENV：去掉 dnf list（update_list 由 builder 提供）。
- spec 0003 + CONTEXT 同步。
