<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# RunJob 详情页统计口径与展示修复

## 背景

流水线执行期间 RunJob 详情页存在 3 个展示缺陷：

1. 用例列表分组头 `执行中 a/x` 的 `a` 只数 `passed`（沿袭"通过 a/x"口径），失败未计入，进度失真。
2. 统计卡 `总计` 取 `case_runs.length`，pkgcmd 模块下把 `no_case`（未找到用例的包，包维度）计入，导致 `总计` 不等于各状态桶之和，违反 ADR 0037"不同维度不混显"原则。
3. 统计卡 `异常`、`超时` 各显示两次（顶部无条件一次 + 底部 >0 才显一次）；ADR 0037/Spec 0003 §5.4 均定义为 >0 才显。

## 范围

- `frontend/apps/web-antd/src/views/pipelines/run-job-detail.vue`：
  - 分组头 `执行中 a/x` 的 `a` 改为已出结果数（passed/failed/timeout/error/skipped），口径经用户确认。
  - 统计卡 `总计` 排除 `no_case`，口径经用户确认。
  - 删除顶部无条件 `异常`/`超时` 两个统计项，恢复 Spec 定义的顺序。
- 新增 `run-job-case-stats.ts`（纯函数：`finishedCaseCount`、`totalCaseCount`）及同名测试，沿用 pipelines 目录"纯逻辑抽 `.ts` + 同名 `.test.ts`"惯例。
- 文档同步：Spec 0003 §5.4（`总计` 口径、`执行中 a/x` 语义）、ADR 0037（对应两处决策 + 修正记录）。

## 明确不做

- 不改后端 API 与数据模型（纯前端渲染层问题）。
- 不改执行矩阵页（execution-detail.vue，其计数无 a/x 语义）。
- 不改用例重跑弹窗与筛选逻辑。
- 不新增依赖。

## 实施步骤

1. RED：编写 `run-job-case-stats.test.ts`（失败含失败/超时/异常的计数、总计排除 no_case），确认失败。
2. GREEN：实现 `run-job-case-stats.ts`，确认通过。
3. 接线 `run-job-detail.vue`：`caseStats.total` 用 `totalCaseCount`；执行中标签 `a` 用 `finishedCaseCount`；删除重复统计项。
4. 同步 Spec 0003 §5.4 与 ADR 0037。
5. 验证（见下）。

## 验证标准

- `finishedCaseCount`/`totalCaseCount` 定向测试先失败后通过。
- `pnpm vitest run apps/web-antd/src/views/pipelines` 全绿。
- `pnpm typecheck`、`pnpm lint` 通过。
- `./scripts/check.sh` 最终通过一次。
