<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: ADR、Spec 与计划决策对账

## 状态

文档修订与 `./scripts/check.sh docs` 已完成。2026-09-04 已完成 Grill：以当前代码行为和时间更新的已采纳 ADR 为准；不满足可追溯审查记录的计划保持 active；已被后续决策改变的搁置计划不按旧方案恢复。合入前审查修正三处（Spec 0003 env_type 维度语义与 SKIPPED→NO_CASE、ADR 0015 §5.4 链接、物理机复用未来方案移出 active），快进合入 main。

## 范围

- 修订 Pipeline Spec 中 `env_type=both`、`suite_name` 和 EnvSet 执行边界的过时描述。
- 为被后续 ADR 改变的 ADR 0007、0014、0015 与 0023 增加明确的范围或部分取代说明。
- 收敛 64k 与物理机搁置计划，使其不再描述已废弃的实现路径，并移入 `docs/plans/superseded/`。
- 记录 `kernel-module-pipeline`、`types-and-exceptions-cleanup` 与 `pkgcmd-pkgserver-physical-toggle` 三份实质完成但缺少可追溯审查记录的计划仍不能归档的原因。

## 非目标

- 不改变业务代码、数据模型、API 或运行时行为。
- 不因无法核实 PR/MR 审查记录而把计划移入 `completed`。
- 不补编号重复的历史文件；后续新文档不得再仅以重复编号作为引用。

## 实施步骤

1. 以当前实现与较新的已采纳 ADR 复核冲突条目。
2. 最小修订 ADR、Spec 和 active plan，保留历史背景并标明适用边界。
3. 运行文档检查与交叉引用检查，复核 diff。

## 验证标准

- Spec 0003 对 `both`、`suite_name`、物理 EnvSet 的描述与 ADR 0018 和当前实现一致。
- 搁置物理机计划不再要求以 `management_status=maintenance` 作为测试期锁。
- 64k 计划不再要求已经删除的 pre-env 安装路径。
- `kernel-module-pipeline`、`types-and-exceptions-cleanup` 与 `pkgcmd-pkgserver-physical-toggle` 明确保留 active 的原因。

## 实施结果

- Spec 0003 已收敛为 `both` 单 RunJob、`suite_name` 和按 EnvSet 执行；Spec 0002 明确普通 TestJob 与流水线内部 TestJob 的边界。
- 早期 ADR 已增加适用范围、替代关系或当前规格指针；旧 64k、物理机调度和物理机复用提案均移入 `docs/plans/superseded/`，复用目标如需实施必须按 ADR 0029 重新 Grill。
- 已补齐三份实质完成计划的清单和留在 active 的可追溯性原因。
- `./scripts/check.sh docs`：通过。
