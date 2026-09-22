<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0017：模块日志收集路径 /opt/<module>-logs + pkgcmd 结果展示

日期: 2026-07-25

## 状态

已采纳。

## 背景

所有模块的 post_env + self-collect 之前用 `/tmp/module-logs/` 作为日志收集目录。`/tmp` 在部分机器上是 tmpfs（RAM 支撑，容量小），mugen 的 logs/results 目录可能很大（几百 MB），容易撑爆 `/tmp`。且所有模块共用一个目录，文件名可能冲突。

pkgcmd 模块的结果展示需要：左侧展示 update_list（本次转测哪些包），右侧展示 pkgcmd.log（每包执行结果），跟 pkgmanage 一样内联展示。mugen 原始日志沿用 post_env 统一拷（不做 per-case 上传）。

## 决策

### 1. 收集目录改为 /opt/<module>-logs/

每个模块的 post_env + self-collect 用 `/opt/<module>-logs/`（按 `template.name` 拼）：
- docker → `/opt/docker-logs/`
- kernel → `/opt/kernel-logs/`
- pkgcmd → `/opt/pkgcmd-logs/`
- pkgmanage → `/opt/pkgmanage-logs/`
- pkgserver → `/opt/pkgserver-logs/`

`_self_collect_logs` 从 `/opt/{template.name}-logs/` 读（`ls -1F`），按 RunJob 的 template.name 算路径。每个模块独立目录，互不干扰；`/opt` 是持久磁盘，不溢出。

不采用：继续用 `/tmp/module-logs/`（tmpfs 风险 + 模块间冲突）。不采用：`${OET_PATH}/module-logs/`（跟 mugen 目录混在一起，清理时可能误删 mugen 本身）。

### 2. pkgcmd 结果展示：update_list + pkgcmd.log 左右内联

> **已变更（ADR 0021）**：pkgcmd 模块的右栏已隐藏，update_list + pkgcmd.log 内联展示不再生效。用例列表全宽展示，点击 case 跳转 mugen 日志页替代。

`result_parser=pkgcmd` 的 RunJob 详情结果区：左侧 update_list（包列表，inline pre 展示），右侧 pkgcmd.log（每包结果，inline pre 展示）。跟 pkgmanage 的内联报告同模式，case_runs 列表保留下方。

- **update_list 生成**：PKGCMD_PRE_ENV 在 UPDATE_REPO_SETUP 后加 `dnf list --available --repo="${version_info}_update_source" | awk '/\.src/ {print $1}' | awk -F. 'OFS="."{$NF="";print}' | sed 's/\.$//' > /opt/pkgcmd-logs/update_list`（照老 Eulerpipeline 脚本）。
- **API 返回 content**：`read_run_job` 里 module_log 的 content 条件从 `"pkgmanage-details" in artifact_name` 扩展到 `or "pkgcmd" in artifact_name or "update_list" in artifact_name`，让 update_list + pkgcmd.log 也能内联返回。
- **前端 dispatch**：`isPkgcmd = result_parser === 'pkgcmd'` → 左右布局（update_list + pkgcmd.log），跟 isPkgmanage 同模式。

### 3. mugen 原始日志：沿用 post_env 统一拷

每个 case 跑完后 mugen 把日志写到 `${OET_PATH}/logs/` + 结果写到 `${OET_PATH}/results/`。post_env 统一把这两个目录拷到 `/opt/<module>-logs/`（logs/ + results/ 作为 `pkg_folder` 目录 artifact）。`_self_collect_logs` 在 finally 块 best-effort 收（挂了也尝试拉）。

不采用：per-case 上传（mugen_runner 每个 case 后多一次 SSH 拉文件，复杂 + 慢）。（后被 [ADR 0048](0048-per-case-log-atomic-upload.md) 采纳为逐 case 原子上传：用例粒度收敛后单 case 日志为 KB~MB 级，内联同步秒级完成，原否决理由不再成立。）

## 影响

- 所有模块的 post_env 脚本（seed.py）：`/tmp/module-logs/` → `/opt/<module>-logs/`。
- `_self_collect_logs`（tasks.py）：`ls -1F /tmp/module-logs/` → `ls -1F /opt/{template.name}-logs/`。
- PKGCMD_PRE_ENV：加 update_list 生成（dnf list + awk）。
- `read_run_job`（service.py）：module_log content 条件扩展。
- `run-job-detail.vue`：isPkgcmd dispatch + 左右布局。
- spec 0003 §4.8 + §5.4 同步。
