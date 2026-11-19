<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0026：kernel 模块物理机装最新 update 内核

日期: 2026-08-26

## 状态

已采纳。

## 背景

update 流水线的 kernel 模块（`env_type=physical`）跑 LTP 前，`KERNEL_PRE_ENV` 只配 repo + 调参，被测内核一直是 PXE 镜像自带的 GA 内核（ADR 0015 scope 仅含 PXE 重装 + mugen + 结果派发）。但 kernel 模块属 update 流水线，语义=验证 update 仓更新后的包；对 kernel 模块而言被更新的包就是 kernel 本身。测 GA 内核名不副实——直到本轮才第一次提出"kernel 模块该测 update 仓最新内核"。

现有唯一的换内核是 -64k（ADR 0024）：按 `os_version` 后缀触发，VM 创建 + 物理 PXE 时对**所有模块**装 `kernel-64k`，语义是"让环境匹配请求的页大小变体"，与"kernel 模块测最新 4k 内核"是不同意图、不同触发模型。

## 决策

### 1. kernel 模块物理机新增"装最新 update 内核"步骤

`create_env_node_physical`（`envs/physical.py`）在 `run_pxe_install` 成功后、标 READY 前，按 `template.name=="kernel"` 且 `os_version` 不以 `-64k` 结尾触发新函数 `install_latest_kernel_via_ssh`。`-64k` 变体仍走 `run_pxe_install` Step 6 的 64k 路径（ADR 0024），不重复触发。

### 2. 新函数 `install_latest_kernel_via_ssh`，镜像 64k 的 SSH 形态

放 `vms/service.py`，签名 `(*, os_version, resource, record_event)`（不带 `db`——函数内不直接写库，事件经 `record_event` sink 由调用方落库；64k 的 `db` 参数实为死参），失败 `raise LatestKernelInstallError` + 经 `record_event` sink 记事件 + 成功设 `resource.kernel_version`。**不**碰 `management_status`（资源生命周期归调用方，与 64k 一致：64k 也不在函数内标 ERROR，由 `run_pxe_install` except 标）。事件 sink 类型用通用别名 `KernelInstallEventSink`（不复用 64k 专属的 `InstallKernel64kEventSink`）。

机制：`list_update_dirs(repo_base_url=vm_openeuler_update_repo_root)[:1]` 取最新轮 → 写 `[openEuler_update_<round>]` repo → `dnf install -y kernel` → `reboot` → 等 SSH 回来（自包含，不从 64k 抽共享 helper）→ `uname -r` 写 `resource.kernel_version` + 记 `kernel_latest_installed`。4k `kernel` 每轮都有，不枚举多轮 repoquery（64k 才需要找有 kernel-64k 的轮）。reboot 后等 SSH 用**两段独立 deadline**（phase1 等下线 ~60s、phase2 等回来 ~300s），不共用一个 120s——共用会把物理机慢重启（BIOS+内核+sshd）误判为失败；64k 虽共用 120s 但不检查 `ssh_back`、乐观记成功，故掩盖了这个问题。

### 3. 失败回滚（物理机不能销毁）

写 repo / `dnf install` 返回非 0 / reboot 后 SSH 超时不回 / `uname -r` 返回非 0 或空 → 函数各记 `kernel_latest_install_failed`（带 `error_code` 区分：`kernel_latest_no_rounds` / `kernel_latest_dnf_install_failed` / `kernel_latest_ssh_not_back` / `kernel_latest_uname_failed`）+ raise `LatestKernelInstallError`。调用方 `create_env_node_physical` 的 except 标 `resource.management_status=DISABLED`（退出轮转；ADR 0023 复用过滤 `ACTIVE`，故不再被 pkgcmd/pkgserver 复用）+ node `ERROR` + raise `TestJobExecutionError("kernel_install_failed") from exc`。**不**退回测 GA 内核（本模块目的就是测最新内核，装不上还跑等于产出误导性"通过"）。

> 留内核说明：pre-reboot 失败（无轮次 / dnf install 失败）机器留 GA 内核；`ssh_not_back` 路径 reboot 已发，机器可能已切新内核或卡在重启中——`DISABLED` 隔离即可，不保证内核状态。

> `ManagementStatus` 枚举只有 `ACTIVE`/`MAINTENANCE`/`DISABLED`，无 `ERROR` 成员。64k 物理路径 `pxe_install.py:318` 写的是 `ManagementStatus.ERROR.value`（不存在的成员，未被测试覆盖、休眠 bug）。本 ADR 不动 64k 路径，新代码用语义正确的 `DISABLED`。64k 那处另列后续修复。

> SSH 命令层异常（如 `sshpass` 缺失致 `run_ssh_command` 抛 `RemoteCommandError`）属环境配置错误，直接传播、不另包一层（与 64k 一致）；本轮只覆盖上述 4 类返回值/超时失败。

### 4. 事件落 job 事件流，不落 resource 事件流

经 `record_test_job_event` 包成 `record_event` sink，事件落到 job 事件流（run-job 详情可见），比 64k 落 resource 事件流更贴合本场景（由 job 触发的换内核）；`resource.kernel_version` 落资源字段（资源详情/飞书卡片可见）。

### 5. `KERNEL_PRE_ENV` 不动；不与 64k 合并

`KERNEL_PRE_ENV` 原样保留 `UPDATE_REPO_SETUP`（pre_env 里照常换源）。那点"换内核时写最小 repo + pre_env 又跑全套 `UPDATE_REPO_SETUP`"是 64k 既有的同款幂等模式，不是新 wart，VM 用例完全不受影响。

不与 64k 合并：64k 是"按版本后缀匹配页大小变体"（VM 创建 + 物理 PXE，所有模块），最新 4k 是"kernel 模块测最新内核"（kernel 模块、物理）。意图/触发不同，合并会把 64k 的版本后缀触发与最新 4k 的模块触发混在一起，且让非 kernel 模块 -64k 失去自动装 64k 内核（回归）。

## 不采用

- **把 `UPDATE_REPO_SETUP` 从 `KERNEL_PRE_ENV` 拿掉、改成"换内核前设一次源"**：会让"设源"成 kernel-swap 专属模式，非换内核的 VM 用例（docker/pkgmanage/pkgcmd-vm/pkgserver-vm 普通版本）无 pre-mugen 换内核阶段承载设源，模式推广不了，把 kernel 搞成特殊 case，破坏"设源统一在 pre_env"模型。否决。
- **单函数 `swap_kernel` 把 64k 当特殊 case 合并**：64k 触发是版本后缀、对所有模块生效（VM 创建 + 物理 PXE）；最新 4k 触发是 kernel 模块。合并会让非 kernel 模块 -64k 失去自动装 64k 内核（行为回归），或把两种触发硬塞一个函数（漏抽象）。否决——共享底层 mechanic 但不合并入口/触发（见决策 2，新函数自包含，不动 64k）。
- **换内核写进 `KERNEL_PRE_ENV`**：reboot 断 SSH → mugen hook_failed（ADR 0024 已否决同类方案）。
- **装失败退回测 GA 内核**：产出误导性"通过"结果，违背本模块目的。
- **`kernel_version` 记标记不读 uname**：64k 不读 uname 的理由是"避免 reboot 后轮询 SSH"，但本函数本来就要等 SSH 回来，等回来后跑一条 `uname -r` 近乎零成本且能记真实内核。故读真实 uname。

## 影响

- `backend/app/modules/vms/service.py`：新增 `install_latest_kernel_via_ssh` + `LatestKernelInstallError`。
- `backend/app/modules/test_management/envs/physical.py`：`create_env_node_physical` 加 kernel 模块触发 + except 失败回滚。
- `backend/tests/test_vms.py`：加 `install_latest_kernel_via_ssh` 5 测试（成功 / dnf install 失败 / 无轮次 / SSH 不回含 deadline / uname 失败）。
- `backend/tests/test_physical_env.py`：加 kernel 链 helper + 4 编排测试（触发 / 非 kernel 跳过 / -64k 跳过 / 失败回滚）。
- `docs/spec/0003-test-pipeline.md` §8.2.2：kernel 模块行为补"装最新 update 内核"步骤。
- 不改 64k 路径（VM/物理）、不改其它模块 pre_env、不改 `KERNEL_PRE_ENV`。
