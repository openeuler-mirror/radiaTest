<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: 回收无 task_id 的 VM 申请孤儿

## 状态（2026-09-04 归档）

Grill 完成并确认；TDD 实现已合入 `fix/orphan-async-task-recovery`；同步修订 [ADR-0035] 与 SPEC
[`0005-platform-runtime.md`](../../spec/0005-platform-runtime.md) 的 worker 恢复约束（原三条禁令被本修订收敛到
`task_id IS NULL` 的窄口子）。

**2026-09-04 kimariyb 端到端验证**：`UPDATE vm_requests SET status='pending', created_at=now()-65min,
task_id=NULL` → GET `/api/v1/vm-requests?all=true`（触发 `_recover_vm_creates` 懒检查）→ 恢复器把
VMRequest 收敛为 `status='failed'` + `error_code='orphaned_no_task'` + `error_message="申请从未成功派发（无
task_id），已回收为失败"`；task_events 与 audit_log 双侧都留有恢复痕迹。原 kimariyb 里 44 条堆积 SQL 一次性
清完；prod 侧 151 条堆积等下轮 `bdfac13`/`c97817a` 部署后自然被同一懒检查回收。

[ADR-0035]: ../../adr/0035-worker-interruption-recovery.md

## 目标

修复 worker 恢复逻辑的盲区：VM 申请(`vm_requests`)因崩溃/中断卡在 `pending`/`queued`/`creating` 且 `task_id IS NULL` 时，现有 `_recover_vm_creates` 永不回收，导致前端"申请记录"里堆积永久"创建中/等待创建/排队中"。

实证(只读诊断)：kimariyb 44 条、prod 151 条(122 creating + 29 pending)`task_id` 全为 NULL，其 started 事件 `celery_task_id` 也为 NULL；最早卡住约 77 小时，刷申请页与 worker 重启均无法收敛。已对 kimariyb 做一次性 SQL 清理，prod 由本修复自愈。

## 根因

`_recover_vm_creates`(`backend/app/modules/tasks/recovery.py:154`)的两个硬条件把无 task_id 的记录全部排除：

- `VMRequest.task_id.is_not(None)`；
- EXISTS 关联 `TaskEvent.celery_task_id == VMRequest.task_id`(NULL 相等在 SQL 里恒为 unknown)。

## 范围

- 在 `_recover_vm_creates` **新增一条"无 task_id 孤儿"回收分支**，与有 task_id 分支互斥(`task_id IS NULL` vs `IS NOT NULL`)。
- 判定：`task_id IS NULL` 且 `status ∈ {pending, queued, creating}` 且 `created_at <= as_of - VM_CREATE_TIMEOUT(60min)`。
- 两种触发(`WORKER_STARTUP`/`LAZY_READ`)用**同一条件**，启动不立即清(避开 `submit_vm_request` 先落 pending+null 再补 task_id 的提交竞态)。
- 动作：`status=failed`、`error_code='orphaned_no_task'`、`error_message` 说明"申请从未成功派发(无 task_id)，已回收为失败"、`completed_at=as_of`；按 `_record_recovery` 写 failed 事件与审计，`before_status` 取行真实值。
- 同一 handler 内合并计数、单次提交；不改已有有-task_id 分支与 `_recover_test_jobs` 等。

## 明确不做

- 不回收 `task_id IS NOT NULL` 的 `pending`(broker 里可能仍有存活消息，维持现有 WORKER_STARTUP 不变量)。
- 不新增定时/轮询后台任务；仍走既有懒读 + worker 启动两条触发。
- 不改前端状态标签映射。
- 不回捞/清理这些孤儿可能占用的宿主资源(它们从未派发，无 VM 实体)。

## 确认决策(grilling)

1. 孤儿判定:仅 `task_id IS NULL`。
2. 时机:新分支两种触发统一要求 `created_at` 超 60min;启动不立即清;有 task_id 分支语义不变。
3. 归类:新 `error_code='orphaned_no_task'`,走 `_record_recovery`,`before_status` 用行真值。
4. Code review 后追加:与 [ADR 0035 修订节](../../adr/0035-worker-interruption-recovery.md)、SPEC 0005 §异步任务中断 对齐,原"排队但尚未开始的记录绝不处理"改为"`task_id IS NULL` 且超阈值可作为派发失败证据"。

## 任务

- [x] P1 失败测试:null-task_id 的 `creating`/`queued`/`pending` 三例被回收为 `failed`+`orphaned_no_task`(lazy 与 startup 各一)。
- [x] P2 回归测试:有 task_id 的 `pending` 仍不被回收(`test_worker_startup_recovers_started_tasks_and_ignores_queued_tasks` 保持绿)。
- [x] P3 边界测试:null-task_id 但未过 60min(lazy 与 startup)均不回收。
- [x] P4 实现 `_recover_vm_creates` 新分支。
- [x] P5 `./scripts/check.sh backend`+`./scripts/check.sh docs` 通过;端到端在 kimariyb 部署后由用户验证(SQL 已回收现有 44 条,残留 0)。
- [ ] P6 分支合入 `main`(先跑 `code-review`)。

## 验证命令与验收场景

- 定向测试:`backend/tests/test_worker_recovery.py`(新增用例 RED→GREEN)。
- 检查入口:`./scripts/check.sh backend`、`./scripts/check.sh docs`。
- 端到端(kimariyb):部署 `fix/orphan-async-task-recovery` 后,未来任何因派发失败卡在 `pending`/`queued`/`creating` 且 `task_id IS NULL` 且 60min 未处理的申请,刷"申请记录"页或 worker 重启时会自动收敛为 `failed`(`orphaned_no_task`),前端不再堆积"创建中/等待创建"。
