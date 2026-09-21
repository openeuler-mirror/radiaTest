<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# 测试任务与 RunJob 终止收敛

## 范围

在既有 RunJob cancel 之上补齐"终止真正能终止"的机制：一次 cancel 请求或
Celery 软超时到达后，`process_test_job` 内的并行环境集线程必须秒级
（本地 `run_process` 打断 ≤5s；端到端从"点取消"到"case 收敛"受 `_cancel_watcher`
15s 轮询周期约束 ≤20s）停止远程 SSH 子进程并收敛 RunJob / TestJob 状态。
同时修复流水线状态聚合把 `cancelled` 误当作非终态导致"取消后仍显示执行中"
的一致性缺陷。

- `run_process` 支持外部 `threading.Event` 打断 selectors 等待并 kill 本地子进程。
- cancel_event 贯穿 `run_control_command → run_case / wait_for_ssh_ready /
  configure_mugen_node / run_hook / prepare_env` 全链路。
- `process_test_job` 手写 `ThreadPoolExecutor` 终止序列，
  SoftTimeLimitExceeded 不再被 `with __exit__` 阻塞。
- HangDetector 判 hung 且非取消路径时 `cancel_event.set()`，取代等待 case 超时。
- `_cancel_watcher` 命中 DB cancel_requested 后同步 `cancel_event.set()`，
  保留原远程 `pkill -f mugen.sh` 旁路。
- 新增稳定错误码 `job_cancelled`，用于区分"人为取消"与"15h 软超时"。
- `pipelines/service._TERMINAL_STATUSES` 纳入 `cancelled`，
  `_worst_wins_run_status` 与 `compute_execution_status` 优先级：
  error > cancelled > failed > succeeded。

## 非目标

- 不新增独立 `POST /test-jobs/{id}/cancel` 端点（P1-B，另起）。
- 不改恢复器查询过滤（P1-E）；worker 崩溃后卡在 `cancelling` 的 RunJob
  不在本次收敛，另立计划处理。
- 不改 `pkill -f mugen.sh` 远程清理策略；不对 docker-mugen_exec_command 场景
  引入容器 PID namespace 感知的终止逻辑（P1-C）。
- 不改并行兄弟线程被 cleanup 误伤的场景（P2-G）。
- 不改数据模型（`cancel_requested` 列、`TestJobStatus.CANCELLED`、`cancelled`
  状态均已存在）。
- 不改 Celery 消息层（不改 `run_test_job_task` 的 `soft_time_limit`，
  不改 `apply_async` 派发）。
- 不新增轮询、定时器、后台 worker、通知、缓存。
- 不改前端任何页面（"已取消"标签已在既有 `cancelled` 状态支持范围内）。

## 实施步骤

### 1. 底层可中断执行器

- `backend/app/core/process_runner.py`
  - `run_process(args, *, timeout_seconds, output_limit_bytes, env=None,
    stdin=None, on_line=None, cancel_event=None)` 新增可选参数 `cancel_event`。
  - selector 分片：`selector.select(timeout=min(remaining, 2))`。
  - 每片前判 `cancel_event is not None and cancel_event.is_set()` →
    `process.kill()` + `cancelled=True`，跳出循环。
  - `ProcessResult` 加 `cancelled: bool = False` 字段（默认 False，向后兼容）。
  - `timed_out` 与 `cancelled` 语义分离：cancel 时 `cancelled=True, timed_out=False`。

- `backend/app/modules/test_management/remote.py`
  - `run_ssh_command / run_remote_bash_command / write_remote_file` 新增
    `cancel_event: threading.Event | None = None` 参数并透传到 `run_process`。
    `scp_directory / scp_file` 只用于 worker 完成 case 后的 best-effort 日志
    汇集(自带 ≤300s timeout),不属于终止关键路径,本次不改。

- `backend/app/modules/test_management/frameworks/mugen_runner.py`
  - `run_control_command` 新增 `cancel_event=None` 参数并透传。
  - 引用该函数的模块内部调用（`prepare_mugen / configure_mugen_node /
    wait_for_ssh_ready / run_hook / prepare_env / run_case` 等）在合适位置
    加 `cancel_event: threading.Event | None = None` 参数并向下转发。
  - 上层看到 `result.cancelled is True` → 抛 `TestJobExecutionError("job_cancelled", ...)`。

### 2. 准备阶段可中断

- `wait_for_ssh_ready`：内部 `time.sleep(min(retry, remaining))` 改为
  若传入 `cancel_event` 则 `cancel_event.wait(...)`；返回非 0 且 `result.cancelled`
  → 抛 `job_cancelled`。
- `configure_mugen_node`：同上。
- `run_hook`：`run_control_command` 传 cancel_event；`require_success` 前置判
  `result.cancelled` → 抛 `job_cancelled`。

### 3. 执行编排与终止序列

- `backend/app/modules/test_management/execution.py`
  - `_run_env_set_thread(job_id, env_set_id, actor_id, cancel_event)` 新增参数；
    内部把 cancel_event 传给 `execute_env_set`。
  - `execute_env_set(db, *, job, env_set, actor, cancel_event=None)`
    - `ensure_test_job_within_deadline(job, cancel_event)`：若 event 已 set，抛
      `TestJobExecutionError("job_cancelled", "测试任务已取消")`；15h 判定不变。
    - 环境集循环 case 分支保持不变（既有的 `_is_cancel_requested` DB 分支
      继续工作，作为跨进程兜底）。
  - `process_test_job(job_id)`
    - 手写 `executor = ThreadPoolExecutor(...)`；不再用 `with`。
    - try/finally 结构：
      ```
      cancel_event = threading.Event()
      executor = None
      try:
          ...
          executor = ThreadPoolExecutor(max_workers=...)
          futures = {executor.submit(_run_env_set_thread(jid, es, actor_id, cancel_event)): es ...}
          for future in as_completed(futures):
              ...
      except SoftTimeLimitExceeded:
          cancel_event.set()
          if executor is not None:
              executor.shutdown(wait=True)
          handle_job_execution_error(db, job=job, actor=actor,
              code="task_timeout", message="测试任务超过 15 小时总超时")
          return
      except (RemoteCommandError, TestJobExecutionError) as exc:
          # 说明:job_cancelled 已在 _run_env_set_thread 层就地收敛为
          # case_run=NOT_EXECUTED + env_set 内 remaining PENDING 转 NOT_EXECUTED
          # + cleanup_env_vms,不再抛到本层。这里只剩"真错误"路径。
          cancel_event.set()
          if executor is not None:
              executor.shutdown(wait=True)
          handle_job_execution_error(db, job=job, actor=actor,
              code=..., message=str(exc))
          return
      except Exception as exc:
          cancel_event.set()
          if executor is not None:
              executor.shutdown(wait=True)
          handle_job_execution_error(db, job=job, actor=actor,
              code="unexpected_execution_error", message=...)
          return
      finally:
          if executor is not None:
              executor.shutdown(wait=False, cancel_futures=True)
      ```
      Soft/异常路径 handler 内先 `wait=True`；finally 里的 `wait=False,
      cancel_futures=True` 是"提交阶段就异常"或未进 handler 的兜底。
    - 顶层 for future 循环结束后（所有 env_set 线程返回，无论自然/被打断），
      保留现有 `_is_cancel_requested → TestJobStatus.CANCELLED` 收敛；被
      cancel_event 打断的 env_set 已在子线程内完成 case/env_set 收敛与 VM 清理，
      主线程只做 job.status 终态判定，不再触发 cleanup_failed_job_envs
      （若 DB 里 cancel_requested=False 则是 Soft/兄弟线程触发，走 except
      SoftTimeLimit / 主线程错误处理路径）。

### 4. `_cancel_watcher` 与 HangDetector 集成

- `run_case(db, *, job, control, case_run, cancel_check=None, cancel_event=None)`
  - `_cancel_watcher` 命中 DB cancel_requested 时：
    `cancel_event.set()`；随后**保留**当前的 `pkill -f mugen.sh` 远程清理
    与 `cancel_detected.set()`（不改现有语义边界）。
  - `run_control_command` 传入 `cancel_event`；返回结果若 `result.cancelled=True`
    且 `cancel_detected.is_set()` 或 `cancel_event.is_set()` → 走现有 not_executed
    分支；若 `cancel_event.is_set()` 但非 cancel_detected（即由 HangDetector 或
    Soft 触发） → 抛 `job_cancelled`。
  - finally：`if detector.is_hung() and not cancel_event.is_set()`：
    `cancel_event.set()` → 触发下一条 SSH 秒退 + 上层抛 `job_cancelled`；
    同时保留现有 `_capture_and_store_console` + `raise EnvSetHangError`
    行为不变。
  - `_run_env_set_thread` 与 `execute_env_set` 收到 `EnvSetHangError` 后的
    现有循环 continue 语义不变（本 case 已 error，其余用例继续），
    但若 `cancel_event` 已被 set（用户取消）则在 for case 循环下一轮通过
    `ensure_test_job_within_deadline` 抛 `job_cancelled`，跳出。

### 5. Pipeline 状态聚合修复

- `backend/app/modules/pipelines/service.py`
  - `_TERMINAL_STATUSES = {"succeeded", "failed", "error", "cancelled"}`。
  - `_worst_wins_run_status`：在"error"检查后、"failed" 检查前，加
    `if "cancelled" in statuses: return "cancelled"`。
  - `compute_execution_status`：同上顺序插入 `cancelled`。
- 不改任何 API 响应字段、不改状态枚举、不改前端。

### 6. 与恢复器交互（本次仅确认边界，不改）

- `_recover_test_jobs` 与 `recover_interrupted_run_jobs` 的状态过滤本次不动，
  避免拉大范围。P0 落地后 worker 崩溃 + `cancelling` 卡死问题（P1-E）另立计划。

## 验证标准

**新增单元测试**（TDD 流程：先写失败用例）
- `test_run_process_cancel_event_kills_child_before_timeout`：跑 `sleep 30`，
  0.5s 后 set，断言 `result.cancelled=True and result.timed_out=False and duration<5s`。
- `test_run_process_cancel_event_absent_preserves_timeout_semantics`：
  回归保护——无 `cancel_event` 保持原 timeout 行为。
- `test_hang_detector_fires_on_hung_callback_when_hang_breaches_threshold`
  + `_does_not_fire_on_hung_when_healthy`。
- `test_wait_for_ssh_ready_raises_job_cancelled_when_event_pre_set`
  + `test_wait_for_ssh_ready_raises_job_cancelled_when_result_cancelled`
  + `test_configure_mugen_node_raises_job_cancelled_when_result_cancelled`。
- `test_ensure_test_job_within_deadline_raises_job_cancelled_before_timeout`
  + `_no_event_preserves_task_timeout`（回归保护 15h 语义不受影响）。
- `test_run_case_soft_cancel_event_marks_not_executed_and_raises`：模拟本地
  `run_control_command` 返回 cancelled=True，无 DB hit / 无 hang →
  case_run.status=NOT_EXECUTED + 抛 `job_cancelled`。
- `test_run_case_hang_fires_on_hung_via_cancel_event`：断言 `HangDetector`
  构造时收到 `on_hung=cancel_event.set` 且被调用。
- `test_process_test_job_soft_timeout_converges_under_5s`：mock
  `execute_env_set` 阻塞等 cancel_event，mock `as_completed` 抛 Soft →
  handler 内 set event → 子线程秒退 → shutdown 秒退 → 断言 elapsed <5s
  且 `job.status==error, error_code=="task_timeout"`。
- `test_process_test_job_db_cancel_finalizes_as_cancelled_not_error`：
  worker 存活 + DB cancel_requested=True + 无 case-in-flight → 走
  as_completed 正常退出路径后 `_is_cancel_requested` → `TestJobStatus.CANCELLED`。
- `test_compute_execution_status_cancelled_not_running`：DB 集成，
  全终态含 cancelled → execution 状态 `cancelled`；含 error 优先；
  `cancelling` 未终态仍显示 `running`。

**回归**：既有 `test_run_case_*` / `test_process_test_job_records_unexpected_execution_error`
/ `test_worker_startup_recovery_failure_does_not_escape` 全部保持通过
（`cancel_event` 默认参数保证旧签名调用点不破）。

**项目检查**
- 定向 pytest 相关文件通过。
- `./scripts/check.sh` 通过；无新增未使用代码与导入。

**验收**（人工/集成环境）
- 通过 dev 环境跑一个含 1 个 sleep 长 case 的 TestJob → 在 run-job-detail.vue
  点取消 → `_cancel_watcher` 下一次轮询 ≤15s 命中 DB cancel → 触发本地
  `run_process` kill → ≤3s 内 case_run 变 `not_executed`，TestJob `cancelled`，
  RunJob `cancelled`，pipeline 看板 execution 状态"已取消"而非"执行中"。
  (整体从"点取消"到"case 收敛"的响应时间受 `_cancel_watcher` 15s 轮询周期
  限制；`cancel_event` 分片 2s 是"信号发出之后"的秒级响应，不是端到端 SLA。)
- 通过 dev 环境把 `TEST_JOB_TIMEOUT` 临时调小 → 触发软超时 → 观察 Celery worker
  日志在 15h+几秒内收敛到 `task_timeout` 并 cleanup_failed_job_envs，
  pipeline execution 状态显示"异常"而非"执行中"（Soft 路径的 cancel → kill
  延迟由 `run_process` 2s 分片保证 <5s）。
