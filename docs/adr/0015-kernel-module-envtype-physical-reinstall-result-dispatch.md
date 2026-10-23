<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0015：update 流水线 kernel 模块——env_type 模型 + 物理机重装集成 + 按 result_parser 派发展示

日期: 2026-07-25

## 状态

已采纳。`env_type=both` 拆为两个 RunJob 的部分已被 [ADR 0018](0018-both-single-runjob-dynamic-envset-updatelist-suite-collapse.md) 取代；物理机测试期锁的部分已被 [ADR 0029](0029-physical-test-resource-usage-state.md) 取代。kernel 物理执行和 PXE 集成仍有效。kernel 使用 `result_parser=ltp`；当前详情页呈现以 [测试流水线功能规格](../spec/0003-test-pipeline.md) §5.4 为准，不再以本文早期的独立 kernel 结果卡描述为准。

## 背景

update 测试流水线的模块模板用 `env_type_split: bool` 决定环境：True 拆 vm+physical，False 单环境（builder 兜底成 VM）。这只能表达"both"或"vm-only"，**表达不了"只物理机"**。kernel 模块当前 `env_type_split=False` → 跑在 VM 上，但 kernel 测试只能在物理机跑（裸金属内核/LTP），配置错误。

同时，物理机 RunJob 现在复用 idle 物理资源 + 新建租约 + **不重装**（[ADR 0014](./0014-physical-machine-pxe-install.md) 的 PXE 重装是独立原子能力，未接进 pipeline）。kernel 模块需要在跑 mugen 前**重装**目标物理机到 pipeline 的 OS。

执行结果展示方面，`run-job-detail.vue` 是所有模块共用的通用视图，不按模块分支；后端 `result_parser` 只用于 case 解析，前端没按它派发。不同模块有不同展示要求，需按 `result_parser` 派发。

## 决策

### 1. env_type 字段取代 env_type_split bool

`TestModuleTemplate` 加 `env_type: str`（`vm`/`physical`/`both`），取代 `env_type_split: bool`。
- `both` → **一个** RunJob，TestJob 内创建 VM/physical EnvSet（ADR 0018 取代了本文早期的双 RunJob 方案）。
- `physical` → 单 physical RunJob。
- `vm` → 单 vm RunJob（env_type=None，builder 兜底 VM，原 env_type_split=False 行为）。

模板取值：docker/pkgmanage=vm，pkgcmd/pkgserver=both，**kernel=physical**。

不采用：保留 bool + 另加 physical_only 标志——两标志语义重叠，不干净。不采用：kernel 设 both + 跳过 vm RunJob——hack，语义不清。

### 2. physical EnvSet：用触发者已占用的物理机 + RunJob 内同步重装

所有 physical EnvSet（kernel 的 physical RunJob，以及 pkgcmd/pkgserver 的 `both` RunJob 内 physical EnvSet）的环境建立不走 `find_physical_resource`（找 idle+新建租约），改为：
1. 找触发者（actor）当前已占用的、**用途标记（`usage_scenario`）= `<模块名>-update`** 的物理资源（arch 匹配，多台取第一台）。模块→用途：kernel→`kernel-update`、pkgcmd→`pkgcmd-update`、pkgserver→`pkgserver-update`。只重装用途匹配的机器，避免误装其它重要机器（如 vm-host/pxe-host）。
2. 按 pipeline run 的 `version`+`arch` 找 `physical_install_image`（os_version 匹配 + arch 匹配）。
3. 调 PXE 重装——把 [ADR 0014](./0014-physical-machine-pxe-install.md) 的 `run_pxe_install_task` 编排逻辑抽成可同步调用的函数（`run_pxe_install(db, resource_id, image_id, ...)`），RunJob 内联调用（阻塞等 SSH 通，复用验收 SSH 的 `verify_host_key=False`）。
4. SSH 通后跑 mugen 套。重装成功后 best-effort 探测硬件回填（[ADR 0014](./0014-physical-machine-pxe-install.md) 第 9 节）。

不采用：找 idle 物理机 + 占用 + 重装——与用户流程不符（用户预先占好机）。不采用：重装作为独立步骤/手动触发——不符合"RunJob 内全自动"。不采用：`.delay()` 触发重装 + 轮询——跨 Celery 任务协调复杂，RunJob 本就是 Celery 任务，内联同步调用更简单。

### 3. 结果展示按 result_parser 派发（后续简化）

`run-job-detail.vue` 的结果区曾按 `detail.result_parser` 派发渲染。`result_parser` 仍由详情 API 返回，并继续决定子用例解析；当前右栏的具体布局已简化，准确行为见 Spec 0003 §5.5。
- `pkgmanage` → 现有 pkgmanage 展示（参考，已调好）。
- `ltp`（kernel）→ `parse_ltp_log` 解析 LTP 子用例；其日志与目录 artifact 按当前通用日志区展示。
- 其余模块按各自解析器或通用布局展示。

kernel 的 `post_env_script` 上传 mugen 原始日志 + `/opt/ltp/ltp.log`（文件 artifact）+ `/opt/ltp/results`（目录 artifact）。

不采用：每模块一个独立 RunJob 详情页（run-job-detail-kernel.vue 等）——共享骨架（状态/节点/task_events/统计）+ 派发结果区更省，骨架一致。

## 影响

- 新增 Alembic 迁移：`test_module_templates` 加 `env_type` 列，回填（env_type_split True→both、False→vm、kernel→physical），删 `env_type_split`。
- `update.py` 策略改用 env_type 产生 RunJob；`both` 的一个 RunJob 在 builder 内按 EnvSet 展开；`case_planner.py` 已按 env_type 工作，无需大改。
- `pxe_install.py` 抽出 `run_pxe_install(...)` 同步函数（`run_pxe_install_task` 改为薄包装调它）；kernel RunJob 的 physical env 建立（`envs/physical.py` 的 kernel 路径）调它。
- kernel 使用 `ltp` result_parser + kernel post_env 上传 ltp 日志；详情 API 返回 result_parser，前端布局见 Spec 0003。
- seed：kernel env_type=physical、result_parser=ltp；其它模板 env_type 按 bool 回填。
- spec 0003 + CONTEXT 同步。
