<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: 修复流水线 trigger enqueue 早于事务提交的竞态

## 状态

complete。Audit PASS-WITH-NITS（2 nit 已修）；backend `./scripts/check.sh backend` 256 passed，5 pre-existing failure（`mugen_runner._env_label` 用 `case_run.env_set_id` 与 `SimpleNamespace` mock 不匹配，diff 不含 mugen_runner，与改动无关）；frontend 未碰。

## 目标

修复 `trigger_pipeline` 把 `enqueue_run_job`（`send_task`）放在 `db.commit()` 之前导致的竞态：
worker（concurrency=20）从 redis 消费 task 几乎瞬间，`run_pipeline_run_job_task` 第一行
`db.get(PipelineRunJob, id)` 在新事务里查不到未提交的 run_job → `if run_job is None: return`
→ task 被 ack 消失，run_job 永远 `pending`（前端显示"等待"），连 test_job/VM 都没建。

实锤：2026-08-05 pkgmanage-test 流水线 5 个版本，20.03-SP4 / 22.03-SP4 的 run_job
永远 pending、test_job=None、vm_request=None，task 不在 redis ready/active/unacked；
24.03 三个版本在 commit 后被消费，正常 running（其中 SP1 的 VM 创建失败已正确标 error）。
vms 侧 `submit_vm_request`（service.py:360-371）已是"先 commit 后 enqueue"正确模式。

## 范围

- **A. 对齐 vms 模式**：`trigger_pipeline`（service.py:282-327）只建 Execution + Run +
  RunJob 空壳 + `db.flush()`，**移除内部 enqueue 循环**（service.py:322-325）。新增
  `enqueue_run_jobs(db, run_jobs, actor_user_id)` 函数；`router.post_trigger`（router.py:285-294）
  改为 `trigger_pipeline(...)` → `db.commit()` → `enqueue_run_jobs(...)` → `db.refresh(execution)`。
- **B. enqueue 失败标个体 error**：`enqueue_run_jobs` 循环里 `try/except
  TestJobQueueUnavailableError`，单个失败 → 该 run_job `status="error"` +
  写 `TaskEvent(phase="enqueue_failed", error_code="queue_unavailable")` + `db.commit()`，
  继续 enqueue 其他 run_job。endpoint 返 201（execution 已建，失败 run_job 显式 error）。
- **C. ADR 0033 对账**：ADR 0033 决策 2 描述了 trigger 模式但遗漏 enqueue 顺序约束，
  补充"enqueue 必须在事务提交后"及理由（worker 用独立 session 查 run_job，commit 前消费
  会查不到导致卡 pending）。

## 非目标

- 不改 vms 侧（`submit_vm_request` 已是正确模式）。
- 不加补偿机制（CLI/API/前端按钮批量重投递）——修复后不再产生新卡 pending run_job；
  历史遗留一次性手动清理（已手动补偿 20.03/22.03）。
- 不加 task 端 autoretry 兜底（治标，竞态窗口仍存在）。
- 不加后台扫描/启动钩子自动重投递（违反 AGENTS.md 不默认加后台任务）。
- 不改 VM 创建失败回写链路（已正常，24.03-SP1 vm_create_failed 已正确标 error）。
- 不改 spec 0002（此修复不改对外产品行为，只改内部事务顺序）。
- 不改 CONTEXT.md（enqueue 顺序是实现约束，放 ADR 不放领域语言）。

## 确认决策（grilling 5 题）

1. **修复策略 = 对齐 vms 模式**：trigger_pipeline 只建空壳+flush，router commit 后
   enqueue。与 vms `submit_vm_request` 一致，直接消除根因，不引入新机制。
2. **enqueue 失败 = 标个体 error 继续**：单个 run_job enqueue 失败 → 该 run_job
   `error(queue_unavailable)` + commit + 继续其他 + 返 201。不整体回滚（会重蹈
   已 enqueue task 卡 pending 的覆辙）。
3. **补偿机制 = 不做**：修复后无新卡 pending；历史一次性手动清理；AGENTS.md 简单优先。
4. **测试/验收 = 核心两行为**：TDD 覆盖 (1) trigger 后 enqueue 在 commit 后（worker
   新 session 可见）；(2) 单个 enqueue 失败标个体 error，其他继续，返 201。
5. **文档 = 只补 ADR 0033**：决策 2 补 enqueue 顺序约束；CONTEXT.md 不动。

## 任务

- [x] T0 TDD 行为1：`test_trigger_enqueues_run_jobs_only_after_commit` RED→GREEN。
  - RED：monkeypatch `celery_app.send_task` 捕获每次调用，在捕获回调里开新
    `SessionLocal` 查 run_job 能查到（事务已提交）；POST /trigger 后验证 send_task
    被调用 N 次（每 run_job 一次）且回调时 run_job 可见。
  - GREEN：`trigger_pipeline` 移除内部 enqueue 循环；新增 `enqueue_run_jobs`；
    `post_trigger` 改 commit 后调 `enqueue_run_jobs`。
- [x] T1 TDD 行为2：`test_trigger_marks_runjob_error_when_enqueue_fails` RED→GREEN。
  - RED：monkeypatch `send_task` 第 2 次调用抛 `TestJobQueueUnavailableError`；
    POST /trigger 返 201；run_job[1] `status=error`；run_job[0]/[2] `status=pending`；
    有 `enqueue_failed` task_event。
  - GREEN：`enqueue_run_jobs` 加 try/except + 标 error + task_event + commit + 继续。
- [x] T2 ADR 0033 决策 2 补充"enqueue 必须在事务提交后"约束 + 理由。
- [x] T3 验证：`./scripts/check.sh all`（ruff + pytest 全量 + 前端）干净，新增两测试绿。
- [x] T4 Audit：独立只读审查 + 复跑验证。

## 进度

- T0–T4 完成。TDD 两行为 RED→GREEN；ADR 0033 决策 2 补充 enqueue 顺序约束 + 决策 5 补 `pending→error` 边注。
- Audit 独立只读审查 PASS-WITH-NITS，2 nit 已修（测试断言解耦 `plan_run_jobs` 顺序改 count；ADR 决策 5 补 `pending→error` 注），复跑 ruff All checks passed + 7 trigger 测试绿。
- 已手动补偿 20.03/22.03（重投递后 pending→running，反证根因）。

## 验证命令与验收场景

- 检查入口：`./scripts/check.sh all`（已设 `UV_CACHE_DIR`）。
- 单测：`./scripts/check.sh backend`（ruff + compileall + pytest）。
- 验收场景：
  1. 行为1 绿：trigger 后 send_task 每次调用时 run_job 在新 session 可见。
  2. 行为2 绿：部分 enqueue 失败 → 个体 error，其他 pending 已 enqueue，返 201。
  3. 全量 `./scripts/check.sh all` 干净。
- 端到端（可选，用户触发部署后）：重跑 pkgmanage-test，确认所有版本 run_job 不再卡 pending。
