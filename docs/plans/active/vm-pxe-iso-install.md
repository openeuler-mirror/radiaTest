<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: 物理机 PXE 安装支持 ISO 源 + 重装页签三级级联

## 状态

active。

## 目标

radiaTest 物理机 PXE 安装支持 ISO 源（dailybuild 开发版如 26.09-DevStation），
覆盖只有 DVD ISO、没 official `OS/EFI` 树的版本；现有 official PXE 安装不受影响。

重装页签从单下拉升级为三级级联（版本→轮次→内核变体）按发行版分组，区分
RC 多轮次 + 多内核（6.6/6.18），避免混乱。

## 背景

- radiaTest 物理机 PXE 用 official `OS/EFI/BOOT/grubaa64.efi` + `OS/` 树
  （mugen mirror `official.repo`）。26.09-DevStation 等开发版没 official OS 树
  （mugen `official.repo`/`mugen.mirror` 均 404），只在 dailybuild 有 DVD ISO +
  变体 everything/repo。
- radiatest 用 milestone + IMirroring(ISO) + Repo + machine_group manager PXE，
  能装开发版（从 ISO 取引导 + 挂 ISO 作源）。
- radiaTest `physical_install_images`（efi_url+repo_url）不支持 ISO 源 → 选不了
  开发版；重装页签单下拉，RC 多轮次多内核会混乱。
- dailybuild `EBS-openEuler-26.09-DevStation/<round>/<变体>/ISO/aarch64/` 下有
  按内核变体分开的 DVD ISO：6.18 变体 `openEuler-26.09-DevStation-...-dvd.iso`，
  6.6 变体 `openEuler-26.09-...-dvd.iso`（名不含 DevStation）。

## 范围

- **A. 数据模型**：`physical_install_images` 加 `round`（release=official/null）+
  `iso_url`（nullable）+ `kernel_variant`（nullable，RC=6.18/6.6，release=null）+
  Alembic 迁移 + schema + serialize。现有 49 行 official 加 round=official。
- **B. 触发分支**：`run_pxe_install` 按 `if image.iso_url` → ISO 模式；`else` →
  现有 official（efi+repo，一字不动）。
- **C. pxe-install.sh ISO 分支**：缓存 ISO（key=os_version+round+kernel_variant+
  arch，N=3 自动删旧）→ loop mount 到 `/var/www/html/iso/<task>/` → 从挂载点提取
  `grubaa64.efi` 放 TFTP + 绑 DHCP（同现有）→ kickstart repo 指向
  `http://<pxe>/iso/<task>/` → finally umount（无论成败）；ISO 文件缓存保留。
  多架构按 key+挂载 task 级隔离。
- **D. 失败处理**：复用现有 PXE 错误语义（标 `management_status=ERROR` + 退出
  轮转 + raise `TestJobExecutionError`）+ pxe-install.sh finally umount 挂载点。
- **E. kickstart 模板**：同模板 + repo 变量（official=repo_url，ISO=挂载点 HTTP），
  不维护两套。
- **F. 前端三级级联**：版本下拉（按 os_version 发行版前缀分组）→ 轮次下拉
  （RC 多轮次，release=official）→ 内核变体下拉（RC 6.18/6.6，release 隐藏/official）。
  `GET /install-images` 返回 round+iso_url+kernel_variant。
- **G. ISO 缓存清理**：每 (os_version, arch) 保留最新 N 轮次（N=3 可配），新 ISO
  下载后自动删超 N 的旧 ISO。

## 非目标

- 不加 `type` 字段（按 os_version 前缀分组发行版，不区分 release/dev）。
- 不改现有 official PXE 路径（else 分支，24.03-LTS-SP4 等行为不变）。
- 不引入新依赖。
- 不做 PXE 之外的安装方式（仍走 PXE 引导，ISO 只作引导源+安装源）。
- 不自动发现 dailybuild 轮次（ADMIN 手动 seed `physical_install_images`）。
- 不改 VM 创建流程（本计划仅物理机 PXE 重装）。

## 确认决策（grilling 6 题）

1. **RC 选轮次**：`physical_install_images` 加 `round`，RC 每轮次一行
   （round=rc3_openeuler-...），release round=official。用户能选特定轮次。
2. **两级级联+按发行版分组**（升级为三级后内核变体）：版本下拉按 os_version
   发行版前缀分组（openEuler-26.09 / openEuler-24.03-LTS），不加 type 字段。
3. **ISO 缓存 N 轮次自动**：每 (os_version, arch) 保留最新 3 轮次 ISO，超 N 删旧，
   新下载后自动触发。
4. **多架构隔离**：iso_url 按 (os_version, arch, round, kernel_variant) 行天然隔离；
   缓存 key 含 arch；挂载点 task 级独立。
5. **内核变体三级级联**：`physical_install_images` 加 `kernel_variant`，前端版本→
   轮次→内核变体三级。RC 有第三级（6.18/6.6），release 隐藏。
6. **6.18 安装部署后调试**：6.6 内核 26.09 可正常装；6.18 安装过程界面不同可能遇
   困难，先按方案开发，部署 dev 后实测 6.18 再调试（grubaa64.efi 引导/kickstart
   兼容可能需调）。

## 任务

- [ ] T0 数据模型迁移：`physical_install_images` 加 round/iso_url/kernel_variant
  三字段 + Alembic 迁移 + schema 校验 + serialize 透传。现有 official 行 round=official。
- [ ] T1 `run_pxe_install` 触发分支：`if image.iso_url` → 构造 ISO 模式
  PXEInstallPayload（iso_url + round + kernel_variant）；else 现有 efi+repo。
- [ ] T2 `pxe-install.sh` ISO 分支：ISO 缓存（下载+按 key 命名+N=3 清理）+ loop
  mount 到 HTTP 路径 + 提取 grubaa64.efi 放 TFTP + kickstart repo 指向挂载 + 绑 DHCP
  + finally umount。现有 official 分支不动。
- [ ] T3 kickstart 模板：repo 变量化（official=repo_url，ISO=挂载 HTTP），同模板。
- [ ] T4 前端三级级联：版本下拉（按发行版前缀分组）→ 轮次下拉 → 内核变体下拉
  （RC 6.18/6.6，release 隐藏）+ API 改造（返回 round+iso_url+kernel_variant）。
- [ ] T5 配置：ISO 缓存路径 + N 轮次（默认3）+ dailybuild 相关配置入 .env.example/
  server.env.example/compose。
- [ ] T6 TDD + `./scripts/check.sh all` + Audit（/code-review + /neat-freak）。
- [ ] T7 部署 dev + 端到端：official 24.03 装不回归 + 26.09-DevStation rc3 6.6 ISO
  装成功 + 6.18 ISO 装调试。

## 验证命令与验收场景

- 检查入口：`./scripts/check.sh all`。
- TDD：触发分支判断 / pxe-install.sh ISO 分支 mock（缓存+mount+提取+repo+umount）/
  N=3 清理 / 前端三级级联 payload。
- 验收场景：
  1. official 24.03-LTS-SP4 PXE 安装行为不变（else 分支，无回归）。
  2. 26.09-DevStation rc3 6.6 变体 ISO 安装：PXE 引导 + kickstart 从挂载 ISO 装 +
     成功起 SSH。
  3. 26.09-DevStation rc3 6.18 变体 ISO 安装：部署后实测，可能需调试引导/kickstart。
  4. ISO 缓存：同 os_version+arch 第 4 个轮次下载后，最旧 ISO 自动删。
  5. 前端三级级联：版本按发行版分组 → 选 RC 版本轮次下拉有 rc3/rc4 → 选轮次后
     内核变体下拉有 6.18/6.6；release 版本无轮次/内核下拉。

## 风险

- **6.18 内核 ISO 安装**：测试反馈 6.6 正常、6.18 安装界面不同可能遇困难
  （grubaa64.efi 引导行为 / kickstart 兼容）。先按方案开发，T7 部署后实测 6.18
  再调试，不阻塞 6.6 + official。
- **6.6 变体 ISO 名不含 DevStation**：dailybuild 6.6 变体 ISO 名
  `openEuler-26.09-...-dvd.iso`（非 DevStation），seed `physical_install_images`
  时 iso_url 注意取变体目录正确路径。
- **ISO 缓存磁盘**：26.09-DevStation 每 RC 每内核变体每架构一个 ~2GB ISO，N=3
  清理控制，但多 os_version 累积仍占空间，必要时调 N 或手动清。
