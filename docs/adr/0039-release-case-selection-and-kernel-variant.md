<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0039：release 流水线支持 case 级用例选择与内核变体

日期: 2026-09-03

## 状态

已采纳。

## 背景

release 流水线类型（B 类 `direct_run`）原由 [SPEC 0003 §9](../spec/0003-test-pipeline.md) 定义为最小形态：suite 级筛选（`config_data.suites`，每个 suite 跑全部 case）、env_type 固定 vm、`find_or_create_suite_template` 建空脚本模板、触发级 `image_round` 覆盖。§11.6 还把 "direct_run 类型的 case 级筛选" 列为延后项。

RC 测试场景需要更细的控制：对每个 suite 精选 case（而非全跑）、按 RC 轮次选定内核变体（dailybuild `*-with-kernel-*`，与 [ADR 0038](0038-vm-custom-kernel-swap.md) 的 VM 申请换内核同一来源）、单版本+单轮次定位一轮 RC。这些诉求与 §9 现状直接冲突，需在编码前明确取舍。

核心约束：release 与 update 不可互相干扰——两者共享通用执行层（§4 `run_pipeline_run_job`、`process_test_job`、§4.8 自汇集），任何 release 增强不得改变 update 运行路径的行为。

## 决策

### 1. 扩展 release 类型本身，不新建类型

在现有 `release`（`strategy_kind=direct_run`，seeded 系统类型）上增加 case 级选择 + 内核变体，而非新建一个 `is_system=False` 的子类型。理由：用户意图明确是增强 release；新建类型会带来类型分裂（看板、模板、配置表单都要分叉），而 release 已是 seeded 系统类型，是承载该能力的正确位置。同步更新 SPEC §9.1（改写为 case 级）并移除 §11.6 的延后项。

### 2. case 级选择走 config_data.case_selections，复用既有 builder

`config_data.case_selections = [{suite_name, case_names}]` 存选中用例。builder 的 `none` case_filter 分支对 direct_run 读该字段，按 RunJob 的 suite 取 `case_names` 传给既有 `select_cases(suite=..., case_names=...)`——与 update 的 `none` 模板（`case_names=None` → 全选）同一代码路径，direct_run 无选择时回退 None，update 行为不变。不新增 case_filter 枚举值，不改 update 的 `repodata_packages`/`service_test_cases` 分派。

### 3. 单版本+单轮次，轮次归配置级

release `versions` 列表长度固定为 1（单版本），`image_round` 存 `PipelineConfig.image_round`（配置级），触发无参数。release 的 RC 语义是"定位一轮 RC 全量测"，不是 update 的"多版本矩阵"；多版本矩阵是 update 专属。触发不再传 `image_round` 覆盖（§9.3 改写），新轮次由编辑配置实现。`PipelineTriggerRequest.image_round` 覆盖能力对 update 保留不变。

### 4. 每架构一套环境跑全部 suite（RunJob 形状 = `version × arch`）

release 单版本，故 RunJob = 每个 `arch` 一个（多架构 = 每架构一套并行）。每个 RunJob 的 TestJob/env_set 跑**全部选中 suite 的 case**（跨 suite 共一套环境，不按 suite 拆分 RunJob）；env_set `node_num` = 全部选中 case 的 `node_num` 最大值（如 2 suite 共 10 case，其中 1 个需主从 2 节点 → 建 2 台 VM，全部 case 共享该 env_set），`env_set_num`=1。这匹配 grill Q4 的"VM 数=max(node_num)、全部 case 在一套环境"语义——之前误实现成 per-suite env（`suite × arch` RunJob）已修正。

builder `_resolve_cases` "none" 分支汇总 `config_data.case_selections` 全部 suite 的选中 case（`select_cases(selections=[...])`）进一个 TestJob，不按 `template.suite_name` 单 suite 选。单模板（见决策 6）承载 pre/post_env，`module_template_id` 指向它。

### 5. 内核变体快照到 TestJob.pipeline_extras（JSONB），透传既有 VMRequestCreate

`config_data.kernel_variant`（dailybuild 变体段）与 `config_data.kernel_rpm_url`（手动 RPM URL）二选一可空，builder 快照到 `test_jobs.pipeline_extras`（JSONB 单列，键 `kernel_variant`/`kernel_rpm_url`）。`create_env_node_vm` 从 `job.pipeline_extras` 读取并透传给 `VMRequestCreate`（[ADR 0038](0038-vm-custom-kernel-swap.md) 已有的字段与校验），由既有 `process_vm_request` → `apply_custom_kernel` 换内核。release 不重写换内核逻辑，只复用 VM 申请链路。update 的 `pipeline_extras` 为 NULL，`create_env_node_vm` 透传 NULL → 不换内核，行为完全不变。

多架构时变体为单一共享选择：`list_kernel_variants` 是 (os_version, round, arch) 维度的，前端取各选中架构可用变体的交集；交集为空则不选变体（留空）。不在配置层做 per-arch 矩阵——变体段名跨架构一致，只是可用性按架构过滤。

**为何用 JSONB 单列而非逐字段加 nullable 列**：类型专属字段（release 的内核参数、未来新流水线的专属参数）走 JSON，不为每个流水线类型给共享 `test_jobs` 加实列——避免"后续新流水线新增列很多"导致的列膨胀与逐类型迁移。共用执行层（ADR 0009）保留为实列（dist/os_version/arch/scripts 等跨类型通用字段），类型专属参数隔离在 `pipeline_extras` JSON。这与 `test_jobs` 已有的 `update_packages: JSON`（类型专属数据走 JSON）思路一致。

### 6. 默认 post_env_script 收集日志，不改通用自汇集

`_find_or_create_release_template` 为 release 单模板写默认 `post_env_script`（拷贝 `${OET_PATH}/logs`+`${OET_PATH}/results` → `/opt/{template.name}-logs/`=`/opt/release-logs/`），使 §4.8 自汇集（SSH 拉 `/opt/{template.name}-logs/*`）对 release 直接可用。**不**改 §4.8 共享自汇集代码加 strategy 分支——那是 update 也运行的通用层。release 的日志落盘靠模板自带脚本，不靠改执行层。`${OET_PATH}` 已由 `build_env_file` 注入（§4.2.2），无需额外编排。

## 后果

- SPEC §9.1/§9.2/§9.3/§9.5 改写，§11.3 验收项重列，§11.6 移除 case 级选择延后项。
- `test_jobs` 加 JSONB `pipeline_extras`（nullable，迁移）；release 存 `kernel_variant`/`kernel_rpm_url`，update 为 NULL。
- `DirectRunPipelineStrategy.plan_run_jobs` 约束单版本、按 arch 建 RunJob（每架构一套环境跑全部选中 suite 的 case）。
- builder `none` 分支 direct_run 汇总 `config_data.case_selections` 全部 suite case；`_find_or_create_release_template` 写默认 `post_env_script`；builder 把 release 内核参数快照入 `TestJob.pipeline_extras`。
- `create_env_node_vm` 从 `job.pipeline_extras` 读内核参数透传 `VMRequestCreate`。
- 前端 release 配置弹窗：cascading dist→os_version→round→多架构 checkbox→内核变体(select XOR URL)→重设计 case 选择器（左 suite 浏览、右"已选"视图：选 suite 默认全选 case、可展开精细取消、可整 suite 移除）。

## 不采用

- **新建独立 direct_run 子类型**承载 case 选择：类型分裂、看板/模板/表单分叉，收益低；release 系统类型是正确承载位置。
- **改 §4.8 共享自汇集按 strategy_kind 分流**（direct_run 直拉 mugen 默认目录）：触及 update 也运行的通用执行层代码，干扰风险高于"模板自带默认 post_env"方案。后者只改 direct_run 专属的 `_find_or_create_release_template`，共享自汇集字节级不变。
- **per-arch 内核变体矩阵**：变体段名跨架构一致，按架构分别选增加 config_data 与 UI 复杂度，无明确收益。
- **release 走 `-64k` os_version 后缀路径**：release 用 `kernel_variant` 字段（显式指定版本内核），与 `-64k`（页大小变体）意图不同，两者触发模型不同（见 ADR 0038 不采用项），release 不叠用。
- **release 物理机 RunJob / ISO-PXE 安装**：当前 RC 测试场景由单版本 qcow2+apply_custom_kernel 覆盖；物理机/ISO 留作后续扩展。
