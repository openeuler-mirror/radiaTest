<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0019：pkgcmd.log per-case 收集 + suite 级折叠 + update_list 先展示

日期: 2026-07-27

## 状态

已采纳。

## 背景

pkgcmd.log 在 post_env 统一遍历 `${OET_PATH}/results/*/` 生成，但 mugen.sh 每跑一个 case 就覆盖 results 目录 → 只有最后一个 case 的结果存活 → pkgcmd.log 不全。老 Eulerpipeline 在每个 testcase 的 subshell 里跑完立刻统计追加到 LOG_FILE，radiaTest 需要同样的 per-case 收集。

前端 case list 平铺所有 case（suite/case 逐行），用户看不清。update_list 应任务启动后立即展示（不等 pre_env + self-collect）。

## 决策

### 1. pkgcmd.log per-case 收集

mugen_runner 的 `run_case` 每个 case 跑完后，立即在机器上统计该 case 的 mugen results（succeed/failed/skipped + failed case 名）并**追加**到 `/opt/<module>-logs/pkgcmd.log`。不再依赖 post_env 统一遍历被覆盖的 results 目录。

- `run_case` 跑完 `mugen.sh -f <suite> -r <case> -x` 后，立刻 SSH 执行一段统计脚本，输出追加到 pkgcmd.log。
- 统计逻辑跟老脚本一致：`ls succeed/ | wc -l` 等。
- post_env 只负责拷 mugen logs/results 目录（不再生成 pkgcmd.log 汇总——已 per-case 追加完）。

不采用：post_env 统一遍历 results（被覆盖，不全）。不采用：worker 生成 pkgcmd.log（worker 不在机器上，拿不到 results 目录）。

### 2. update_list 先展示

builder 已把 `packages`（fetch_update_packages 结果）存到 `TestJob.update_packages`（ADR 0018）。API 返回 `update_packages` → 前端任务启动后**第一个展示**（不等执行完）。update_list 标记 no_case 包（case_run 为 `NO_CASE` → "无用例"；ADR 0037 取代了早期 `SKIPPED` 语义）。

### 3. suite 级折叠

> **已变更（ADR 0021）**：pkgcmd 模块右栏已隐藏，"右栏执行结果展示 suite 级汇总"不再适用。suite 折叠和 case 点击跳转 mugen 日志保留。

前端 case list 按 `suite_name` 分组，默认折叠。suite 行显示：名 + 状态色（全通过绿/有失败红/全跳过灰）+ ✓N ✗N 计数。副标题标环境（全 VM→"VM"、全 physical→"物理机"、混合→"VM + 物理机"）。点 suite 展开 case 列表。右栏"执行结果"只展示 suite 级汇总（pkgcmd.log inline）。

## 影响

- `mugen_runner.py`：`run_case` 跑完后追加统计到 `/opt/<module>-logs/pkgcmd.log`。
- `seed.py`：PKGCMD_POST_ENV 去掉 results 遍历（改为只拷 logs/results 目录）。
- `service.py`：RunJob detail API 返回 `update_packages`。
- `run-job-detail.vue`：update_list 先展示 + suite 折叠 + 环境副标题 + isPkgcmd dispatch。
- spec 0003 + CONTEXT 同步。
