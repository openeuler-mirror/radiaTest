<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: pkgserver 日志展示优化 — stdout/stderr 移 case-log + 删执行结果/pkg_manage_folder + 修重复日志

## Goal

1. case_run 的 stdout/stderr 移到 case-log 页面顶部展示。
2. 右栏删除"执行结果"块和"pkg_manage_folder"段,所有模块统一只保留"日志"段。
3. 修复 env1/env2 重复日志 bug(`_self_collect_logs` 目录路径不含 env_set_index)。

## Confirmed Decisions

1. case-log 页面复用 `getRunJobDetailApi(runJobId)` 获取 case_run 的 stdout/stderr,无新后端接口。
2. 所有模块(含 pkgcmd)右栏统一只保留"日志"段,移除 `v-if="!isPkgcmd"`。
3. 重复日志 bug 根因:`_self_collect_logs` 的 `local_parent` 不含 `env_set_index`,env1/env2 的 pkg_folder 拷到同一路径,第二个覆盖第一个。

## Task Checklist

### Task 1: 后端 — 修复重复日志 bug (tasks.py)

- [ ] `_self_collect_logs`: multi_env 时 `local_parent` 加 `env{env_set_index}` 子目录,让 env1/env2 的 pkg_folder 指向不同目录
- [ ] 测试: multi_env 下两个 env_set 的 logs artifact storage_path 不同

### Task 2: 前端 — case-log.vue 加 stdout/stderr

- [ ] 调 `getRunJobDetailApi(runJobId)` → 从 `case_runs` 按 `caseRunId` 找到 stdout/stderr
- [ ] 展示在页面顶部(stdout + stderr pre 块),mugen 日志在下方
- [ ] 无 stdout/stderr 时展示空状态

### Task 3: 前端 — run-job-detail.vue 右栏简化

- [ ] 移除 `v-if="!isPkgcmd"` 和 `:class` 条件 grid → 右栏始终展示,左栏始终 `runjob-left`
- [ ] 删除"执行结果"块(isPkgmanage/isKernel/default 分支 + isPkgcmd 分支)
- [ ] 删除"pkg_manage_folder"段
- [ ] 保留"日志"段(module_log 链接)
- [ ] 清理死代码: isPkgmanage, isKernel, isPkgcmd, reportArtifacts, folderArtifacts, openFolder
- [ ] 保留: mugenLogs, openLog

### Task 4: 文档同步

- [ ] ADR 0021: 标注右栏不再 pkgcmd 专属隐藏,统一只保留日志段
- [ ] Spec 0003: 更新右栏描述
- [ ] CONTEXT.md: 更新右栏描述

## Verification

- `./scripts/check.sh backend` — ruff + pytest
- `./scripts/check.sh frontend` — typecheck + lint + build
- 手动验证: case-log 页顶部显示 stdout/stderr;右栏只有日志段;无重复 mugen 日志文件
