<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: kernel 模块物理机装最新 update 内核

## 状态（2026-09-04 归档）

静态实现+单测+审计已完成（`4ad8dfd` 起，`install_latest_kernel_via_ssh` + `LatestKernelInstallError` +
`create_env_node_physical` 触发/回滚覆盖，`test_vms.py`/`test_physical_env.py` 断言齐）。2026-09-04 用户反馈：
"C 组我们已经测试过很多 kernel update 的了，是没问题的"——覆盖 `kernel_latest_installed` 事件 + `resource.kernel_version` + 失败回滚 DISABLED + 64k 不触发四条。MR 审查以 main merge commit 为代理。

## 目标

update 流水线 kernel 模块（`env_type=physical`）跑 LTP 前，从 update repo 装最新 `kernel` + 重启 + 用新内核跑，使 kernel 模块真正验证 update 仓更新后的内核（而非 GA 镜像内核）。

## 范围

- 新增 `install_latest_kernel_via_ssh` + `LatestKernelInstallError`（`vms/service.py`），镜像 64k 的 SSH 形态，自包含（不动 64k）。
- `create_env_node_physical`（`envs/physical.py`）加触发：`run_pxe_install` 成功后、标 READY 前，按 `template.name=="kernel"` 且 `os_version` 不以 `-64k` 结尾调用；except 失败回滚（标 `management_status=ERROR` + node `ERROR` + raise `TestJobExecutionError("kernel_install_failed")`）。
- 单测覆盖触发编排与失败回滚（`tests/test_physical_env.py` 既有风格）。

## 非目标

- 不动 64k 路径（VM 创建 + 物理 PXE，ADR 0024）。
- 不动其它模块 pre_env、不动 `KERNEL_PRE_ENV`（保留 `UPDATE_REPO_SETUP`）。
- 不与 64k 合并函数入口/触发（意图与触发模型不同，见 ADR 0026）。
- 不加 grubby / page-size 验证硬化（scope 控制，与 64k 推迟 T6 同理）。
- 不改前端（kernel 模块已有 ltp 结果展示；`resource.kernel_version` 已有字段与展示）。

## 确认决策（grilling 对齐）

- **Q1 目标**：kernel 模块属 update 流水线，跑 LTP 前装最新 update repo `kernel` + 重启 + 跑，而非测 GA 内核。
- **Q2 机制/触发**：新增物理机 SSH 函数，在 `create_env_node_physical` 里 `run_pxe_install` 成功后、标 READY 前调；触发 `template.name=="kernel"` 且非 `-64k`；`-64k` 走 `run_pxe_install` Step 6 不重复。
- **Q3 抽象边界**：不与 64k 合并——64k 是"按版本后缀匹配页大小变体"（VM 创建+物理 PXE，所有模块），最新 4k 是"kernel 模块测最新内核"（kernel 模块、物理）。各走各的，新函数自包含、不从 64k 抽 helper。
- **Q4 repo 源**：新函数自己写最小 repo（`list_update_dirs(repo_base_url=vm_openeuler_update_repo_root)[:1]` 最新轮 → `[openEuler_update_<round>]`）→ `dnf install -y kernel` → `reboot` → 等 SSH。`KERNEL_PRE_ENV` 原样不动，VM 用例不受影响。
- **Q5 失败回滚**：装失败/reboot-SSH 不回 → 标 `resource.management_status=DISABLED` + node `ERROR` + raise `TestJobExecutionError("kernel_install_failed")` + 留 GA 内核，不退回测 GA 内核；标 DISABLED 也让 ADR 0023 的 pkgcmd/pkgserver physical 不复用这台。
- **Q6 kernel_version**：reboot-wait 确认 SSH 回来后跑 `uname -r` 写真实内核版本进 `resource.kernel_version` + 记 `kernel_latest_installed`；不加 grubby 硬化。

## 任务

- [x] 文档：ADR 0026 + spec 0003 §8.2.2 更新（文档先行）
- [x] T1 `install_latest_kernel_via_ssh` + `LatestKernelInstallError`（TDD：成功路径写 repo→install→reboot→uname→kernel_version+installed 事件；失败路径 dnf install 失败→failed 事件+raise）
- [x] T2 `create_env_node_physical` 触发编排 + 失败回滚（TDD：kernel+非-64k 触发+成功→READY；非 kernel 跳过；-64k kernel 跳过；失败→ERROR+raise）
- [ ] 验证：`./scripts/check.sh all` + dev 触发 update 流水线选 kernel → PXE → 装最新内核+reboot → LTP → 结果页；失败路径验证

## 验证命令与验收场景

- 静态：`./scripts/check.sh backend`（ruff + compileall + pytest）。
- 全量：`./scripts/check.sh all`。
- 验收场景：
  1. dev 触发 update 流水线选 kernel（非 -64k 版本）→ 物理机 PXE 重装 → 自动装最新 update 内核 + reboot → mugen LTP → run-job 详情见 `kernel_latest_installed` 事件 + `resource.kernel_version` 为真实 uname。
  2. 失败路径：模拟 `dnf install kernel` 失败 → node `ERROR` + `resource.management_status=ERROR` + `TestJobExecutionError("kernel_install_failed")` + 不跑 LTP。
  3. -64k 版本选 kernel → 走 64k 路径，不重复触发本步骤。

## 进度

- [x] Clarify（grilling Q1–Q6 对齐）
- [x] Architect（codebase-design：深模块 `install_latest_kernel_via_ssh`，复用既有 test_management→vms seam，不新增抽象）
- [x] Elaborate（ADR 0026 + spec 0003 §8.2.2 + 本 plan）
- [x] Solve（TDD T1→T2，13 新/相关测试全绿）
- [x] Audit（独立 reviewer 两轮：第一轮发现 2 major + 文档漂移；第二轮确认全 FIXED、Audit clear）
- [x] Reconcile（neat-freak：code/ADR/spec/plan 一致；AGENTS.md 规范执行审计通过；README doc-index 既存漂移另列待拍板）
- [ ] 验证：dev 远程部署端到端（静态全绿：414 passed/1 skipped + ruff + scripts/docs；dev 触发 update 流水线选 kernel → PXE → 装最新内核+reboot → LTP → 结果页；失败路径）—— 需在远程 dev 执行，本轮工作站不可达

## 发现

- `ManagementStatus` 枚举只有 ACTIVE/MAINTENANCE/DISABLED，无 ERROR 成员。新代码失败标 `DISABLED`（退出轮转，ADR 0023 复用过滤 ACTIVE 故不复用）。
- 64k 物理路径 `pxe_install.py:318` 写的是 `ManagementStatus.ERROR.value`（不存在的成员，未被测试覆盖、休眠 bug）。本轮不动 64k，另列后续修复。
- Audit 发现：reboot-wait 原拟共用 120s deadline（同 64k），但本函数检查 `ssh_back` 会让慢物理重启被误判 DISABLED → 改两段独立 deadline（phase1 等下线 ~60s、phase2 等回来 ~300s）。补 3 个失败路径测试（no_rounds / ssh_not_back 含 deadline 时间 mock / uname_failed），函数共 5 测试。
- SSH 命令层 raise（如 sshpass 缺失）不另包一层（与 64k 同），ADR §3 已注明；本轮只覆盖返回值/超时 4 类失败。

## 未决问题

- 实跑若发现 grub 未切默认内核（`uname -r` 仍是旧内核），单列后续硬化，不在本轮加 grubby。
