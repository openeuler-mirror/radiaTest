<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0031：TestJob/RunJob 终止收敛机制（本地 kill + 分级终止信号）

日期: 2026-09-03

## 状态

已采纳。部分取代 [ADR 0030](0030-runjob-cancel.md) 的"远程进程清理不本地 kill"
决策；扩展 [ADR 0016](0016-hang-detector-self-heal.md) 的 HangDetector 接口，新增
`on_hung` 回调；与 [ADR 0035](0035-worker-interruption-recovery.md) 的
`worker_interrupted` / `task_timeout` 恢复语义互补。

## 背景

ADR 0030 落地后，RunJob cancel 与 15h 软超时在生产环境暴露三类终止不彻底的问题：

- `process_test_job` 用 `with ThreadPoolExecutor(...) as executor`；Python
  `except SoftTimeLimitExceeded` 匹配**之前**会先执行 `with.__exit__` 里的
  `executor.shutdown(wait=True)`——此时子线程仍卡在 `run_control_command` 里
  最长 `CASE_COMMAND_TIMEOUT_SECONDS`(12h+60s) 的 sshpass 子进程上，15h 软超时
  形同虚设，只有等子线程自然 timeout 才收敛。
- `Cancel / HangDetector / SoftTimeLimit` 三个终止源没有共享通路：`_cancel_watcher`
  只 pkill 远程 mugen.sh；`HangDetector` 只在命令返回后判 hung，不主动打断当前
  SSH；`SoftTimeLimitExceeded` 只抛在主线程，进不到子线程。挂死 case 依然要等
  case 命令 timeout。
- 独立 TestJob 无 cancel 入口，`cancel_requested` 字段仅由流水线级联设。本次不动，
  列入下一轮。

Pipeline 端还有一个直接可观测的 bug：`_TERMINAL_STATUSES = {succeeded, failed, error}`
未含 `cancelled`，`_worst_wins_run_status` / `compute_execution_status` 用
`s not in _TERMINAL_STATUSES` 判"是否还有活动"→ 用户点完 cancel、RunJob 已经是
终态 `cancelled`，Execution 状态仍显示为 `running`，运维看不到终止事实。

## 决策

### 1. job 级与用例级 `threading.Event` 分级传递（信号层）

`process_test_job` 顶层持有一个 job 级 `cancel_event: threading.Event`，逐层向下传到
`_run_env_set_thread` → `execute_env_set` → `prepare_env / prepare_rerun_env /
prepare_mugen / configure_mugen_node / wait_for_ssh_ready / run_hook / run_case
/ _cancel_watcher`。软超时和 DB 取消汇流到该事件；`run_case` 为每个用例创建独立
事件，供挂死判定使用：

| 源 | 位置 | 触发时机 |
| --- | --- | --- |
| `SoftTimeLimitExceeded` | `process_test_job` 主线程 handler | Celery 15h SIGALRM 到达 |
| DB `cancel_requested` | `process_test_job` watcher 每 15s 轮询 | 用户/流水线 API 设标志后 ≤15s |
| Hang 判定 | `HangDetector.on_hung` 回调 | set 当前 case 的本地事件，不影响 job 级事件 |

`_cancel_check_factory`（原 DB 查询闭包）由 `process_test_job` 的 watcher 使用，
从 `preparing` 起覆盖 VM 创建、环境准备与用例执行；命中后先 `set cancel_event`。
用例运行期间的 `_cancel_watcher` 保留远程 `pkill -f mugen.sh` 职责；若 job 级事件先
杀掉本地 SSH，`run_case` 返回时也会补发远程 pkill。本地 kill 和远程 pkill 都跑，
两条通路互补。

### 2. `run_process` 支持多个终止信号打断本地子进程（执行层）

`backend/app/core/process_runner.py::run_process` 新增可选参数
`cancel_event: threading.Event | None = None` 和附加事件序列。任一事件命中时把
selectors 分片从"整段 remaining"改为 `min(remaining, 2.0)`；每片前判一次 `is_set()`，命中
`process.kill()` + 返回 `ProcessResult(cancelled=True, timed_out=False)`。
`timed_out` 与 `cancelled` **语义分离**：`timed_out` 只表达"步骤自然超时"，
`cancelled` 表达"人为/信号打断"，两者独立置位。`ProcessResult` 与
`RemoteCommandResult` 各加 `cancelled: bool = False` 字段，默认值保持向后兼容。

**为什么是 2 秒**：既能让"点取消到本地 kill"平均 ≤3s（远优于原 12h），又不至于
每 10ms 打一次 `is_set()` 拉高 CPU；与 `_cancel_watcher` 15s DB 轮询周期相比
不引入额外数据库压力。**为什么不用 `selector.register` 一个 self-pipe 立即被
唤醒**：需要额外 fd + 兼容 Windows 分支，收益（≤2s vs 立即）与本次"秒级"目标
不匹配，YAGNI。

### 3. `_run_env_set_thread` 与 `process_test_job` 分别收敛（收敛层）

- **`_run_env_set_thread`** 捕获 `TestJobExecutionError(code="job_cancelled")`
  时**不**调用 `handle_job_execution_error`（避免覆写主线程决定的终态），只做
  本 env_set 局部收敛：剩余 PENDING `case_run.status = NOT_EXECUTED` +
  `cleanup_env_vms(preserve=False)` → return `_EnvSetResult(has_error=False)`。
  VM 清理显式在本分支跑，防止取消中断本 case 后主线程未走 cleanup 的 VM 泄漏。
- **`process_test_job`** 抛弃 `with ThreadPoolExecutor`，改手写：
  `executor = ThreadPoolExecutor(...)` + `try / except / finally`。Soft handler
  顺序固定为 `cancel_event.set() → executor.shutdown(wait=True) →
  handle_job_execution_error`——不再等 `with.__exit__` 阻塞。`finally` 里
  `shutdown(wait=False, cancel_futures=True)` 只兜"提交阶段就异常"的罕见路径。
- **终态决定权归主线程**：`_run_env_set_thread` 不再"抢"标 `TestJob.status`；
  只有主线程 `as_completed` 收完所有 future 后，按 DB `cancel_requested` →
  CANCELLED / Soft 或普通错误 → ERROR 收敛。恢复服务已写入的终态通过行锁和刷新检查
  保留，旧 Worker 不得覆盖。

### 4. HangDetector 新增 `on_hung` 回调（接口扩展）

`HangDetector.__init__` 接受 `on_hung: Callable[[], None] | None = None`，只在
`_hung` 从 False→True 的那一次转换时触发。`run_case` 传入当前 case 的本地事件
`set` 作为 `on_hung`。挂死场景下：detector 判定 → 本地 kill 当前 sshpass → `run_case`
走原 hung 分支（`_capture_and_store_console` + `EnvSetHangError` + 现有自愈计数），
不再等 `CASE_COMMAND_TIMEOUT_SECONDS`。ADR 0016 的自愈语义与非对称
3-set/1-clear 计数**保持不变**。

### 5. 统一错误码 `job_cancelled` 与消息（防漂移）

`mugen_runner._raise_cancelled()` 是模块内私有 helper，把散落在 11 处的
`raise TestJobExecutionError("job_cancelled", "测试任务已取消")` 收敛到一处。
业务码字符串与消息文本单一真源，避免未来 code 或 message 漂移。

### 6. Pipeline 状态聚合把 `cancelled` 视为终态（修 pipeline 显示 bug）

- `_TERMINAL_STATUSES = {succeeded, failed, error, cancelled}`。
- 三处聚合函数（`_worst_wins_run_status` / `compute_execution_status` /
  `_execution_status_from_runs`）统一按 **error > cancelled > failed > succeeded**
  优先级返回。理由：人为截断意味着剩余用例没测完，运维关心"为什么被取消"多于
  "哪个用例红了"；一支 `cancelled` + 其它 `succeeded` 的 Run 若显示 `succeeded`
  会把取消事实藏起来。

### 7. 挂死不进入 job_cancelled 打断链

`hang` 只 set 当前 case 的本地事件，让**当前 case** 的 SSH 命令秒退，`run_case` 里保留
原 `detector.is_hung() → EnvSetHangError` 分支——这样 ADR 0016 自愈计数
（连续 N 次挂死才跳过本 env_set 剩余 case）不受影响；用例结束后本地事件随之废弃，
同一 env_set 的后续 case 和兄弟 env_set 均继续执行。

## 后果

**收益**：

- 主线程 `SoftTimeLimitExceeded` → job 收敛 error(task_timeout) **≤5s**（2s 分片
  × 少量调度）。原来最长可挂住 12h+60s。
- 挂死 → 本 case SSH kill + console 抓取 + EnvSetHangError，取代等 case timeout。
- DB cancel → 端到端 ≤18s（`_cancel_watcher` 15s + 本地 kill ≤3s）。
- Pipeline 看板不再对已取消的 RunJob 显示 "执行中"。
- 一个稳定的错误码 `job_cancelled` 供上层判定（原方案只有 `task_timeout` 混用）。

**代价**：

- `cancel_event: threading.Event | None = None` 参数出现在 ~14 个签名上。若第三
  个 flag 再来（例如 priority class、trace id）应引入 `JobExecutionContext`
  dataclass 收敛（本轮 ponytail：先透传，等有第三个成员再抽）。
- `_cancel_watcher` 与"本地 kill"两条通路并存：pkill 打开新的 SSH 连接、本地
  kill 通过 `subprocess.kill()` 关掉当前的。顺序上先本地 kill + 后 pkill，
  避免"远程 kill 触发本地 SSH EOF 反而先返回，`_cancel_watcher` 卡在下一步"。
  实测两条通路 2 秒内都能收敛。

**明确留下**（下一轮）：

- 独立 TestJob 无 `POST /test-jobs/{id}/cancel` 端点（P1-B）。
- `mugen_exec_command = "docker exec ... mugen.sh"` 场景下 `pkill -f mugen.sh`
  在宿主机看不到容器 PID namespace 里的 mugen.sh，只依赖本地 kill 收敛（P1-C）。
- `handle_job_execution_error` 里 `cleanup_failed_job_envs` 并行兄弟线程可能
  还在跑，导致 SSH 突然失败的次生 error 事件（P2-G）。
- 用例级 `_cancel_watcher` 未 `join`；`cancel_stop.set()` 后 daemon 线程自然退出。
  TestJob 级 watcher 在任务结束时显式 stop 并短暂 join，避免跨任务遗留。

## 不采用的方案

- **用 signal.pthread_kill / os.kill 强杀子线程持有的 SSH 子进程**：需要在多层
  持有 process 引用；`time.sleep`、`threading.Lock`、SQLAlchemy session 内部
  poll 等打断不到；race 复杂，比 selector 分片更易出错。
- **`shutdown(wait=False, cancel_futures=True)` 立即返回主线程**：已 submit
  且 execute_env_set 正在跑的子线程 Python 层不能强杀，会变成孤儿线程继续跑
  直到自然 timeout，期间可能覆写主线程已提交的 `job.status` → `error / cancelled`
  被后续 `case_run.status / env_set.status` 二次改写。
- **`ProcessResult` 不加 `cancelled` 字段，只加 timed_out**：上层无法区分
  "步骤自然 timeout"与"信号打断"，`wait_for_ssh_ready` 看到 timed_out=True 会
  继续下一轮重试，形成忙循环。加字段最小成本消除歧义。
- **`run_process` 用 `cancel_check: Callable[[], bool]` 而非 `Event`**：更灵活，
  但外层循环的 `time.sleep(x)` 无法用 predicate 打断（要 poll 或分片）；而
  `Event.wait(x)` 天然可"秒级醒 + 判返回值"。DB 检查与 event 通过
  `_cancel_watcher` 桥接足够，不必在底层用 predicate。
- **把 `cancel_event` 与 `job` 塞进 `JobExecutionContext` dataclass 全签名改造**：
  影响 30+ 处 `job: TestJob` 参数，评审 diff 巨大，最小改动原则下先透传，等
  第三个此类成员出现再抽。
