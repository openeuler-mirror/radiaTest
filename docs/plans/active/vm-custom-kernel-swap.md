<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: VM 申请支持创建时换指定内核

## 状态

active。

## 目标

把 VM 申请表单的"内核版本"字段从无用的展示属性，改造为"创建时自动换指定内核"
的原子能力。选定 OS 版本 + 轮次 + 架构后，申请人可二选一：

1. **下拉选内核变体**（主路径，dailybuild 来源）：系统枚举该轮次目录下
   `*-with-kernel-*` 子目录（如 `26.09-with-kernel-6.18` / `...-6.6`），
   申请人下拉选一个变体；系统拼出同目录 repo、按变体段版本前缀精确匹配
   `kernel-*` 包并 `dnf install`。
2. **手填 RPM URL 兜底**（任意来源）：申请人填一个 `kernel-*.rpm` 完整 URL；
   系统推断其所在 `Packages/` 上一级为 repo baseurl，配 repo 后
   `dnf install kernel-<NVR>`。

两条路径都走同一个"换内核"原子能力：配 repo → 精确装 kernel 主包 → reboot →
等 SSH 回来 → `uname -r` 验证新内核生效 → 真实版本写入 `resource.kernel_version`。
换内核失败即整个 VM 申请失败（销毁刚建的 VM），与现有 `-64k` 后处理语义一致。

## 背景（已验证事实）

- `kernel_version` 当前是 `String(128)` 展示属性；前端表单有输入框但
  `buildVMRequestPayload` 未把它发到后端，属于死接线。
- dailybuild 路径规律普适：`http://<host>/dailybuild/EBS-<dist>/<round>/<变体段>/everything/<arch>/`。
  其中 `EBS-` 前缀普适（20.03~26.09 全这格式），`<round>` = 表单 `image_round`，
  `<arch>` = 表单 `arch`，可从已选字段推断；变体段（`<ver>-with-kernel-<kver>`）
  可枚举。
- 验证样本 `kernel-6.18.40-0.0.0.14.oe2609` 主包**自带所有 `kmod(*.ko)`**（内核模块
  打包在主包内，无独立 `kernel-modules` 包），`requires` 仅 `dracut`/`grubby`/
  `initscripts`/`linux-firmware`/`module-init-tools`/`/bin/sh`——全是 VM 装好就有的
  基础包。故只装 kernel 主包即得完整可启动内核。
- **坑**：变体 repo 里可能混入同名非真内核包（如 `kernel-26.2.5.21`）。直接
  `dnf install kernel` 会取版本号最高的、可能装错。必须按变体段版本前缀
  （`with-kernel-6.18` → `6.18`）或 URL 的 NVR 精确匹配 `kernel-<前缀>.*`。

## 范围

- **A. 数据模型**：`VMRequest` 新增 `kernel_variant`（变体段，`String(128)`）+
  `kernel_rpm_url`（兜底 URL，`String(2048)`），二选一非空触发换内核；
  `Resource.kernel_version` 复用为"换内核成功后 `uname -r` 真实值"展示字段。
- **B. 输入与变体枚举**：前端在选定 OS 版本 + 轮次 + 架构后异步加载变体下拉；
  新增后端枚举 API（`dist + round + arch` → 该轮次下 `*-with-kernel-*` 变体列表，
  顺带返回各变体 repoquery 到的 `kernel-<版本>.*` 包名，选变体即知包是否存在）；
  保留"手填 RPM URL"开关作为兜底输入。两条路径前端互斥（选了变体清空 URL，反之亦然）。
  下拉默认空选项 = "不换内核"，`kernel_variant` 与 `kernel_rpm_url` 都空时不触发换内核，
  VM 用装机镜像自带默认内核。
- **C. 提交前预检**：`submit_vm_request` 在 `create_vm_request` 前校验——变体路径
  验证 repo 可达 + `repoquery` 确认 `kernel-<前缀>.*` 存在；URL 路径 HEAD 验证
  RPM 可达 + 推断 repo 的 `repodata/repomd.xml` 可达。预检失败拒绝创建并提示，
  避免浪费 VM 创建资源。
- **D. 换内核后处理 service**：新写 `apply_custom_kernel`，委托一个共享 SSH 安装
  函数 `install_custom_kernel_via_ssh`：推断 repo baseurl → 写 `[local-kernel]` repo
  文件 → `dnf clean` + `makecache` → 精确 `dnf install kernel-<NVR>` → `reboot`
  → 等 SSH down/up 回来 → `uname -r` 比对预期版本串。
- **E. 流程编排**：`process_vm_request` 复用现有 `-64k` 插入点（`create_lease`
  后、`request.status=SUCCEEDED` 前），新写互斥调度：`request.kernel_variant` 或
  `request.kernel_rpm_url` 非空 → 调 `apply_custom_kernel`；否则 `os_version`
  以 `-64k` 结尾 → 调现有 `apply_kernel_64k`；都没有 → 不换。
- **F. 失败回滚**：换内核全失败（repo 不可达 / 包不存在 / dnf install 失败 /
  reboot 后 `uname -r` 仍是旧内核）→ 复用 `_rollback_just_created_vm`
  （destroy-vm.sh + 释放租约 + 软删 resource + fail_request），与 `-64k` 一致。
- **G. 事件流**：`VMRequest` 事件流记录换内核全程——成功
  `kernel_custom_installed`（来源变体段/URL + `uname -r` 结果）；失败按阶段记
  `kernel_custom_repo_unreachable` / `kernel_custom_not_found` /
  `kernel_custom_install_failed` / `kernel_custom_boot_mismatch`，与现有
  `kernel_64k_*` 事件模式对齐。
- **H. 配置**：新增 `vm_dailybuild_repo_root`（默认
  `http://121.36.84.172/dailybuild`，与 `vm_openeuler_update_repo_root` 同机不同根），
  写入 `.env.example` / `server.env.example` 占位 + compose 默认值。

## 非目标

- 不改物理机换内核（那是 PXE + `install_latest_kernel_via_ssh`，独立流程）。
- 不做"换内核 URL/变体历史收藏"（YAGNI，未要求）。
- 只换 `kernel` 主包（已验证自带 `kmod(*.ko)` 模块），不额外装 `kernel-devel`/
  `kernel-headers`/`kernel-source` 等。
- 不做轮询、通知、后台 worker、定时器；换内核是 VM 创建流程内同步步骤。
- 不改 `-64k` 既有逻辑（仅互斥调度，不改 `apply_kernel_64k` 本身）。
- 不改 `kernel_version` 在资源页/飞书卡片的展示位置（仍是展示字段，只是值来源
  变为换内核成功后的 `uname -r`）。
- 不支持本地 RPM 文件来源（上传/指定本地路径），可扩展为：本地 RPM 经 SCP 传到
  VM 后 `dnf install /tmp/kernel-*.rpm`（kernel 主包依赖是基础包、VM 已有，单包
  可装）。本次仅支持变体下拉 + RPM URL 两类远程来源。

## 确认决策（grilling 5 题 + 追加 2 点）

1. **安装机制**：从变体段/URL 推断同目录 repo baseurl，配成 `[local-kernel]`
   repo，按变体段版本前缀（`with-kernel-6.18` → `6.18`）或 URL 的 NVR 精确匹配
   `kernel-*` 包，`dnf install` 装该主包。避开同名非真内核包（如 `kernel-26.2.5.21`）。
2. **输入形态**：下拉选变体（dailybuild，系统枚举）为主 + 手填 RPM URL 兜底
   （任意来源），两条路径共用同一换内核原子能力。
3. **触发/互斥/插入点**：复用 `-64k` 插入点（`create_lease` 后、`SUCCEEDED` 前）；
   用户显式选变体/填 URL → 走新 `apply_custom_kernel`，跳过 `-64k`；否则
   `os_version` 带 `-64k` → 走 `-64k`；都没有 → 不换。
4. **失败回滚**：换内核全失败（含 reboot 后 `uname` 不匹配）= VM 创建失败，
   复用 `_rollback_just_created_vm` 销毁重建，与 `-64k` 一致。原子性优先，不留半成品 VM。
5. **成功判定 + 展示值**：成功 = `dnf install` 完成 → reboot → SSH 回来 →
   `uname -r` 显示新版本（匹配变体/URL 解析的版本串）；成功后 `uname -r` 真实值
   写入 `Resource.kernel_version`。`uname -r` 还是旧内核 → 判失败 → 销毁重建。
6. **事件流追溯（追加）**：换内核来源（变体段/URL）+ 结果（`uname -r`）全程记入
   `VMRequest` 事件流，与 `kernel_64k_*` 模式对齐。
7. **提交前预检（追加）**：`submit_vm_request` 在创建前校验 repo 可达 + kernel 包
   存在，预检失败拒绝创建并提示。

## 任务

- [ ] T0 数据模型迁移：`VMRequest` 新增 `kernel_variant` / `kernel_rpm_url` 两字段
  + Alembic 迁移；`VMRequestCreate` schema 增两字段（`kernel_rpm_url` 校验
  http/https + `.rpm` 结尾）；`serialize_vm_request` 透传。
- [ ] T1 变体发现：新写 `list_kernel_variants(dist, round, arch)` 解析 dailybuild
  轮次目录下列出 `*-with-kernel-*` 子目录 + 对每个变体 repoquery 取
  `kernel-<前缀>.*` 包名；新增 `GET` 枚举 API。
- [ ] T2 预检：`submit_vm_request` 创建前调预检（变体路径 repo 可达 + 包存在；
  URL 路径 RPM HEAD 可达 + 推断 repo `repomd.xml` 可达），失败 raise 业务错误。
- [ ] T3 `apply_custom_kernel` service + 共享 `install_custom_kernel_via_ssh`
  （推断 repo + 写 repo 文件 + 精确 `dnf install kernel-<NVR>` + reboot + 等 SSH +
  `uname -r` 比对预期版本串 + 事件回调）。
- [ ] T4 `process_vm_request` 互斥调度（显式换内核优先 / 否则 -64k / 都无则不换）+
  失败 `except` → `_rollback_just_created_vm` + 事件流。
- [ ] T5 前端：改造"内核版本"输入为"内核 RPM URL" + 变体下拉（依赖 OS 版本+轮次+
  架构选定后异步加载）+ 手填 URL 开关兜底 + 两条路径互斥；`buildVMRequestPayload`
  补 `kernel_variant` / `kernel_rpm_url`。
- [ ] T6 配置：`vm_dailybuild_repo_root` + `.env.example` / `server.env.example` /
  `docker-compose.server.yml` 默认值。
- [ ] T7 TDD + `./scripts/check.sh all` + Audit（`/code-review` + `/neat-freak`，用户触发）。
- [ ] T8 部署 dev + 端到端（真实变体 + 真实 URL 各跑一次，验 `uname -r` 生效）。

## 进度

- T0–T7 完成：TDD 9 测试绿（install 变体/URL、schema 校验、互斥调度、变体发现、预检×3、install_failed）；`./scripts/check.sh` backend（437 passed）+ frontend（67 passed）全绿，ruff/eslint/vue-tsc/oxfmt 全绿。
- Audit（code-review）修复：`install_custom_kernel_via_ssh` 的 `dnf install` returncode 原未检查（直接 reboot）→ 补 `kernel_custom_install_failed` 事件 + raise 不 reboot；补 `kernel_custom_repo_unreachable`（repoquery returncode 检查）；修 stale docstring。
- 顺手修了 d5d61bb 引入的 9 个 pre-existing 测试失败（write_remote_file fake 签名 + `dnf install` 命令匹配 + env test os_version setup），check.sh 从 9 失败降到 0。
- 待 T8 部署 dev 端到端实测。

## 验证命令与验收场景

- 检查入口：`./scripts/check.sh all`。
- TDD：变体发现 / 预检两路径 / `install_custom_kernel_via_ssh` mock（推断 repo +
  精确匹配包 + dnf install + reboot + uname 判定）/ 互斥调度 / 失败回滚 / 事件流。
- 验收场景：
  1. 选 OS 版本+轮次+架构，下拉选 6.18 变体，提交 → VM 创建 → 换 6.18 内核 →
     `uname -r` 显示 `6.18.40-...`，`resource.kernel_version` 为真实版本。
  2. 手填 RPM URL → VM 创建 → 推断同目录 repo → 换内核 → `uname -r` 验证。
  3. 变体 repo 不可达 / kernel 包不存在 → 预检拒绝创建并提示，不进入 VM 创建。
  4. 换内核后 `uname -r` 仍是旧内核（grub 没切过去）→ 判失败 → 销毁重建 +
     `kernel_custom_boot_mismatch` 事件。
  5. `os_version` 带 `-64k` 且不填换内核 → 走现有 `-64k` 后处理（兼容不回归）。
