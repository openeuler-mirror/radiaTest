<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0014: 物理机 PXE 安装

日期: 2026-07-24

## 状态

已采纳。本文"不扩 test job env_type"的原始范围仅约束本 ADR 的首轮原子能力实现；Pipeline 对该能力的后续集成由 [ADR 0015](0015-kernel-module-envtype-physical-reinstall-result-dispatch.md) 决定。

## 背景

radiaTest 已有 VM 创建链路（异步 Celery + 宿主脚本 + task_events + DHCP 反查 + SSH 验收），物理资源模型已含 BMC 凭据/MAC/primary_ip 字段。但 spec0001 将"PXE 装机"列为 Non-Goals，CONTEXT.md 写"测试任务不支持物理机环境执行"。

实际需求：物理机测试前需要重装系统（和 VM 创建对称——VM 从 qcow2 创建，物理机从 PXE 装机）。参考 radiaTest PXE 全链路（SSH 到 PXE 服务器 → 同步引导文件 → 改 dhcpd.conf 绑 MAC → ipmitool 设 PXE 启动 + 重启 → 轮询 SSH 等完成）。

## 决策

把物理机 PXE 安装实现为**原子能力**（非 test job 集成），后续 test job 需要时可调用并自行扩展。

### 1. 范围：只做原子装机能力

- `POST /resources/{id}/install` API + 异步 Celery 任务编排 5 步装机流程
- 本 ADR 不扩普通 test job API 的 `env_type`；Pipeline 内部集成留给后续 ADR 决定。
- 后续 test job 需要"先重装再跑用例"时，调用此原子能力并自行编排

不采用：同时做 test job 集成——范围过大，先收敛装机能力本身。

### 2. 验收方式：worker 一次同步调用 + 长 timeout

装机 Celery 任务编排全流程：调 `run_host_script` 到 PXE 服务器（sync + bind dhcp）→ worker 直连 BMC（ipmitool set PXE boot + power reset）→ worker 循环 SSH 验收（每 10 秒，最长 60 分钟——大版本装机包大，30 分钟不够）。每步写 task_event。不拆成"启动装机 + 用户手动刷新验收"。

验收细节：worker 用 `root` + 固定密码 `openEuler12#$` 登录目标机验证（账号密码登录,非密钥）；SSH **不校验 host key**（`StrictHostKeyChecking=no` + `UserKnownHostsFile=/dev/null`），因为重装后目标机 host key 必然变化,worker 的 `known_hosts` 残留旧 key 会让 `accept-new` 误判 "REMOTE HOST IDENTIFICATION HAS CHANGED" 而失败。验收通过后 `os_version` 直接写镜像的 `os_version`（其值已是 `openEuler-XX` 形式,不重复加 `openEuler-` 前缀）。

不采用：懒判断两步法——物理机装机是原子操作，用户期望触发后等待完成，不需要手动刷新触发验收。

### 3. PXE 服务器纳管为 `pxe-host` 标签的 PHYSICAL 资源

类比 `vm-host`，由 ADMIN 永久占用。PXE 服务器 SSH 凭据、tftp/httpd 路径从资源模型读取。worker 通过 `run_host_script` 操控（复用现有宿主脚本契约）。PXE 服务器就是现有 DHCP 服务器（172.168.131.94），一台机器同时承担 DHCP/PXE/TFTP/HTTPd 角色。

不采用：当外部基础设施配置——不可视、不可管、不复用资源模型。

### 4. root 密码：固定默认 `openEuler12#$`

ks 模板用固定 `rootpw --iscrypted` hash（对应 `openEuler12#$`，和 VM 默认一致）。`ks %post` 设 `PermitRootLogin yes` + `PasswordAuthentication yes` + `systemctl enable --now sshd`，确保装机后 sshd 允许密码 root 登录（部分 OS 默认禁密码 root 致验收 SSH 认证失败）。装机后用此密码 SSH 验收，验收通过后加密写入资源 `ssh_password_ciphertext`。不在任何文件存明文。

不采用：用户指定密码或配置文件存密码——复杂且有安全风险。

### 5. ks 模板：通用，不硬编码网卡名

`network --bootproto=dhcp` 不指定 `--device`（或用 `--device=link`），一套模板适配所有硬件。ks/grub 模板放代码仓 `host_scripts/` 目录跟随版本。

不采用：按硬件维护多套模板——维护成本高。

### 6. ipmitool 在 worker 容器内执行

worker Docker 镜像加装 `ipmitool`。装机任务中 worker 直连目标 BMC 执行 `chassis bootdev pxe + power reset`，不走 PXE 服务器。PXE 服务器只负责 PXE/DHCP 基础设施操作（sync files + bind dhcp）。

不采用：放 PXE 宿主脚本内——ipmitool 需要到目标 BMC 网络可达，worker 容器在内部网络中更通；且和 radiaTest messenger 的分工一致（messenger 本机跑 ipmitool）。

### 7. 物理机安装镜像模型：新建 `physical_install_images` 表

字段：`os_version`、`arch`、`efi_url`（grub EFI 下载地址）、`repo_url`（repo 根，其下有 `images/pxeboot/`）。ADMIN 手动维护镜像记录。ks/grub 模板放代码仓不进表。

不采用：配置驱动或复用 VM 镜像发现——PXE 需要的 EFI/repo URL 和 VM qcow2 路径结构不同。

### 8. 进度跟踪：只用 task_events

装机 Celery 任务每步写 task_event（`pxe_sync_files`/`pxe_bind_dhcp`/`pxe_ipmi_boot`/`pxe_installing`/`pxe_finished`/`pxe_failed`）。资源 `management_status` 设为 `maintenance`（装机中），完成后恢复 `active`。不新建装机请求表。

不采用：新建装机申请单表——原子能力不需要独立状态机，task_events 时间线足够。

### 9. 硬件探测回填：重装后自动 + 手动刷新

重装成功后（SSH 验收通过）best-effort SSH 探测硬件（一次 `bash -s` 跑 `lscpu`/`dmidecode -t memory`/`lsblk`/`uname`/`dmidecode -t baseboard`），解析后回填 `Resource.arch`/`kernel_version` + `PhysicalResourceSpec.cpu_model`/`cpu_count`/`memory_count`/`memory_spec`/`hdd_count`/`hdd_spec`/`ssd_count`/`ssd_spec`/`ssd_card_count`/`ssd_card_spec`/`board_sn`（探测值非 None 才覆盖，失败字段保留原值）。`os_version` 不覆盖（遵循第 2 节，重装写 `image.os_version`，之后重装自动刷新）。

另提供 `POST /resources/{id}/probe`（ADMIN）手动刷新（硬盘插拔后点一下）。前端资源详情抽屉加「刷新硬件」按钮。

探测 SSH 复用验收的 `verify_host_key=False`（重装后 host key 必变）；`run_ssh_command` 加 `output_limit_bytes` 参数，探测传 512KB（`dmidecode -t memory` 在多内存机器上输出大，默认 `SUMMARY_LIMIT=16KB` 会截断致前段标记丢失、arch/kernel/cpu/mem 全 None）。

不采用：beat 轮询 BMC power 状态自动探测——成本高，违背懒释放；重装后 + 手动按钮够用。

## 影响

- 新增 `physical_install_images` 表 + migration
- 新增 PXE 操控宿主脚本 `host_scripts/pxe-install.sh`（sync boot files + bind dhcp + 回滚）
- 新增 ks/grub 模板 `host_scripts/pxe-templates/`
- 新增装机 Celery 任务 + `POST /resources/{id}/install` API
- worker Dockerfile 加装 `ipmitool`
- 前端物理机列表行操作列加"重装系统"按钮（选镜像 + 确认）
- 新增硬件探测模块 `hardware_probe.py`（一次 SSH 跑 lscpu/dmidecode/lsblk/uname 解析回填）
- 新增 `POST /resources/{id}/probe` API + 前端详情抽屉「刷新硬件」按钮
- `run_ssh_command` 加 `output_limit_bytes` 参数（探测传 512KB）
- spec0001 移出 Non-Goals，补物理机安装条目
- CONTEXT.md 补"物理机 PXE 安装"领域语言
