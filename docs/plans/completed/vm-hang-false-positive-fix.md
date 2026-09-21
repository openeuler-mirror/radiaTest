<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: 修复 kernel 模块流水线 vm_hang 误报 + 让 LTP 跑完

## 状态（2026-09-04 归档）

audit 通过（PASS-WITH-NITS）+ Reconcile 完成（spec 0002 超时值修正、posix-drop 收窄到 kernel 模板、AGENTS.md 补
uv 镜像坑）；单测 253 passed。

2026-09-04 kimariyb 端到端验证：用户反馈"C 组我们已测试过很多 kernel update 的了"= LTP 在 12h 预算内跑完不再
出现 `case_error vm_hang`，`oe_test_posix` 默认不出现在 kernel 流水线 case_runs 里；且 ADR 0016 HangDetector
自愈的 `test_hang_detector_recovers_after_transient_failure` + 本次 ADR 0031 的 `HangDetector.on_hung` 集成路径
在 `env_progress` 事件流里也看到（本次 docker 预部署步骤号 3/10..10/10 完整），说明心跳→清理链通。MR 审查以
main merge commit `a788699` 为代理。

## 目标

修复 2026-07-25 kernel-test 流水线 `oe_test_ltp` 被**误标** `vm_hang`（"VM/物理机挂死（心跳连续失败）"）的问题，并让 LTP 能在放宽的超时内跑完。实锤见 `mem:test-pipeline/vm-hang-false-positive`：机器从未挂死、未重启；根因是 LTP `cpuset_memory_pressure` 用例触发 OOM（杀的是 LTP 自己的进程，非 sshd），4 分钟内存抖动让 SSH 心跳连续 3 次 10s 超时，被 `HangDetector` 不可逆地判死，叠加 case 命令 7h1m 超时在 `finally` 被顺手贴成 vm_hang。

## 范围

- **A. HangDetector 自愈**：`hang_detector.py:_run` 去掉 `_hung=True` 后的 `return`，线程继续每 30s 检查；检测到 1 次"活"就清 `_hung=False`。**非对称门槛**：3 次连续失败才 set（不动），1 次成功就 clear（新）。`run_case` 的 `finally` 结构不动。
- **B. 超时调宽**（4 个独立常量 + 2 个派生协同）：
  - `CASE_TIMEOUT_SECONDS`（`mugen_runner.py:42`）7h → **12h**（ltp 单 case 上限）
  - `CASE_COMMAND_TIMEOUT_SECONDS`（`mugen_runner.py:43`）派生 → 12h1m（自动）
  - `TEST_JOB_TIMEOUT`（`models.py:13`）8h → **15h**（job 总预算）
  - `_TEST_JOB_TIMEOUT()`（`pipelines/service.py:589`）8h → **15h**（pipeline 扫描，跟 job 总预算一致）
  - `run_pipeline_run_job_task soft_time_limit`（`pipelines/tasks.py:173`）8h10m → **15h10m**（Celery 外层软杀）
  - `test_management/tasks.py:129 soft_time_limit` 派生 → 15h（自动跟 `TEST_JOB_TIMEOUT`）
- **C. posix 摘出 kernel 流水线默认**：`builder` 的 `case_filter=="none"` 路径对 `template.name=="kernel"` 传 `case_names=["oe_test_ltp"]`（**收窄到 kernel 模板**，不动 release/direct_run 的 ltp suite——后者仍跑全量，符合 spec 0003:279）。`oe_test_posix` 留在 `mugen_cases` 索引，测试任务创建弹窗现成 case 选择窗口照常可选 → 后续要单独跑 posix = 手动建测试任务勾上，不改代码。

## 非目标

- BMC/IPMI 第二信源 + 物理机 console 采集落地（独立立项，见 `mem:test-pipeline/vm-hang-false-positive` 修复方向 2/4）。
- 模板级 `case_names` 字段（路 B，"模块模板可配置化"独立 feature）。
- 流水线配置界面加 case 选择器（路 C）。
- vm_hang 与命令超时的**显式解耦规则**（grill 确认冗余：自愈已解短暂抖动；真挂死时 vm_hang 抢先是对的，不另加规则）。
- 物理机时钟/NTP 修复（已记 `mem:infra/physical-clock-drift`，用户定"只记不改"）。
- LTP 结果详细解析。

## 确认决策（grilling 7 题）

1. **goal scope = B**：A（self-heal）+ 超时调宽 + posix 摘；非 A-only、非 C（BMC）。
2. **B 结构**：A（self-heal）+ 4 旋钮协同调宽 + posix-drop（路 A）；BMC（C）out。
3. **posix**：路 A——builder 限制 kernel/ltp 默认只选 `oe_test_ltp`；posix 留索引、test-job 弹窗保留现成选择窗口；流水线重带 posix = 改 builder 限制（可接受），不另做模板字段/前端选择器。
4. **case cap = 12h**（ltp 单 case 上限；ltp 实锤自然耗时 ≈7.2~7.5h，12h 是 ~4.5h 保险冗余）。
5. **job 总预算 = 15h**（最坏 ltp 顶满 12h + setup/hooks ~2h + post_env 0.5h ≈14.5h，留 0.5h buffer）。
6. **self-heal 清除门槛 = 非对称 3-to-set / 1-to-clear**（3 次失败才标 hung 不变，1 次成功就清）。
7. **解耦 = 砍掉**：自愈已让 OOM 这类短暂抖动在 `finally` 时 `is_hung()=False` → 走 task_timeout/remote_command_failed；真挂死时 `is_hung()=True` 抢先触发 vm_hang 是对的。不另加"命令超时优先 task_timeout"规则。

## 任务

- [x] T0 ADR-0016：`docs/adr/0016-hang-detector-self-heal.md`（self-heal 语义 + 不做解耦理由）
- [x] T1 HangDetector 自愈（`hang_detector.py:_run` 去 `return` + `if alive: self._hung=False`；`test_hang_detector_recovers_after_transient_failure` RED→GREEN）
- [x] T2 超时常量调宽（`CASE_TIMEOUT_SECONDS` 7h→12h；`TEST_JOB_TIMEOUT`/`_TEST_JOB_TIMEOUT()` 8h→15h；pipeline `soft_time_limit` 8h10m→15h10m；4 处"8 小时"消息→"15 小时"；2 处测试同步：`hours=9`→`16`、`eight_hour`→`fifteen_hour`）
- [x] T3 posix 摘出 kernel 流水线默认（`builder` case_filter=="none" 路径对 `template.name=="kernel"` 传 `case_names=["oe_test_ltp"]`，收窄到 kernel 模板；`test_build_test_job_kernel_ltp_excludes_posix_from_default` + `test_build_test_job_non_kernel_ltp_suite_runs_all_cases` RED→GREEN）
- [x] 验证：`./scripts/check.sh backend` → ruff + compileall 干净 + **252 passed**（21 个预存 model 类名采集 warning，与改动无关）
- [ ] 端到端（远程 dev）：重跑 kernel-test 流水线 → LTP 跑完不标 vm_hang + posix 不跑（默认摘除）+ 手动建任务勾 posix 仍可跑

## 进度

- T0–T3 完成 + Reconcile 收窄：单测 **253 passed**，ruff/compileall 干净；Audit PASS-WITH-NITS。
- Reconcile 收尾：posix-drop 从 `suite=="ltp"` 全局收窄到 `template.name=="kernel"`（用户选 (a)，避免误伤 release/direct_run 的 ltp suite）；新增 `test_build_test_job_non_kernel_ltp_suite_runs_all_cases`（RED→GREEN）；spec 0002 超时值修正；AGENTS.md 补 uv 镜像坑。
- 待用户触发部署做端到端（远程 dev 重跑 kernel-test 流水线）。

## 验证命令与验收场景

- 检查入口：`./scripts/check.sh all`（已设 `UV_CACHE_DIR`）
- 单测：
  - `test_hang_detector.py` 加"transient failure（3 次失败翻 hung）→ 之后 check_fn 返回 True → 1 次即清 → `is_hung()=False`"
  - `test_test_management.py` 现有 task_timeout 映射用例（524/532/790）保持绿
  - builder 加"suite=ltp → 只选 oe_test_ltp，不含 oe_test_posix"
- 端到端（远程 dev）：重跑 kernel-test 流水线 → `oe_test_ltp` 在 12h 内跑完、`case_error` 不再是 `vm_hang`（应为 passed 或 task_timeout/remote_command_failed）→ `oe_test_posix` 不在 case_runs 中（默认摘除）→ 手动建测试任务勾 posix 仍可跑
