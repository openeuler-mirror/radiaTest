<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0030: RunJob 取消功能

> **部分被 [ADR 0031](0031-termination-convergence.md) 取代**：本文档"检查点"
> 与"远程进程清理"两节的原方案（"新开 SSH 执行 `pkill -f mugen.sh`，远程进程
> 退出后本地 SSH 自然返回"、"不直接 `process.kill()` 本地 SSH 子进程"）已被
> ADR 0031 的 job 级 `cancel_event` + `run_process` 本地 kill + selectors 2s
> 分片方案取代。状态机、权限、`cancelled/cancelling` 语义与 API 端点仍然有效，
> 且 ADR 0031 补齐了原方案未覆盖的 4 个场景（15h 软超时打不断并行子线程、
> 挂死时不主动终止、准备阶段无 cancel 检查、pipeline 看板 `cancelled` 状态
> 被误当作非终态）。

## 上下文

Pipeline RunJob 触发后最长运行 15 小时（`TEST_JOB_TIMEOUT`），用户无法主动中
止。长用例（如 12 小时 pkgmanage）一旦启动只能等结束或超时。需要一个取消机
制让 ADMIN 能在运行中中止 RunJob。

## 决策

### 状态机

RunJob 新增 `cancelled` 终止状态；已开始准备或执行时经由中间态 `cancelling`：

```
running → cancelling → cancelled
```

`cancel_requested` 布尔标志独立于 `status`。API 对 `pending` 任务直接改为
`cancelled`，不创建 TestJob；对 `preparing`/`running` 任务设标志并改为
`cancelling`，worker 在创建 TestJob 前、创建后执行前和执行结束后检查标志，最终改
`cancelled`。分离请求与执行让用户知道"已受理"，并覆盖准备阶段的并发取消。

TestJob 同步标 `cancelled`，保持 RunJob 和 TestJob 状态一致。

### 检查点

三级检测：

1. **用例执行期间**：复用 `HangDetector` 心跳线程（已每 30 秒轮询），加并行
   cancel 检查。命中后新开 SSH 执行 `pkill -f mugen.sh`，远程进程退出后本地
   SSH 自然返回。**先 kill 远程再等本地退出**——顺序不能反，否则丢失 SSH 通
   道无法清理远程进程。
   > **已被 [ADR 0031](0031-termination-convergence.md) §1/§决策 5 反转**：
   > 现在改为**先** `set cancel_event` 让本地 `run_process` selectors 分片 ≤2s
   > kill sshpass 子进程 **再** 新开 SSH `pkill -f mugen.sh` 释放远程资源，两条
   > 通路并行；本地 kill 是主保证，pkill 是补充。
2. **用例间**：`execute_env_set` 的 case 循环每次迭代前检查。
3. **环境集间**：外层循环每次调用 `execute_env_set` 前检查。

### 远程进程清理

不直接 `process.kill()` 本地 SSH 子进程。改为：新开 SSH → `pkill -f mugen.sh`
→ 远程 mugen 退出 → 本地 SSH 收到 EOF 自然返回。比强制 kill 更干净，不留
孤儿进程。

> **已被 [ADR 0031 §决策 2](0031-termination-convergence.md) 反转**：本地
> `run_process(cancel_event=...)` 的 selectors 分片 ≤2s 会主动 `process.kill()`
> 本地 sshpass 子进程并返回 `cancelled=True`；远程 pkill 保留但降为次要通路。
> 反转原因是"新开 SSH pkill"在 docker-namespace / 挂死机器 / 12h case command
> 场景下不够快或不够可靠。

### 环境清理

复用 `cleanup_failed_job_envs`：VM 销毁，物理机保持占用。不释放物理机租约
——物理机生命周期归调用方，与现有失败/挂死处理一致。

> **补充**：[ADR 0031 §决策 3](0031-termination-convergence.md) 新增 `run_case`
> 内"本地被 cancel_event 打断"分支的收敛：`_run_env_set_thread` 捕获
> `job_cancelled` 时**直接调 `cleanup_env_vms(preserve=False)`**，不再依赖
> 主线程的 `cleanup_failed_job_envs`——避免兄弟 env_set 打断时主线程走
> CANCELLED 收敛路径不进入 cleanup 循环的 VM 泄漏。

### 权限

ADMIN only，与手动重装物理机、销毁环境等操作一致。

### 边界

非 `running`/`preparing`/`pending` 状态的 RunJob 拒绝取消，返回 409。`pending`
取消不进入 `cancelling`，已终止的 RunJob 取消无意义。

## 不采用方案

- **Celery `revoke(terminate=True)`**：直接杀 ForkPoolWorker 进程。虽然能用
  新加的 `task_id` 列，但太重——杀掉整个 worker 进程，远程 mugen 可能成孤
  儿，且无法做远程清理。
- **改 `run_process` selector 循环**：传入 `cancel_check` 回调。能秒级响应但
  改了底层公用函数，影响面太大。
  > **已被 [ADR 0031 §决策 2](0031-termination-convergence.md) 采纳，且改用
  > `cancel_event: threading.Event`（而非原候选的 predicate 参数）**，理由：
  > 外层 `wait_for_ssh_ready` / `configure_mugen_node` 需要 `event.wait(x)`
  > 让 `time.sleep` 也秒级被打断，predicate 做不到。
- **新增 `cancelled` 用例状态**：用例级别不值得新增枚举，复用 `not_executed`
  足够。
- **幂等键**：`UPDATE SET cancel_requested=True` 天然幂等，不需要额外机制。
