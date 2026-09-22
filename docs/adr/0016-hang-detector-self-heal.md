<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0016：HangDetector 从"不可逆判死"改为"可自愈（非对称 3-set/1-clear）"

日期: 2026-07-27

## 状态

已采纳。

## 背景

2026-07-25 的 kernel-test 流水线，`oe_test_ltp` 被标记为 `vm_hang`（"VM/物理机挂死（心跳连续失败）"），但物理机从未挂死、从未重启。

实锤（见 `mem:test-pipeline/vm-hang-false-positive`）：LTP 的 `cpuset_memory_pressure` 用例触发 OOM（杀的是 LTP 自己的进程，非 sshd），约 4 分钟的内存抖动让 SSH `echo ok` 心跳连续 3 次 10s 超时。`HangDetector._run`（`hang_detector.py:28-43`）在连续 3 次失败后置 `self._hung = True` 并 **`return`**（线程退出、永不复位）。case 命令在 7h1m 超时后，`run_case` 的 `finally`（`mugen_runner.py:527`）检查 `detector.is_hung()` 仍为 True，于是走 vm_hang 早退路径（`mugen_runner.py:531`）抢先 raise `EnvSetHangError`，把"命令超时"误贴成"机器挂死"，并连带跳过本 env_set 剩余 case。

根因不是机器挂死，是**心跳不可逆**：短暂 SSH 抖动一旦凑够 3 次失败就永久判死，之后机器恢复也无法翻案。

## 决策

### 1. HangDetector 可自愈，非对称门槛

`HangDetector._run` 去掉 `_hung = True` 之后的 `return`，线程不再退出，继续每 `interval`（30s）检查；检测到一次"活"（`check_fn()` 返回 True）即清 `self._hung = False`。

门槛**非对称**：
- **5 次连续失败才 set**（`max_failures=3`→`5`，2026-08-15 调宽）——高负载 VM（如 sssd 测试期间）sshd 响应慢，3 次 10s 超时（90s 窗口）太激进。5 次 30s 超时加心跳间隔（约 300s 窗口）给 sshd 更多恢复时间。同时 `HEARTBEAT_TIMEOUT_SECONDS` 从 10s 提到 30s。
- **1 次成功就 clear**（新增）——`echo ok` 返回 0 即此刻确实活着，标"非 hung"是对的，快速翻案。

### 2. 不采用：vm_hang 与命令超时的显式解耦规则

曾考虑加规则"命令超时（`result.timed_out`）时优先走 task_timeout、别让 vm_hang 抢先"。

不采用。推演：
- **短暂抖动（如 OOM 4 分钟）**：自愈后心跳恢复，`finally` 时 `is_hung()=False` → 自然走到 `result.timed_out` 的 task_timeout/remote_command_failed 路径（`mugen_runner.py:546+`）。**自愈已把误贴修掉，不需要额外规则。**
- **真挂死（机器一直没活到 case 结束）**：`finally` 时 `is_hung()=True` 且命令也超时 → vm_hang 抢先触发。**这是对的**——机器真死了，该标 vm_hang 而非 task_timeout。当前"`if hung` 抢先"结构在此反而正确。
  > **推演前提已由 [ADR 0031](0031-termination-convergence.md) §决策 4/§7 改变**：
  > 挂死现在通过 `HangDetector.on_hung` 立即 `cancel_event.set()` → 本地
  > `run_process` selectors 2s 分片 kill sshpass，命令**不再自然 timeout**
  > （`result.cancelled=True, result.timed_out=False`）。但"vm_hang 抢先"
  > 结论仍成立（`hung` 分支仍在 `if result.cancelled` 之前判断）；决策本身
  > 不反转，只更新推演路径。见本文 §关联。

显式解耦规则在两种情形下都不增加正确性，无 observed failure 背书，纯加 complexity，违背最小实现原则。不做。

## 后果

- 短暂 SSH 抖动（OOM/内存压力/CPU 饱和）不再误判 vm_hang；4 分钟级别的抖动过后约 30s 内即翻案。
- 真挂死（机器持续无响应到 `finally`）照样 `is_hung()=True` → vm_hang 照常触发，**不漏报**。
- `is_hung()` 语义从"曾经连续失败过"变为"当前是否处于失败态"——`run_case` 的 `finally` 读取的是此刻状态。`run_case` 的 `finally` 结构不动，行为自然正确。
- 同步配套：case 超时从 7h 调宽到 12h、job 总预算 8h→15h（让 LTP 真能跑完，见 `docs/plans/active/vm-hang-false-positive-fix.md`）；kernel 流水线默认只选 `oe_test_ltp`（`oe_test_posix` 摘出默认，留 mugen 索引供手动测试任务勾选）。
- 不在范围：物理机 BMC/IPMI 第二信源 + console 采集落地（独立立项）；vm_hang 与命令超时解耦（本 ADR 决策 2 不采用）；物理机时钟/NTP（见 `mem:infra/physical-clock-drift`，用户定"只记不改"）。

### 3. vm_hang 不再 break 整个 env_set，改为 catch + continue + 熔断

2026-08-15 新增。原行为：`execute_env_set` 捕获 `EnvSetHangError` 后把剩余 case 全标 ERROR 并 break。导致 sssd 用例一时吃满资源触发 vm_hang 后，后续 20+ 个无关用例全被跳过。

**新行为**：
- `EnvSetHangError`：当前用例已被 `run_case` 标 ERROR，`execute_env_set` 不再标全部剩余，改为计数 +1，`continue` 到下一个用例。
- `RemoteCommandError`（SSH 连不上）：同理，标 ERROR + 计数 +1，`continue`。
- 用例正常完成时重置计数为 0。
- **熔断**：连续 3 个 vm_hang/RemoteCommandError（VM 真死场景，每个浪费 ~10s SSH 超时）后，剩余用例标 ERROR + break。避免 20 个用例浪费 200s。
- `run_hook`（pre_env/post_env）的 `RemoteCommandError` 不在 case 循环 catch 范围内，仍向上传播终止 TestJob。

不采用：vm_hang 后等 VM 恢复再继续——无法确定恢复时间，且等待会拖慢整体执行。直接试下一个用例，让 HangDetector 自愈机制和 SSH ConnectTimeout 自然处理。

## 关联

- 实锤与排查：`mem:test-pipeline/vm-hang-false-positive`
- 执行计划：`docs/plans/active/vm-hang-false-positive-fix.md`
- 前序 kernel 流水线：[ADR 0015](./0015-kernel-module-envtype-physical-reinstall-result-dispatch.md)
- **接口扩展**（2026-09-03，[ADR 0031](./0031-termination-convergence.md)）：
  `HangDetector.__init__` 新增 `on_hung: Callable[[], None] | None = None`；挂死
  判定从 False→True 转换时触发一次，用于 set 当前 case 的本地终止信号并打断 SSH
  命令，取代"等 case 自然 timeout 才发现挂死"。该信号不会取消 TestJob。自愈计数与非对称
  3-set/1-clear 语义不变；`is_hung()=True` 抢先标 `vm_hang` 的规则也不变。
