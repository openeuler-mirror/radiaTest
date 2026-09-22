<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0037：run-job 统计与用例列表展示语义细化

日期: 2026-08-29

## 状态

已采纳（2026-09-04 对账确认）。本 ADR 描述的前端展示语义已实现并已同步到 Spec 0003。
2026-09-07 修正：`执行中 a/x` 的 `a` 由通过数改为已出结果数（失败/超时/异常/跳过计入，只排除 pending/running/not_executed/no_case）；`总计` 明确排除 `no_case` 包，保证与各状态计数求和一致。

## 背景

run-job 详情页与执行矩阵的统计/用例列表展示存在 5 个语义问题。**纯前端问题**——后端数据已齐：执行摘要与 run-job 详情的 `counts` 含 `not_executed`/`no_case` 桶，`case_run.suite_name` 对 pkgcmd 即包名（`plan_cases` 按 `suite_name == 包名` 查 mugen 用例），`result_parser` 可识别 pkgcmd。

1. 用例未执行时，用例列表分组头（suite 级）清一色显示"跳过 0/x"——`groupedCases` 的 switch 漏计 `pending`/`running`，各计数为 0，标签 ternary 落到 else 默认"跳过"；展开后 case 行才显示"等待"。误导首屏，且统计卡/执行矩阵不渲染 `not_executed` → 未执行项统计恒 0。
2. pkgcmd 未找到用例的包（`no_case`，`suite_name=包名`）按 suite 分组、套"跳过 0/1"头，展开才见"未找到用例"；应直接显示"包名+未找到用例"。
3. 统计行把 `no_case`（未找到用例的包，包维度）和 mugen 用例计数（总计/通过/失败/跳过/未执行，用例维度）混在一行，不同维度混显。
4. 用例列表分组头显示"失败 2/12"，数字实为 `passed` 数（贴在"失败"标签旁），无法判断是失败 2 还是成功 2。
5. 筛选失败用例后显示"失败 0/1"（passed=0/total），冗余且有歧义。

## 决策

### 1. 统计行拆两维度，包行仅 pkgcmd

统计卡（run-job-detail）分两行：

- **用例行**：`总计` / `通过` / `失败`（常显）；`跳过` / `待执行`(pending) / `未执行`(not_executed) / `执行中`(running) / `异常` / `超时`（>0 才显）。`总计`不含 `no_case`（未找到用例的包，包维度归包行），与各状态计数求和一致。
- **包行**（仅 `result_parser === 'pkgcmd'`）：`找到用例 x | 未找到用例 N`。`x` = 找到 mugen 用例的包数（按 suite 分组、有非 `no_case` case 的 suite 数）；`N` = `no_case` case 数（= 没找到用例的包数）。

包行只在 pkgcmd 显示——只有 pkgcmd（`case_filter=repodata_packages` → `plan_cases`）产生 `no_case` 包；pkgserver（`service_test_cases`）与其余模块无此维度。

### 2. 用例列表分组头（suite=包）

- **默认（未筛选）**：suite 全 `no_case`→"未找到用例"；全 `not_executed`→"未执行"；全 `skipped`→"跳过"；全 `pending`→"待执行"；有 `running`/`pending`（执行中、非全 pending）→ `执行中 a/x`（`a`=已出结果数，含通过/失败/超时/异常/跳过，`x`=总数；蓝底）；其余（全终态、有跑过或混合）→ `通过 a/x`（`a=x` 绿底，`a<x` 红底）。统一格式，消除"清一色跳过"与 issue 4 歧义；执行中的 suite 显"执行中"蓝底而非"通过 0/x"红底（避免误读为失败）；物理机不执行的 suite 显"未执行"而非"通过 0/x"。
- **筛选某状态**：`<状态> b`（`b`=该 suite 内该状态条数，无 `/total`）。
- **`no_case` 的 suite**（没找到用例的包）：suite 层直接显示"未找到用例"，不展开、不走"通过 a/x"。

### 3. case 行状态标签

case 行 `pending` 标签由"等待"改为"**待执行**"（与统计桶一致）；`not_executed→未执行`、`skipped→跳过`、其余不变。语义区分：`跳过`=mugen 跑了但用例内部跳；`未执行`=物理机开关关/64k 未转测，不会跑；`待执行`=pending，会跑、排队中。

### 4. `pending`/`not_executed`/`skipped` 三类分开（不合并）

- **待执行** = `pending`（会跑、排队中）。
- **未执行** = `not_executed`（物理机开关关 / 64k 未转测，**不会跑**）——独立桶，**不进待执行、不进跳过**。
- **跳过** = `skipped`（mugen 跑了但用例内部跳）。

统计卡/矩阵三类分开计数（均 >0 才显）。这是对本 ADR 初版"待执行聚合 pending+not_executed"的修正——初版把 `not_executed`（物理机不执行）误并入待执行，致物理机不执行的用例显示成"待执行"且"跳过"项看似被删；改为三类分开后，物理机不执行的用例归"未执行"。

### 5. 执行矩阵格子

矩阵格子（`execution-detail`）：

- 状态 chip：`pending→待执行`。
- 计数：`通过`/`失败` 常显；`执行中`(running)/`待执行`(pending)/`未执行`(not_executed)/`跳过`(skipped)/`未找到用例`(`no_case`，仅 pkgcmd 格子)/`异常`/`超时` >0 才显。

修复现状（矩阵不渲染 `not_executed`、"跳过"常显 0）。

## 取舍 / 不采用

- **不合并 `not_executed`+`skipped`（用户选分开）**：mugen 跳过（skipped）与物理机不执行（not_executed）是不同语义，分开显示"跳过"/"未执行"；`not_executed` 不计入"待执行"（它不会跑）。
- **分组头不采用"状态标签 + x/y"**：改统一"通过 a/x"着色（uniform suite 显状态标签）——避免"失败 2/12"（数字实为 passed）这类歧义，且首屏不再清一色"跳过"。
- **矩阵不加"找到用例"行**：矩阵格子小，`通过`/`失败` 已是 found case 的结果，"找到用例"冗余；只加"未找到用例"(`no_case`)。
- **不改后端**：所需数据（`counts.not_executed`/`no_case`、`case_run.suite_name=包名`、`result_parser`）后端已提供，全部前端渲染层解决。

## 影响

- 涉及前端：`run-job-detail.vue`（统计卡、`groupedCases`/`caseStats`、分组头、case 行）、`execution-detail.vue`（矩阵格子计数）、`pipelines.ts`（`PipelineExecutionSummary`/`RunJobDetail` 类型如有字段缺失）。
- `docs/spec/0003-test-pipeline.md` §5.4（run-job 详情统计/用例列表、矩阵格子）需同步本 ADR 的展示语义（实施时一并改）。
- 不影响后端 API/数据模型。
