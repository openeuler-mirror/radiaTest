<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0040：物理机 PXE 安装改用本地 OS 树源 + 内核差异转"装后换内核"

日期: 2026-09-05

## 状态

已采纳。

## 背景

物理机 PXE 安装此前区分 official（efi_url+repo_url，mugen 本地 OS 树）与 ISO
（下载 dailybuild 整份 DVD ISO 到 PXE 服务器再挂载作源）两种模式。开发版
（26.09-DevStation 等）走 ISO 模式，实测存在系列问题（见
`docs/pxe-install-debug-issues.md`）：

- 整份 26GB ISO 从 `121.36.84.172` 下载落 PXE 服务器（94），磁盘占用大；
  环境约束要求**不得向 94 下载大 ISO**（可接受目标机/网络上小文件拉取）。
- `GET /install-images` 冷缓存时同步全扫 dailybuild（~44s），前端"暂无数据"。
- 镜像列表不按 arch 过滤且触发不校验，选错 arch 镜像 → PXE 引导失败回退老盘。
- `_wait_for_ssh` 只探 SSH，老系统 root 密码与默认相同会被误判"装机成功"。
- DHCP 只绑单一 `resource.mac_address`，多网卡机启动网卡未绑则拿不到引导。

radiaTest（成熟参照）做法：`i_mirroring.location` 直接登记本地 OS 树；PXE 只 rsync
`location/images/pxeboot/`（vmlinuz/initrd）到 PXE 服务器 tftp，kickstart
`url --url=<location>` 边装边从本地 OS 树拉 RPM——**无整包下载、无外网**。

## 决策

### 1. 安装源统一为本地 OS 树；ISO 下载退役

`pxe-install.sh` 优先走 official 分支（`efi_url`+`repo_url` 齐全时），ISO/mount
分支仅作本地兜底（也只用已有本地 ISO，不下载）。`physical_install_images.repo_url`
由登记扫描回填 94 本地 `iteration.repo/<os>/<round>/<variant>/OS/<arch>/`。

### 2. 按变体登记 ± swap 兜底

本地源登记按 `(round, variant)` 探测 94 是否有该变体的 OS 树：
- 变体自身树存在 → 该变体行 `repo_url` 指自己的树，直装，`swap_kernel_variant=NULL`；
- 变体自身树缺失 → `repo_url=base 变体树` + `swap_kernel_variant=变体目录全名`
  （先装基础，装完换内核到该变体）；
- **变体目录在本地 round 中整体缺失**（连 ISO/repo 目录都没有）→ 无法确定 swap
  目标变体名，**不登记**（不可装），以免被误标为"本地直装"；
- base 树缺失 → 该行不登记（前端禁触发）。
换内核复用既有 `install_custom_kernel_via_ssh`（ADR 0038）的变体路径，repo 走
dailybuild（`EBS-<os>/<round>/<variant>/everything/<arch>/`），仅小 RPM，符合"不向
94 落大文件"约束。`base 变体` 存新表 `install_image_base_variants`（os_version→kver），
前端 ADMIN 可编辑，seed 默认 DevStation→6.6。

### 3. 重装后校验，防假成功

`_wait_for_ssh` 通过后、回写凭据/os_version 前，校验：
- `os-release` 含目标版本号（区分旧系统，如 22.03 vs 26.09）；
- RC 轮次标记 `/root/.kronos-install-marker`（kickstart %post 写入
  `<os_version> <round>`）与镜像一致；
- swap 变体由 `install_custom_kernel_via_ssh` 以 `uname -r` 校验。
任一项不符 → `pxe_failed`，恢复 active，**不回写 os_version**。

### 4. 换内核失败宽容（区别于 VM 的原子回滚）

ADR 0038 对 VM 采用"失败销毁回滚"；物理机换内核失败（repo 不可达/包缺失/重启后
内核不符）采用**宽容**策略：保留基础系统（如 k6.6）可用，资源恢复 active，
`os_version` 记基础发行版，事件写明"换内核未完成"。理由：物理机 PXE 装出的基础
系统脱机可用，DISABLE 一台健康机器浪费资源；VM 无此选择（申请失败需回收）。

### 5. docker 多网络卡全绑

装机前（旧系统仍 SSH 可达）采集 `/sys/class/net/*/address` 全部 MAC，
`pxe-install.sh` 将同一 IP+引导文件绑到**全部网卡**；采集失败退化主 MAC。

### 6. 镜像目录列表不阻塞请求

`GET /install-images` 先返回 DB 已有行；dailybuild 发现 + 本地登记在
后台线程刷新（进程内 ≤5 分钟节流），列表不再被 40+ 秒同步扫描拖住。

## 不采用的方案

- **继续整份 ISO 下载/挂载安装**：污染 94 磁盘、依赖外网、无复用缓存收益。
- **自动判断"唯一有树的变体为基础"**：多个变体都有树时无法唯一确定；基础变体
  用显式配置（前端口维护），清晰、可迁移、不随本地镜像状态漂移。
- **VM 式"换内核失败即销毁回滚"**：物理机基础系统可用，宽容更合适（见第 4 节）。