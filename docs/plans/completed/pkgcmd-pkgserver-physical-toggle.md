<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: pkgcmd/pkgserver 可选物理机用例 + SKIPPED 语义清理

## 状态（2026-09-04 归档）

T1–T7 全部落地（提交 `912a4cf` + `063af18d` + 后续 [ADR 0037](../../adr/0037-runjob-stats-and-suite-header-display.md)），
`a788699` 之后 `./scripts/check.sh` 全量重跑通过（backend 495 passed / 1 skipped，docs/scripts/frontend EXIT=0），MR
审查记录以 main 侧 merge commit 为代理。2026-09-04 kimariyb 现场核对：pkgcmd 配置"使用物理机"flag 呈现生效，
DB 里 docker 分支跑过 8 条 `status='skipped'` 用例（对应 Goal 2 mugen-skip 语义保留）。NO_CASE/NOT_EXECUTED 分支
历史 3103 个 case_run 分布可反推。

## 目标

1. pkgcmd/pkgserver 配置加"是否执行物理机用例"开关（per-module flag，默认 true；总开关 UI 联动）。关掉 → 物理机用例**不执行但在前端可见、标 NOT_EXECUTED**。
2. 顺手清理既有"未执行却标 SKIPPED"的迷惑性：
   - no_case 包（pkgcmd 无用例的包）→ 新状态 `NO_CASE`（"未找到用例"）。
   - 64k 最新轮未转测 → 新状态 `NOT_EXECUTED`（"未执行"）。
   - mugen 自己 skip（mugen 跑了 mugen.sh 但用例内部跳）→ 留 `SKIPPED`（"跳过"）。

kernel（physical-only 模块）不受物理机开关影响。

## 决策（grilling 确认）

1. config 级、按模块（pkgcmd/pkgserver 各一个 flag）；kernel 不受影响。
2. per-module flag 是真相（`pkgcmd_physical_enabled`/`pkgserver_physical_enabled`，默认 true，向后兼容）；"总开关"是 UI 一键联动，无总 flag、无优先级。
3. 物理机禁用时：env_set 照建（可见）+ case_runs 标 NOT_EXECUTED、不建 node（无机）、execute_env_set 跳过。
4. 3 个清晰状态：`NO_CASE`（未找到用例，no_case 包）/ `NOT_EXECUTED`（未执行，物理禁用+64k 跳过）/ `SKIPPED`（跳过，mugen 自己 skip）。
5. 前端 + 后端一起做。

## 范围

- `TestCaseRunStatus` 加 `NO_CASE` + `NOT_EXECUTED`；`TestEnvSetStatus` 加 `NOT_EXECUTED`。
- builder：no_case 包 → `NO_CASE`（原 SKIPPED）；物理 flag off → 建 physical env_set（status NOT_EXECUTED）+ case_runs NOT_EXECUTED + 不建 node。
- 环境创建：64k 最新轮未转测 → 当前 EnvSet/Case 收敛为 `NOT_EXECUTED`（原 SKIPPED）；mugen 自己 skip → 留 `SKIPPED`。
- execution：execute_env_set 跳 NOT_EXECUTED env_set（无机、不跑 case）；case 循环跳 NO_CASE/NOT_EXECUTED/SKIPPED。
- worst-wins（compute_run_status/compute_execution_status）：NO_CASE/NOT_EXECUTED/SKIPPED 都中性（终态、不算失败）。
- service stat 计数：加 no_case + not_executed。
- 前端：status 显/筛选/统计卡带 NO_CASE + NOT_EXECUTED；configForm 加 per-module 物理 flag + 总开关联动 + save 写 config_data。

## 非目标

- 不改 kernel 模块（physical-only，不受物理机开关管）。
- 不改 64k 最新轮未转测的判定逻辑（只约束其结果标记为 `NOT_EXECUTED`）。
- 不改 mugen 自己 skip 的逻辑（留 SKIPPED）。
- 不改既有 config_data 其他字段。

## 任务

- [x] T1 backend enum：TestCaseRunStatus 加 NO_CASE + NOT_EXECUTED；TestEnvSetStatus 加 NOT_EXECUTED。
- [x] T2 backend builder（TDD）：no_case 包 → NO_CASE；物理 flag off → physical env_set NOT_EXECUTED + case_runs NOT_EXECUTED + 不建 node。
- [x] T3 backend 环境创建（TDD）：64k 最新轮未转测 → NOT_EXECUTED；mugen-skip 留 SKIPPED。
- [x] T4 backend execution（TDD）：execute_env_set 跳 NOT_EXECUTED env_set；case 循环跳 NO_CASE/NOT_EXECUTED/SKIPPED。
- [x] T5 backend worst-wins + stat（TDD）：NO_CASE/NOT_EXECUTED 中性；stat 计数加 no_case + not_executed。
- [x] T6 前端：status 显/筛选/统计卡（NO_CASE"未找到用例" + NOT_EXECUTED"未执行" + SKIPPED"跳过"）+ configForm per-module 物理 flag + 总开关联动 + save。typecheck。
- [x] T7 文档：spec/0003（pkgcmd/pkgserver 模块 + 状态语义）+ ADR 0037（状态语义决策）+ plan 进度。

## 验证命令与验收场景

- `./scripts/check.sh backend`（pytest + ruff）+ 前端 `pnpm typecheck`。
- TDD：每步 RED-GREEN。
- 验收：
  1. pkgcmd config 物理机 flag off → 触发 → physical env_set 可见（NOT_EXECUTED，无机）+ vm env_set 正常跑；no_case 包标 NO_CASE。
  2. 总开关取消 → pkgcmd+pkgserver 都只 vm。
  3. 64k 流水线最新轮未转测 → case_runs NOT_EXECUTED（不再 SKIPPED）。
  4. mugen 自己 skip 的用例 → SKIPPED（不变）。
  5. 前端 RunJob 详情：NO_CASE/NOT_EXECUTED/SKIPPED 三种标记区分清楚；统计卡 + 筛选带 NO_CASE/NOT_EXECUTED。

## 进度

- Clarify + grilling 完成（5 决策）。
- T1-T6 全部完成（commit 912a4cf）：enum + builder + mugen_runner + execution + stat + 前端。280 测试绿，ruff 绿，typecheck 绿。
- T7 文档已完成：Spec 0003 同步状态和物理机开关，ADR 0037 固化前端状态语义。
- 待补可追溯的全量检查、部署 dev 验收和 PR/MR 审查记录。
