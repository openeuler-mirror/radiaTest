<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: 物理机 PXE 安装改造 — 本地 OS 树安装源 + 内核换装 + 可靠性加固

## 状态

active（grill 已对齐 + 已完成实现，待 dev 实测后按实测结论收敛）。

## 目标

修正/取代 `vm-pxe-iso-install.md` 的"ISO 下载挂载"路线：物理机 PXE 安装的**安装源一律使用 94 本地 OS 树**（radiaTest 成熟模式），不再向 94 下载整份 ISO；内核差异收敛为"装后换内核（swap）"；并修复 PXE 调试中定位的可靠性缺陷（错 arch、假成功、多网卡 DHCP、列表慢）。同时让未来的"两个内核变体都可直装"天然成立。

## 背景与问题（详见 `docs/pxe-install-debug-issues.md`）

- 现状 `run_pxe_install`：置 maintenance → PXE 服务器跑 `pxe-install.sh`（ISO 分支下载/挂载整份 ISO，指向 121.36.84.172）→ ipmitool PXE → `_wait_for_ssh`（只探 SSH）→ 回写 os_version。实测问题：
  1. 选错 arch 镜像（x86 机用 grubaa64）→ PXE 引导失败，回退老盘；且列表不按 arch 过滤、触发不校验。
  2. 假成功：老系统 root 密码与默认相同 → `_wait_for_ssh` 误判，os_version 被写成目标版本，无实际重装。
  3. 只能绑定单一 `resource.mac_address`，dhcpd 无动态池/全局 filename，多网卡机启动网卡未绑 → 引导下载不到 → 回退老盘。
  4. 26GB ISO 从 121.36 下载落 94（污染磁盘）；用户红线：**不得向 94 下载大 ISO**。
  5. `GET /install-images` 冷缓存同步全扫 dailybuild（~44s），前端重装弹窗"暂无数据"。
- radiaTest 参考：`i_mirroring.location` 直接登记 94 本地 OS 树；PXE 只 rsync `location/images/pxeboot/`（vmlinuz/initrd）到 tftp，kickstart `url --url=<location>` 边装边从本地树拉 RPM——**无整包下载、无外网**。
- 94 本地现状：rc3 DevStation 只有 k6.6 的 OS 树（pxeboot/repodata/EFI 齐全）；k6.18 只有 ISO、无 OS 树/k6.18 everything repo。DevStation 6.18 靶的交付方式 = 装 6.6 基础 + 换内核。

## 范围

- 安装源模型：RC 镜像按 `(round, variant)` 登记**本地 OS 树** `repo_url` + `efi_url`（复用 `physical_install_images` 现有字段）；变体有自己的树 → 直接装该树；无树变体 → `repo_url=基础树` + 装后 swap。
- 可配置基础变体：新表 `install_image_base_variants`（`os_version → base_kernel_variant`），前端 ADMIN 可编辑；seed 默认 DevStation→6.6 + 扫描时单树自动建议。
- arch 防线：前端按机器架构过滤列表；后端 `POST /resources/{id}/install` 校验 `image.arch == resource.arch`（不符 400）。
- 假成功防线：装机后校验 `os-release` 与 `image.os_version` 匹配 + KS `%post` 写 round 标记回读对比 + swap 后 `uname -r`；不符 → `pxe_failed`、恢复 active、不回写 os_version。
- swap 集成：`run_pxe_install` Step6 与 64k 并列，复用 `install_custom_kernel_via_ssh`（变体 repo=dailybuild `EBS-<os>/<round>/with-kernel-<ver>/everything/<arch>/`）；失败宽容（保留基础系统可用、active、事件/日志注明来源）。
- DHCP 多网卡：装机前 SSH 采集目标机全部网卡 MAC，`pxe-install.sh` 全部绑定同一 IP+引导文件，清残留绑定；采集失败退化主 MAC。
- 列表接口不阻塞：`GET /install-images` 先返回 DB 已有行；dailybuild 发现与本地登记在后台异步刷新（短缓存）。
- 前端重装弹窗：版本→轮次→内核三级；按机器架构过滤；轮次只列有安装源的；徽标 `[本地直装]` / `[装<base>+换内核]`；无源灰显禁触发；base 映射编辑入口；swap 来源明细只在任务日志展示。
- `pxe-install.sh`：ISO 分支停用（仅保留手工兜底能力），官方分支（repo_url+efi_url）成为装机主路径。

## 非目标

- 不在 94 上同步/构建新镜像内容（94 镜像同步属镜像侧 infra，本计划只消费已有的本地 OS 树；k6.18 everything repo 不本地化，swap 走 121.36）。
- 不改 VM 创建/PEB 相关流程。
- 不引入新的远程 PXE 服务器（仍为 PXE 服务器资源，当前 = 94 的 PXE/DHCP/tftp/httpd）。
- 不强制"每个变体都可直装"——取决于本地树是否已同步；未同步即禁触发。
- 不新增大文件轮询/下载的后台任务：dailybuild 发现与本地登记在列表接口以
  **进程内后台线程**刷新（≤5 分钟节流）；部署时同步仍走 Celery/CLI seed。
- 历史 ISO 下载缓存（`/var/cache/kronos-iso` 软链）为调试期临时手段，随实现下线。

## 确认决策（grill 结论）

1. 安装源 = 本地 OS 树；按 `(round, variant)` 登记，有树直装、无树"基础树+swap"（Q1/Q4）。
2. 换内核在目标机内做，repo 走 121.36 增量（小 RPM），94 不参与、不落大文件（Q2，用户红线）。
3. 复用 `physical_install_images.repo_url/efi_url`，本地扫描登记；缺本地源禁触发（Q3-A）。
4. 基础变体映射：**前端可配**小表 `install_image_base_variants`；seed 默认 DevStation→6.6 + 单树自动建议（grill 补充）。
5. 前后端 arch 双防线（前端过滤 + 后端硬校验 400）。
6. 装机后 os-release + round 标记 + swap uname 三重校验，不符不回写 os_version。
7. swap 失败宽容：保留基础系统可用、资源 active、事件/日志注明来源。
8. DHCP 多网卡：装机前全 MAC 采集 + 全绑。
9. 列表接口先返回 + 后台刷新（消除 44s 阻塞）。
10. 徽标 `[本地直装]`/`[装<base>+换内核]`；轮次只列有源；swap 来源仅日志可见。
11. 6.18 = 装 6.6 基础 + 换内核（用户定调）；新版本若两变体都有树则各自直装，天然成立。

## 任务

- [ ] T0 数据模型与迁移：新表 `install_image_base_variants` + Alembic + schema + 前端可配接口（GET/PUT）；seed 默认 DevStation→6.6。
- [ ] T1 本地源登记：`seed-rc-install-images`/列表刷新扫描 94 `iteration.repo`，按 `(round, variant)` 探测 OS 树 → 写 `repo_url/efi_url`；无树变体登记"基础树+swap"标记；缺基树 → 禁触发。
- [ ] T2 后端 arch 校验：`POST /resources/{id}/install` 校验 `image.arch==resource.arch` → 400。
- [ ] T3 `GET /install-images` 不阻塞：先返回 DB 行；dailybuild 发现 + 本地登记走后台刷新（短缓存）；修复冷缓存 44s。
- [ ] T4 `run_pxe_install`：装后校验 os-release 匹配 + round 标记回读（KS `%post` 写 `/root/.kronos-install-marker`） + swap 变体调 `install_custom_kernel_via_ssh`（失败宽容策略：保留基础、active、事件注明）；不再依赖 ISO 分支。
- [ ] T5 `pxe-install.sh`：装机前采集全部网卡 MAC 并全绑（同 IP+引导文件，清残留）；official 分支为主；ISO 分支停用。
- [ ] T6 前端：重装弹窗三级选择按机器 arch 过滤、轮次只列有源、徽标 `[本地直装]`/`[装<base>+换内核]`、无源禁触发；base 映射编辑 UI。
- [ ] T7 ADR：记录安装源模型（本地 OS 树 + swap，不下载 ISO，radiaTest 参照）与 64k/custom-kernel swap 失败策略；标注取代 `vm-pxe-iso-install.md` 的 ISO 下载路线。
- [ ] T8 文档同步：产出行为/API/权限验收标准同步到 `docs/spec/`；CONTEXT 如需。
- [ ] T9 TDD + `./scripts/check.sh` + 部署 dev + 端到端验收（见下）。

## 验证命令与验收场景

- 检查入口：`./scripts/check.sh`。
- TDD：arch 校验 / os-release+round 校验 / swap 失败宽容 / DHCP 多 MAC 绑定 / 列表秒回 / 前端徽标与禁触发。
- 端到端（71，x86_64）：
  1. rc3 k6.6：选 6.6 → `[本地直装]`，走本地 OS 树装成，os-release 含 26.09，round 标记匹配，资源 active。
  2. rc3 k6.18：选 6.18 → `[装6.6+换内核]`，装 6.6 后 swap 到 6.18，`uname -r` 匹配；swap 源在任务日志可见。
  3. 选 arch 不符（人为构造）→ 前端不展示 + 后端 400。
  4. 老系统不装成：`os-release` 不符 → `pxe_failed`、os_version 保持旧值。
  5. 多网卡：从非主 MAC 的网卡 PXE 也能拿到引导（DHCP 全绑）。
  6. `GET /install-images` 冷缓存 ≤ 几秒返回；轮次只列有源。
- 回归：official（24.03-SP4 等，efi+repo）PXE 安装行为不变。

## 风险

- **swap 依赖 121.36 dailybuild**：外部不可达时换内核失败（宽容降级为 6.6 可用），需日志明确提示。
- **本地树覆盖不全**：未同步轮次/变体 → 该行不可装（符合红线，但需 UI 清晰提示，避免"为啥没这个版本"）。
- **多网卡全绑**：dhcpd host 块增多/同 IP 多 MAC，需避免残留冲突（脚本清残留）；采集要在旧系统 SSH 还通时完成。
- **base 映射误改**：UI 编辑 + seed 默认 + 必存校验，防止把基础配成无树的变体。
- **71 实机未知**：grub.cfg 相对路径/引导细节可能仍要调——先写计划、实机调通后回改计划再实现（本轮流程约定）。