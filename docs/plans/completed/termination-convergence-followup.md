<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: 终止收敛补正

## 状态

- 两轮终止收敛实现与定向回归已完成；恢复竞态、执行全生命周期取消和 VM 销毁派发盲区均已覆盖。
- 本轮在用户确认的边界内完成：恢复结果拥有终态写入权；恢复仍不对外部资源执行自动清理或重放。
- `8ec2281 fix: converge interrupted cancellation and VM destroy recovery` 合入 `main` → `a788699` 之后再次验证：`./scripts/check.sh` 全量通过（backend 495 passed / 1 skipped，docs/scripts/frontend 全绿），基线已恢复。计划已归档到 `docs/plans/completed/`。

## 范围

- 将单个 EnvSet 的挂死中断与 TestJob 级取消信号隔离：挂死当前 case 记录为错误，后续 case 和兄弟 EnvSet 保持执行；用户取消与软超时仍终止整个 TestJob。
- 让 `pending`、`preparing` 与 `running` 的 Pipeline RunJob 取消都收敛为 `cancelled`，避免没有 TestJob 的取消永久停在 `cancelling`。
- 让恢复为 `error` 或 `cancelled` 的 TestJob 与 RunJob 成为终态写入屏障，仍在运行的 Worker 不得覆盖恢复结果。
- 将 `cancelling + cancel_requested` 的中断 RunJob 及其 TestJob 收敛为 `cancelled`。
- 在 TestJob 的 VM 创建、环境准备和用例执行全生命周期观察既有取消请求；取消发生在执行前时一并收敛尚未执行的 EnvSet 与 CaseRun。
- 回收已派发但从未写入 `destroy_started` 事件且超过既有销毁时限的 VM 销毁锁，使资源可被再次释放。
- 让流水线自收集日志保持 best-effort，日志失败不得反向失败已完成的流水线任务。

## 非目标

- 不修改数据模型、迁移、取消 API 路径或权限边界。
- 不对 Worker 中断恢复自动连接宿主机、删除 VM 或测试环境，也不自动重新投递 Celery 任务。
- 不新增定时器、周期扫描、依赖或新的取消 API；继续复用现有 15 秒取消观察和懒读取/Worker 启动恢复入口。

## 实施步骤

1. 在恢复服务、TestJob 执行器、RunJob Worker 与 VM 销毁恢复入口分别写失败测试，固定终态不回写、取消收敛、超时锁回收和日志 best-effort 的行为。
2. 以最小状态检查和既有事件/锁记录实现恢复优先级与 `cancelling` 收敛，不改变恢复的外部副作用边界。
3. 将取消观察提升到 TestJob 生命周期；保留用例运行期间的远程 Mugen 停止，预执行取消只收敛数据库中的未执行子记录。
4. 扩展恢复决策与运行时规格，明确排队销毁和取消中断的结果。
5. 运行定向检查、项目检查和最终代码审查；完成后将相关计划移入 `docs/plans/completed/`。

## 验证标准

- 单个 EnvSet 挂死后，当前 case 为 `error`，后续 case 可继续，TestJob 最终为 `error`；兄弟 EnvSet 不被取消。
- 取消 `pending` 或 `preparing` RunJob 不创建或执行 TestJob，最终状态为 `cancelled`。
- 同一批无 `task_id` 的孤儿记录恢复两次时，第二次不重复改变状态、事件或审计记录。
- 恢复已将 TestJob/RunJob 写为终态后，旧 Worker 的后续成功或失败结果不能覆盖该终态。
- `cancelling + cancel_requested` 的 RunJob 在恢复后为 `cancelled`，关联 TestJob 同步为 `cancelled`。
- 取消在 VM 创建或环境准备期间到达时，当前操作结束后 TestJob 进入 `cancelled`，未执行的 EnvSet 与 CaseRun 为 `not_executed`。
- 超过既有销毁时限且没有 `destroy_started` 的 VM 销毁任务会清除执行锁、保留资源，并允许后续重新释放；未超时的排队任务不受影响。
- 自收集日志失败不会改变已收敛的 Pipeline RunJob 终态。
- 相关 pytest 与 `./scripts/check.sh` 通过，且没有新增未使用代码或导入。
