<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# pkgunion 模块：pkgcmd/pkgserver 用例并集 + pre_env 全量更新

## 背景与问题

1. **用例重叠**：pkgcmd（`repodata_packages` → `plan_cases` 按 `suite_name==更新包名` 匹配）会选中 suite 内全部用例，包含 `oe_test_service_*`；pkgserver（`service_test_cases` → 按 `case_name` 全表匹配 `oe_test_<type>_<name>`）也选中同类用例。同一 service 用例在两个模块各执行一次，浪费环境与时长。
2. **全量更新缺失**：现有 `UPDATE_REPO_SETUP` 只换源 + makecache，机器保持 GA 基线 + 按需装被测包。用户要求"换源后更新全部包到最新版本再执行用例"。

## 方案（经 Grill 确认，Q1–Q7）

新建 `pkgunion` 模块（进 seed），不改 pkgcmd/pkgserver：

- **case_filter=`repodata_union`**：`fetch_update_packages`（source 包名 → `plan_cases`）∪ `fetch_service_packages`（filelists 服务 → `case_name` 匹配），按 `(suite_name, case_name)` 去重，env_type 拆分与 no_case 口径沿用 repodata 路径；`update_packages` 返回两路包名并集（供 pre_env 补装 update 轮新增包）。
- **pre_env**（顺序）：`UPDATE_REPO_SETUP` → `dnf update -y` 全量更新（失败即 pre_env 失败，fail-fast）→ pkgcmd 环境位（`mount --make-rshared` + sysctl userns + polkit）→ pkgserver 全套服务语义（`update_list` 生成 → 按 `KRONOS_TEST_PACKAGES` 补装 → 服务发现 → `select_services` 分类 → `check_new_service` 冒烟无专用用例的服务，`|| true` 不影响退出码）。**不 reboot**——运行旧内核+新 userland（真实用户 `dnf update` 后常态）；最新内核由 kernel 模块在物理机单独覆盖。
- **post_env**：`clean_up_env`（停服务+卸包，卸载是服务测试动作的一部分）→ 重装 openssh-server + 重启 sshd（自汇集依赖 SSH）→ 生成 `pkgunion-details.log`（扫全部 results suite）→ 拷 mugen logs/results → `RESTORE_SSH_ACCESS`。
- **result_parser=`pkgunion`**（独立值，非复用 pkgcmd）：per-case 日志路径按 parser 名派生（`/opt/{parser}-logs/`），自汇集按模板名拉（`/opt/pkgunion-logs/`），复用会路径错位。接入三处分发表：mugen_runner 子用例解析集合、per-case 收集集合、前端 isPkgcmd 判断。
- **互斥校验**：PipelineConfig 保存时，pkgunion 与 pkgcmd/pkgserver 不得同时勾选（`PipelineConfigValidationError`），否则重叠换个地方回来。
- **命名派生**：`usage_scenario=pkgunion-update`、`pkgunion_physical_enabled`（物理机开关 flag，后端通用派生无需改）。
- **前端三处一行级**：`run-job-detail.vue` isPkgcmd 加 pkgunion；`pipelines/index.vue` 物理机开关 + parser SelectOption 各加一条。no_case/包行展示为状态驱动，零改动自动生效。
- **存量配置不自动迁移**：现有勾 pkgcmd/pkgserver 的配置照常可跑，由用户自行换成 pkgunion。

## 明确不做

- 不合并、不修改 pkgcmd/pkgserver 模板与 case_filter（保留可回退）
- 不改公共 `UPDATE_REPO_SETUP`（其余模块不引入全量更新，后续推广是纯加法）
- 不做跨模块 builder 去重（RunJob 并行构建无共享状态，复杂度不值）
- pre_env 全量更新后不 reboot、不引入等 SSH 回来机制
- 不自动迁移存量配置，不代用户改配置
- 不新增数据库表/列（模板走既有 seed 幂等更新）

## 实施步骤（TDD，每步先失败测试再实现）

1. builder `_resolve_cases` 加 `repodata_union` 分支：两路解析 → `(suite, case)` 去重合并 → env_type 拆分 → no_case 与 update_packages 口径。单测：重叠用例只出现一次、no_case 只来自 repodata 路、vm/physical 拆分、包名并集。
2. seed：`PKGUNION_PRE_ENV`/`PKGUNION_POST_ENV` + `DEFAULT_TEMPLATES` 加 pkgunion 条目。单测：test_seed.py 加模板字段断言 + pre_env 含 `dnf update -y` 断言。
3. mugen_runner：解析集合 `{pkgcmd,pkgserver,mugen_results,docker}` 与 per-case 收集集合 `("pkgcmd","pkgserver")` 各加 `pkgunion`。单测。
4. 配置互斥校验（create/update 路径）。单测：pkgunion+pkgcmd / pkgunion+pkgserver 均 422/校验错误，pkgunion 单独勾通过，pkgcmd+pkgserver 同时勾（现状）仍允许。
5. 前端三处小改。
6. 文档：Spec 0003（§8.1 四分派、§8.2.6 pkgunion、互斥校验、验收标准）+ ADR（并集策略、互斥取舍、全量更新落点与不 reboot、否决合并老模块/静态分工/跨模块去重的理由）。
7. `./scripts/check.sh`。

## 验证标准

- 上述单测先失败后通过；`./scripts/check.sh` 通过
- 危险用例过滤（ADR 0043）在 builder 统一接入点对新分支自动生效（同代码路径，无需额外接入）
- 部署后实测（远程 dev/prod，用户侧）：物理机占用并标 `pkgunion-update` 用途；配置勾 pkgunion 触发，确认 pre_env 全量更新执行、用例并集无重复、`check_new_service` 产出、`pkgunion-details.log` 与日志自汇集正常
