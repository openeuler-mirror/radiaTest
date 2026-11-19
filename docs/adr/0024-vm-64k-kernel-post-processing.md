<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0024：VM/物理机/流水线 64k 内核后处理

## 状态

已接受(Accepted)。

## 背景

2403sp4 的 64k page-size 内核用于 update 测试。64k 内核不是独立 qcow2 镜像，而是
从 2403sp4 update repo 装 `kernel-64k` 包 + 重启获得。两种使用场景：

1. **普通 VM 申请**：`os_version` 选 `openEuler-24.03-LTS-SP4-64k`，装完基础 SP4 后从
   最多 5 个 update 轮次中寻找 `kernel-64k`，安装并验证后对外提供 64k VM。手动物理机
   PXE 保持只安装基础镜像，不提供 64k 选项。
2. **update 测试流水线**：VM 与物理机都只测试最新 update 轮；最新轮未提供
   `kernel-64k` 时把当前环境结构化收敛为 `NOT_EXECUTED`，不回退旧轮。

## 决策

### 1. `os_version` 后缀 `-64k` 触发后处理（不新增 DB 字段）

`os_version` 以 `-64k` 结尾表示请求 64k 后处理，但后端只接受代码明确支持的
`openEuler-24.03-LTS-SP4-64k` 与 aarch64 组合。不新增 `Resource`/`TestJob` 字段，复用
`os_version`/`version`；流水线触发、VM 申请和 worker 分层校验。手动物理机 PXE 不暴露
该目标版本。update 流水线保留既有的 x86_64/-64k 组合跳过规则；其他非 aarch64 架构
会在触发前被拒绝。

**`find_image` 对 `-64k` 做 strip**：VM 申请 `os_version=...-64k` 时，`create_vm_request`
用 `os_version.removesuffix("-64k")` 查 base 镜像（无 64k qcow2 镜像），`request.os_version`
保留 `-64k` 供 `apply_kernel_64k` 触发。当前仅 `openEuler-24.03-LTS-SP4-64k` 需要 64k 后处理
（其他版本直接启动），前端只在 2403sp4 base 镜像存在时暴露 `-64k` 选项。

### 2. update repo 轮次来源 = `repodata`，**不是** `image_discovery`

普通申请回退找上一轮 update repo 时，轮次从 `${version}-update.json` 取（值如
`update_20250101`），由 `pipelines/repodata.py:_collect_update_dirs` 解析。新增
`repodata.list_update_dirs(repo_base_url, version)` 返回全量降序列表。普通 VM 申请最多回退
5 轮；update 流水线只检查最新轮，避免用旧内核产生与本轮转测内容不对应的测试结果。

**否决 `image_discovery.discover_images()`**——它枚举的是 qcow2 镜像 round（值如
`round-9`，来自 `iteration/<dist>/<version>/<round>/<arch>/`），与 kernel-64k 所在的
update repo 轮次（`update_YYYYMMDD`）不是一回事。

### 3. 共享核心 `install_kernel_64k_via_ssh` + 两入口

`vms/service.py:install_kernel_64k_via_ssh(os_version, resource, record_event)` 是共享核心：
轮次枚举 → 每轮写 `[openEuler_update_<round>]` repo 文件（`baseurl` 用 dnf 变量 `$basearch`，
不是 `$(arch)`——后者在 Python 写文件时不会被 bash 展开）→ `dnf repoquery` 预检 →
`dnf install -y kernel-64k` → 用 `grub2-set-default` 选择 64k 启动项 → `reboot` → 等 SSH
恢复 → 验证 `getconf PAGESIZE=65536` → 读取 `uname -r` → 记 `kernel_64k_installed`。
事件记录通过 `record_event` 回调由各入口包：

- **VM**（`apply_kernel_64k`）：`record_vm_request_event`（subject_type=vm_request）。
  流水线 `create_env_node_vm` 不再 strip `-64k`，传给 `process_vm_request` → `apply_kernel_64k`
  统一在 VM 创建时装 64k + 重启。
- **物理机**（`pxe_install.apply_kernel_64k_to_physical`）：`_record_event`
  （subject_type=resource, task_type=pxe_install）。

**已删除**：`mugen_runner.apply_pipeline_kernel_64k`（pre_env 后装 64k + 重启的独立逻辑）。
原因：pre_env 后重启 VM 会导致 docker 容器丢失；64k 安装是 VM 创建的原子能力，
应在 pre_env 前完成。环境创建直接返回当前环境的结构化结果，不再搜索全局 TaskEvent 文本
决定是否跳过。

### 4. 回滚语义按场景区分

- **普通 VM 申请**：5 轮全无或安装、启动、页大小验证失败 → `_rollback_just_created_vm`
  （`destroy-vm.sh` + 释放租约 + 软删 resource + `fail_request`）。
- **update 流水线未转测**：最新轮无包不是机器故障；当前 Node、EnvSet、Case 标为
  `NOT_EXECUTED`，Test Job 正常成功，基础 VM/物理机环境保留。
- **物理流水线故障**：repo 查询、安装、默认启动项、SSH 恢复或页大小验证失败 → Node
  `ERROR`、资源 `management_status=disabled`，不运行测试。

### 5. 流水线 64k 信号 = `job.os_version` 以 `-64k` 结尾 + "本周转测检查"跳过

信号统一为 `os_version`/`version` 后缀 `-64k`。`create_env_node_vm` 保留该目标并让
`process_vm_request` 采用“最新轮”策略；`create_env_node_physical` 查找去掉后缀的基础 PXE
镜像，但把原始 Test Job 目标版本传给 `run_pxe_install` Step 6。两种环境只有完成 64k
启动验证后才把 Node 标为 `READY`。

最新轮无包由环境创建直接返回“未转测”，`execute_env_set` 只收敛当前 EnvSet 的 Node 和
Case，不读取其他任务的事件。

builder 阶段 `fetch_update_packages` / `fetch_service_packages` 对 `version` strip `-64k`
再拼 repo URL（repo 服务器无 `-64k` 目录，不 strip 会 404）。

`find_image` 仍对 `-64k` 做 strip（用 base 镜像，决策 1）。

**已删除**：`apply_pipeline_kernel_64k`（mugen_runner.py）和相关辅助函数
（`_log_latest_round_64k_status`、`_mark_64k_not_executed`、`_reboot_and_wait_64k`、
`_wait_for_ssh_unreachable`）。原因：64k 安装统一走 VM 创建的原子能力，
不再在 pre_env 后重复装 + 重启。

### 6. 新增 `vm_openeuler_update_repo_root` 配置

默认 `http://121.36.84.172/repo.openeuler.org`（与 update 流水线 `config_data.repo_base_url`
同源）。`.env.example` + `deploy/server.env.example` 加占位。

### 7. 以实际启动结果作为成功标准

安装包成功不等于已经从 64k 内核启动。系统必须设置默认 64k GRUB 启动项，最多 60 秒确认
SSH 下线、最多 300 秒等待 SSH 恢复，并验证 `getconf PAGESIZE` 精确为 `65536`。成功后
`resource.os_version` 写规范化 64k 目标版本，`resource.kernel_version` 写 `uname -r` 的
真实结果；命中的 update 轮次保留在任务事件中。

## 考虑过的方案

- **用 `image_discovery.discover_images()` 枚举 round 回退**：否决——qcow2 镜像 round（`round-9`）
  与 update repo 轮次（`update_YYYYMMDD`）不同源。
- **新增 `TestJob.kernel_64k` DB 字段**：否决——non-goal 不新增 DB 字段；用 `os_version`
  `-64k` 后缀信号。
- **`config_data["kernel_64k"]` + `/tmp` 哨兵文件**（早期方案）：否决——要求用户额外设
  config 标志、每 env_set 多一次 SSH 查哨兵；改 `version` `-64k` 后缀，用户选版本即触发。
- **流水线 64k 装放 pre_env.sh**：否决——reboot 断 SSH → `run_hook`/`require_success`
  判 hook_failed → env_set ERROR。装+重启改为在 VM 创建时统一走 `apply_kernel_64k` 原子能力，
  pre_env 前就完成。
- **只确认 RPM 安装成功**：否决——无法证明系统实际从 64k 内核启动，会让错误环境进入
  READY 并产生无效测试结果。

## 影响

- `backend/app/core/config.py`：新增 `vm_openeuler_update_repo_root`。
- `backend/app/modules/pipelines/repodata.py`：新增 `list_update_dirs`，`_latest_update_dir`
  重构为复用 `_collect_update_dirs`。
- `backend/app/modules/vms/service.py`：`install_kernel_64k_via_ssh` + `apply_kernel_64k` +
  `_rollback_just_created_vm` + `Kernel64kNotFoundError`；`process_vm_request` create_lease
  后调 `apply_kernel_64k`，except → `_rollback_just_created_vm`；`create_vm_request` 对
  `-64k` `os_version` strip 后查 base 镜像 + 保留 `-64k` 在 `request.os_version`。
- `backend/app/modules/vms/pxe_install.py`：`apply_kernel_64k_to_physical` +
  `_record_event` 加 `error_code`；物理流水线把保留 `-64k` 的 Test Job 目标版本传给
  `run_pxe_install`，Step5 基础系统安装后据此执行 64k 后处理，成功返回后节点才可 `ready`。
- `backend/app/modules/test_management/envs/vm.py`：`create_env_node_vm` 不再 strip `-64k`，
  直接传给 `process_vm_request` → `apply_kernel_64k`。
- `backend/app/modules/test_management/execution.py`：`execute_env_set` 不再调
  `apply_pipeline_kernel_64k`，也不再查全局 TaskEvent 文本；环境创建通过结构化返回值让当前
  EnvSet 收敛为 `NOT_EXECUTED`。
- `backend/app/modules/test_management/frameworks/mugen_runner.py`：**已删除**
  `apply_pipeline_kernel_64k` + `_log_latest_round_64k_status` + `_mark_64k_not_executed` +
  `_reboot_and_wait_64k` + `_wait_for_ssh_unreachable`。`HOOK_TIMEOUT_SECONDS` 1800→3600
  （docker pre_env 10 步累计需 30-40 分钟）。
- `backend/app/modules/pipelines/repodata.py`：`fetch_update_packages` +
  `fetch_service_packages` 对 `version` strip `-64k` 再拼 repo URL。
- `.env.example` + `deploy/server.env.example`：`VM_OPENEULER_UPDATE_REPO_ROOT` 占位。
- 前端：`api/core/pipelines.ts` `KNOWN_VERSIONS` 加 `openEuler-24.03-LTS-SP4-64k`（流水线测试版本可选）；
  `views/virtual-machines/index.vue` `osVersionOptions` 在 2403sp4 base 存在时追加 `-64k` 选项，
  `roundOptions` 对 `-64k` 按 base 版取 round；Test Management API 类型支持环境和节点的
  `not_executed` 状态。
- `CONTEXT.md`：补"64k 内核后处理"核心规则。
- 不改 ADR 0005（VM 生命周期不变式不改，64k 是末尾后处理 hook）/ADR 0032（update
  流水线 pre_env 不变，64k 是 pre_env 后的额外步骤）。
- 64k 成功路径已把默认启动项设置、SSH 重连、页大小和实际内核版本纳入 worker 验证。
