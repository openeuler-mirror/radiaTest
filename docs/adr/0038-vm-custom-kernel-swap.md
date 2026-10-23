<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0038：VM 申请支持创建时换指定内核

日期: 2026-09-01

## 状态

已采纳。

## 背景

VM 申请表单原有"内核版本"字段是死接线：前端有输入框但 `buildVMRequestPayload` 未提交，
后端 `VMRequest.kernel_version` 仅作展示属性，从未触发换内核。现有唯一的换内核是 `-64k`
（ADR 0024）：按 `os_version` 后缀触发，对所有模块装 `kernel-64k`，语义是"让环境匹配页
大小变体"。用户要的是"创建时换上指定版本的内核"（如 6.18），来源 dailybuild 仓库，与
`-64k` 是不同意图、不同触发模型。

## 决策

### 1. 改造 `kernel_version` 字段为换内核能力，新增两字段

`VMRequest` 新增 `kernel_variant`（变体段，如 `26.09-with-kernel-6.18`）+ `kernel_rpm_url`
（兜底 URL）两字段，二选一非空触发换内核；都空则不换（VM 用装机镜像默认内核）。`kernel_version`
复用为"换内核成功后 `uname -r` 真实值"的展示字段。不复用单一字段存 URL——URL 与版本号语义
不同，混用会丢失"用户当初指定哪个内核"的请求凭证，且 URL 长度远超 128。

### 2. dual-path：变体下拉 + URL 兜底，共用同一 SSH 安装原子

变体路径（主）：选定 OS 版本+轮次+架构后，系统枚举 dailybuild 该轮次下 `*-with-kernel-*`
子目录下拉选；从变体段解析版本前缀，拼 dailybuild repo baseurl，SSH `repoquery` 找精确 NVR。
URL 路径（兜底）：手填完整 RPM URL，系统推断其所在 `Packages/` 上一级为 repo baseurl，
从文件名解析 NVR（跳过 repoquery）。两路径汇入同一 `install_custom_kernel_via_ssh`：写
`[local-kernel]` repo → 精确 `dnf install kernel-<NVR>` → reboot → 等 SSH → `uname -r` 比对。

dailybuild 路径规律普适（`EBS-<dist>/<round>/<变体>/everything/<arch>/`），变体段可枚举、
轮次段等于表单 `image_round`，故变体路径能省到"选一个下拉"；非 dailybuild 标准结构或自编译
发布站走 URL 兜底，覆盖任意来源。

### 3. 与 `-64k` 互斥，显式优先

`process_vm_request` 的 `create_lease` 后、`SUCCEEDED` 前加 `_apply_post_create_kernel` 调度：
有 `kernel_variant`/`kernel_rpm_url` → `apply_custom_kernel`；否则 `os_version` 以 `-64k`
结尾 → 现有 `apply_kernel_64k`；都没有则不换。不叠加——两者目的不同（指定版本内核 vs 页大小
变体），同一 VM 不需要先装 64k 再换指定内核。

### 4. 失败销毁回滚，原子性优先

换内核全失败（repo 不可达 / 包不存在 / `dnf install` 失败 / reboot 后 `uname` 不匹配）复用
`_rollback_just_created_vm`（destroy-vm + 释放租约 + 软删 resource + fail_request），与
`-64k` 一致。不留"默认内核的半成品 VM"——用户要的是换好内核的 VM，原子性意味着要么得到、
要么什么都没有。

### 5. `uname -r` 判定 + 写真实版本

`dnf install` 返回 0 ≠ 换内核成功——grub 可能仍切旧内核。唯一硬证据是 reboot 后 SSH 回来
跑 `uname -r` 显示新版本（与变体/URL 解析的版本串匹配）。等 SSH 回来这一步本就省不掉（不等
就标 SUCCEEDED，用户 SSH 进去可能还没启动完），顺手 `uname` 零额外成本，成功后真实值写入
`resource.kernel_version`。`uname` 仍是旧内核 → 判失败 → 销毁重建。

### 6. 按版本前缀精确匹配包，避开同名非真内核陷阱

变体 repo 里可能混入同名非真内核包（如 `kernel-26.2.5.21`）。直接 `dnf install kernel`
会取版本号最高的、装错。必须从变体段（`with-kernel-6.18` → `6.18`）提取版本前缀，
`repoquery 'kernel-6.18.*'` 精确匹配，或 URL 路径从文件名解析 NVR，`dnf install kernel-<NVR>`。

### 7. 提交前预检

`submit_vm_request` 在 `create_vm_request` 前调 `precheck_custom_kernel`：变体路径 HTTP 验证
repo `repomd.xml` 可达 + 下载 `primary.xml.zst` 解析确认 `kernel-<前缀>.*` 存在；URL 路径
HEAD 验证 RPM URL 可达 + 推断 repo 可达。失败拒绝创建（400），避免浪费 VM 创建资源在
创建时才发现 repo 不可达/包不存在。包名精确查询发生在 install 时 SSH `repoquery`（VM 已建），
预检只兜底"提交瞬间可达"。

## 后果

- VM 申请表单"内核版本"输入框改造为"内核变体"下拉 + "内核 RPM URL"兜底输入，二选一互斥。
- 新增 `GET /vm-images/kernel-variants` 枚举 API + `vm_dailybuild_repo_root` 配置。
- 换内核失败 = 整个 VM 申请失败重来（与 `-64k` 一致），失败率高时浪费 VM 创建资源——可接受，
  原子性优先。
- dailybuild 仓库不可达时变体下拉为空，用户走 URL 兜底。

## 不采用

- **本地 RPM 上传**（SCP 传 VM + `dnf install /tmp/kernel-*.rpm`）：留作后续扩展，本次仅两
  类远程来源。kernel 主包依赖是基础包（VM 已有），单包可装，本地路径技术上可行但本次不做。
- **`kernel-devel`/`headers` 等额外包**：验证 `kernel-6.18.40` 主包自带所有 `kmod(*.ko)`
  模块，只换主包即得完整可启动内核。
- **与 `-64k` 合并**：意图/触发不同，合并会让 `-64k` 的版本后缀触发与本特性的显式指定混在
  一起，且让 `-64k` 失去自动行为。
