<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: 回收无 task_id 的 Pipeline RunJob 孤儿

## 状态（2026-09-04 归档）

Grill 完成并确认；TDD 实现已合入 `fix/orphan-async-task-recovery`；同步修订 [ADR-0035] 与 SPEC
[`0005-platform-runtime.md`](../../spec/0005-platform-runtime.md) 的 worker 恢复约束（原"缺 task_id 或 started
事件不处理"改为"`task_id IS NULL` 的 pending 且超阈值可作派发失败证据"）。

**2026-09-04 kimariyb 端到端验证**：`UPDATE pipeline_run_jobs SET status='pending', created_at=now()-16h,
task_id=NULL` → GET `/api/v1/pipelines/run-jobs/<id>`（该 endpoint 走 `_recover_pipeline_tasks`）→ 恢复器把
RunJob 收敛为 `status='error'` 并写 `phase='error'` + 事件 `error_code='orphaned_no_dispatch'`；task_events 与
audit_log 双侧都留有恢复痕迹。code-review 记录保留在 main `bdfac13` 与其后 amend merge。

[ADR-0035]: ../../adr/0035-worker-interruption-recovery.md

## 目标

补齐 `_recover_pipeline_run_jobs` 的同类盲区:RunJob 因崩溃卡在 `pending` + `task_id IS NULL`(即从未进入 `enqueue_run_jobs` 的 task_id 补齐阶段),现有恢复永不触碰。设计与 `vm-orphan-request-recovery` 同构,阈值不同。

## 根因

`recover_interrupted_run_jobs`(`backend/app/modules/pipelines/service.py:421`)三条 AND 硬条件:

- `status IN ('preparing','running')` — 排除 `pending`;
- `task_id IS NOT NULL`;
- EXISTS `pipeline_runjob` 的 `started` 事件且 `celery_task_id == task_id`。

`plan_run_jobs` 提交后、`enqueue_run_jobs` 补 `task_id`(`service.py:361-363`)前进程崩溃 → 三条全不满足 → 永久 `pending` 孤儿。

## 范围

- 在 `recover_interrupted_run_jobs` 新增"无 task_id 孤儿"回收分支,与有 task_id 分支互斥。
- 判定:`task_id IS NULL` 且 `status = 'pending'` 且 `created_at <= as_of - TEST_JOB_TIMEOUT`(15h)。
- 两种触发同一条件,启动不立即清(避开 `plan → commit → enqueue_run_jobs` 的写入窗口竞态)。
- 动作:`status='error'`;`orphaned_no_dispatch` 落在恢复 task_event 与系统审计里(`PipelineRunJob` 模型无 `error_code` 列);message "申请从未成功派发(无 task_id),已回收为异常";走 `record_task_recovery`;`before_status` 取行真值。
- 保留现有 `list_recoverable_pipeline_test_job_keys` 与之配对的 TestJob 收敛链路不动。
- 同一 handler 内合并计数、单次提交。

## 明确不做

- 不回收"有 task_id + pending + 无 started"的 broker 丢消息场景(手动 `POST /pipelines/run-jobs/{id}/cancel` 兜底,与 VM 策略一致)。
- 不为孤儿引入新常量,复用 `TEST_JOB_TIMEOUT`。
- 不引入 `cancel_requested` 通道(那是 `runjob-cancel` 计划的正交逻辑)。
- 不改前端状态标签映射。

## 确认决策

1. **Q1**:接受"有 task_id + pending"保持自动盲区;手动 cancel 兜底。
2. **Q2**:孤儿阈值沿用 `TEST_JOB_TIMEOUT=15h`(用户反馈频繁后单开 `PIPELINE_ORPHAN_TIMEOUT`)。
3. **Q3**:错误码 `orphaned_no_dispatch`,走 `record_task_recovery`,`before_status` 用行真值。

## 已记录的设计取舍

已由同批 [ADR 0035 修订](../../adr/0035-worker-interruption-recovery.md)承载:
- 15h 阈值对"从未派发"偏长、可按用户反馈调窄 → ADR-0035 修订"取舍"。
- WORKER_STARTUP 立即清 `preparing/running` 假设单副本、多副本滚动升级会误杀其他 worker in-flight → ADR-0035 原"决策"第 4 条 + "影响"第 2 条已明写"不支持同一环境横向运行多个 Worker 容器",扩副本前需另立 ADR。

## 任务

- [x] P1 失败测试:`pending + task_id NULL + created_at 超 15h` 在 lazy 与 startup 两种触发下都回收为 `error`,`orphaned_no_dispatch` 记在恢复事件中。
- [x] P2 边界测试:`pending + task_id NULL` 未过 15h 不回收(lazy 与 startup 各一)。
- [x] P3 回归测试:`pending + task_id 有` 仍不被孤儿分支误杀(`test_worker_startup_recovers_started_tasks_and_ignores_queued_tasks` 保持绿;独立用例 `test_orphan_run_job_recovery_skips_with_task_id_pending`)。
- [x] P4 实现 `recover_interrupted_run_jobs` 新分支。
- [x] P5 `./scripts/check.sh backend`+`./scripts/check.sh docs` 通过。
- [ ] P6 分支合入 `main`(先跑 `code-review`),后续在 kimariyb 部署刷流水线页验证一条 `pending + task_id NULL + created_at > 15h` 变为 `error`。

## 验证命令与验收场景

- 定向测试:`backend/tests/test_worker_recovery.py`(新增用例 RED→GREEN)。
- 检查入口:`./scripts/check.sh backend`、`./scripts/check.sh docs`。
- 端到端(kimariyb):部署 `fix/orphan-async-task-recovery` 后,任一 `pending + task_id NULL + created_at > 15h` 的 RunJob 会被 worker 重启或刷流水线列表/详情页顺带收敛:行状态 `error`,恢复 task_event `error_code='orphaned_no_dispatch'` 且 message 含"无 task_id"。
