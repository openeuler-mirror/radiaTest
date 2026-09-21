<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan（历史提案，已取代）：pkgcmd/pkgserver physical EnvSet 复用前序物理机

## 状态

尚未实施。旧的测试期 `management_status=maintenance` 锁和固定 sleep-and-retry 前提已被 [ADR 0029](../../adr/0029-physical-test-resource-usage-state.md) 取代。本文保留复用目标的历史提案；如需实施，必须重新 Grill 并在 `docs/plans/active/` 新建可执行计划。

## 目标

在 update 流水线中，pkgcmd/pkgserver 的 physical EnvSet 可复用同一 `(execution, version, arch)` 前序模块已完成测试的物理机，避免不必要的 PXE 重装。没有可复用前序资源时，保持现有按模块 `usage_scenario` 选择物理机并 PXE 重装的 fallback。

## 当前约束

- 资源是否正在被测试由非终态 TestJob 的 physical Env Node 关联派生；不以 `management_status` 表示整个测试期占用。
- 认领候选资源时使用数据库行锁，并立即持久化新 Env Node 的 `resource_id`。同一资源不能被两个非终态 TestJob 同时使用。
- `management_status=maintenance` 仅覆盖实际 PXE 重装的原子阶段；重装完成后恢复 `active`，不表示资源已经可被其他测试并发使用。
- 复用候选必须满足：前序 TestJob 已终态、前序 physical Env Node 已关联资源、资源可 SSH 访问且为 `active`。前序测试成功与否不是复用条件。
- 前序链保持 pkgcmd → kernel；pkgserver → pkgcmd、kernel。docker/pkgmanage 不参与。
- 找不到或无法使用前序资源时，fallback 按当前模块的 `usage_scenario` 选取测试空闲资源并重装；它也必须遵循 ADR 0029 的行锁和活动节点排他规则。
- 等待仅受当前 TestJob 的既有总截止时间约束；不新增固定 sleep-and-retry、Celery 任务依赖、全局并发配置或额外锁表。

## 非目标

- 不改变 ADR 0018 的 `both` 单 RunJob、内部 VM/physical EnvSet 并行模型。
- 不用显式 Celery 链表达 kernel → pkgcmd → pkgserver 依赖。
- 不修改 PXE 主流程、Mugen 部署策略、`keep_env` 语义或资源管理 API。
- 不因本方案提高 worker 并发或新增轮询、后台任务、资源状态列。

## 实施前确认项

1. 重新 Grill：确定候选查询、前序终态判断、资源行锁顺序、等待/超时传播和 fallback 的精确边界。
2. 在新 active 实施计划中写明最小 TDD 场景：前序复用、前序不可用 fallback、并发争用、资源测试期禁止重认领。
3. 代码、Spec 与 ADR 同步后，运行项目检查、远程 dev 端到端验证，并保留 PR/MR 审查记录。

## 历史说明

早期计划将整个测试期写成 `management_status=maintenance`，并要求 `_find_occupied_physical` 固定 sleep-and-retry、提高 worker 并发及按模块拉长 soft time limit。这些前提已被 ADR 0029 否决，不再具有实施效力。
