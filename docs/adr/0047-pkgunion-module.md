<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0047: pkgunion 模块——pkgcmd/pkgserver 用例并集与 pre_env 全量更新

日期：2026-09-14
状态：已接受

## 背景

两个诉求叠加：

1. **用例重叠**：pkgcmd（`repodata_packages`）按 `suite_name==更新包名` 选中 suite 内全部用例（含 `oe_test_service_*`）；pkgserver（`service_test_cases`）按 `case_name` 全表匹配同类用例。同一 service 用例在两个模块各执行一次，双份环境、双份时长，结果还是同一个。
2. **全量更新**：现有 `UPDATE_REPO_SETUP` 只换源 + makecache，机器保持 GA 基线 + 按需装被测包；用户要求"换源后更新全部包到最新版本再执行用例"。

## 决策

新建 `pkgunion` 模块（seed），不动 pkgcmd/pkgserver：

- **`case_filter=repodata_union`**：builder 内 `fetch_update_packages`+`plan_cases`（repodata 路）与 `fetch_service_packages`+case_name 匹配（service 路）取并集，按 `(suite_name, case_name)` 去重；no_case 口径沿用 repodata 路；`update_packages` 返回两路包名并集供 pre_env 补装。
- **pre_env 全量更新**：`UPDATE_REPO_SETUP` 后 `dnf update -y`（显式 fail-fast），**不 reboot**——运行旧内核+新 userland 是真实用户 `dnf update` 后的常态，最新内核已由 kernel 模块在物理机单独覆盖（ADR 0026），再引入 reboot+等 SSH 回来机制收益配不上复杂度。全量更新只落在 pkgunion 的 pre_env，不改公共 `UPDATE_REPO_SETUP`——其余模块（docker 的 `dnf check-update` 产出、kernel 的 LTP 基线）测试语义不受影响，后续推广是纯加法。
- **保留 pkgserver 全套服务语义**：`check_new_service` 冒烟无专用用例的服务 + post_env `clean_up_env` 卸载（卸载是服务测试动作的一部分，对应 mugen `oe_test_service_restart` 的 post_test），避免 pkgunion 相对被替代两模块覆盖缩水。
- **`result_parser=pkgunion`（独立值）**：per-case 日志路径按 parser 名派生（`/opt/{parser}-logs/`）而自汇集按模板名拉（`/opt/pkgunion-logs/`），复用 pkgcmd 会路径错位；接入子用例解析、逐 case 收集、rerun 归档三处分发表。
- **配置互斥**：update 配置保存时校验 pkgunion 与 pkgcmd/pkgserver 不得同时勾选（422）。不加校验则重叠换个地方回来（新模块与老模块之间重复执行）。
- 存量配置不自动迁移，由用户自行换勾；物理机用途标记 `pkgunion-update`（部署侧占用并标记）。

## 备选方案与不采用理由

- **合并 pkgcmd+pkgserver 为单模块**：改动过大——模板合并、历史数据迁移（`PipelineRunJob.module_template_id` FK）、UI 矩阵/统计/ADR 0021 联动，且失去老模块可回退性。否决。
- **静态分工（pkgcmd 过滤 `oe_test_service_*` 前缀，service 用例归 pkgserver）**：改动最小，但"只勾 pkgcmd 时 service 用例无人执行"是行为回归，模块职责被迫重定义。否决。
- **动态让位（pkgserver 排除 pkgcmd 将选中的用例）**：无行为回归，但 pkgserver 的用例选择隐式依赖兄弟模块是否在场，跨模块耦合是排障坏味道。否决。
- **跨模块 builder 去重**：RunJob 并行构建无共享状态，为边缘场景引入协调机制不值。否决。
- **全量更新改公共 `UPDATE_REPO_SETUP`**：会改变 docker（check-update 报告变空）/kernel/pkgmanage 的既有测试语义。否决；需求跟新模块走。

## 影响

- builder 四分派（none/repodata_packages/repodata_union/service_test_cases）；危险用例过滤（ADR 0043）在 builder 统一接入点对新分支自动生效。
- 顺手修复既有 bug：`_PER_CASE_COLLECT_SCRIPT` 的 shell 花括号未转义，`.format(module=...)` 抛 KeyError 被 best-effort 吞掉，pkgcmd/pkgserver 的逐 case 日志收集自引入（1a92de8）起静默失效；pkgunion 接入该路径时修复并转双写花括号。
- 前端：pkgunion 详情页与 pkgcmd 同款（右栏隐藏全宽展示，ADR 0021 语义）；配置表单物理机开关加 per-module flag；no_case/包行展示状态驱动自动生效。
