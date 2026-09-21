<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: pkgcmd 前端清理 — 删除执行结果块 + case 跳转 mugen 日志 + 去 emoji

## Goal

对 pkgcmd 模块的 RunJob 详情页做三项前端调整:
1. 删除"执行结果"展示块(右栏),功能由用例列表完全替代。
2. 用例列表中点击 case 直接跳转到该 case 的 mugen 日志(文件夹内的日志文件),删除 pkg_manage_folder(文件夹浏览器)模块。
3. 前端页面不使用任何 emoji 或装饰性 Unicode 符号;将规则加入 AGENTS.md;整顿当前所有前端页面。

## Scope and Non-Goals

### 做
- pkgcmd 模块隐藏右栏(执行结果块),左栏全宽。其他模块右栏不变。
- 所有模块的 case 行可点击,跳转到 mugen 日志页(文件夹内的日志文件)。
- 新增后端端点:按 case_run 查找 mugen 日志文件内容。
- 新增前端 `case-log.vue` 页面,展示 case 的 mugen 日志。
- folder-browser.vue 和 log-viewer.vue **保留**(其他模块右栏仍用)。
- AGENTS.md 新增"前端不使用 emoji"规则。
- 清除 `run-job-detail.vue` 和 `execution-detail.vue` 中的 ✓ ✗ ⏭ ⚠ 符号。
- Reconcile:同步 ADR 0017/0018/0019/0021、Spec 0003、CONTEXT.md。

### 不做
- 不删除 folder-browser.vue / log-viewer.vue(其他模块仍用)。
- 不删除后端 folder 读写 API 和路由。
- 不修改 RunJob detail API 返回字段。
- 不新增轮询、缓存、后台任务。
- 不修改后端 mugen_runner 或 seed.py 的日志收集逻辑。
- 不为每个模块拆分独立详情页组件(留待后续)。

## ADR/Spec/CONTEXT 冲突说明

用户明确要求删除右栏,代码为准。以下文档描述右栏,需在 Reconcile 阶段更新:

| 文档 | 冲突点 |
|------|--------|
| ADR 0017 §2 | pkgcmd 结果展示:update_list + pkgcmd.log 左右内联(右栏内) |
| ADR 0018 §5 | suite 级折叠 + "执行结果只展示 suite 级汇总"(右栏内) |
| ADR 0019 §3 | 右栏"执行结果"展示 suite 级汇总(pkgcmd.log inline) |
| Spec 0003 §4 (line 149) | 右栏执行结果块 + 日志段 + pkg_manage_folder 段详细描述 |
| CONTEXT.md (line 193) | 右栏"执行结果"区 + 日志段 + pkg_manage_folder 段 |

## Confirmed Decisions

1. 右栏仅对 pkgcmd 隐藏藏(`v-if="!isPkgcmd"`),其他模块保留。
2. "mugen 日志"= 文件夹内 mugen 日志文件(`logs/<suite>/<case>/*.log`),不是 case_run 的 stdout/stderr。
3. 点击 case → 跳转到独立日志查看页(所有模块)。
4. folder-browser.vue 和 log-viewer.vue 保留(其他模块右栏仍用)。
5. 新增后端端点封装"按 case_run 查找 mugen 日志文件"逻辑(路径匹配属后端职责)。
6. 前端页面不使用 emoji 或装饰性 Unicode 符号。

## Task Checklist

### Task 1: 后端 — 新增 case mugen log 端点

- [ ] service.py: 新增 `get_case_mugen_log(db, run_job_id, case_run_id) -> dict | None`
  - 取 RunJob → test_job_id, pipeline_run_id。
  - 取 TestCaseRun → 校验属于 test_job,取 suite_name, case_name。
  - 查 `TestLogArtifact` 中 job_id == test_job_id 且 artifact_type == "pkg_folder" 且 artifact_name 以 "logs" 结尾的 artifact。
  - 用 `LogCollector.list_dir_files` 列文件,按 `{suite_name}/{case_name}/` 前缀过滤。
  - 返回 `{content, file_path, files, run_id, artifact_id}`(首个匹配文件内容 + 全部匹配路径)。
  - 无匹配 → 返回 None(路由层 404)。
- [ ] router.py: 新增 `GET /pipelines/run-jobs/{run_job_id}/case-runs/{case_run_id}/mugen-log`
- [ ] tests: 新增 `test_get_case_mugen_log_found` + `test_get_case_mugen_log_not_found`

### Task 2: 前端 — 新增 case-log 页面

- [x] api/core/pipelines.ts: 新增 `getCaseMugenLogApi(runJobId, caseRunId)` + 类型
- [x] views/pipelines/case-log.vue: 新页面
  - 调用 `getCaseMugenLogApi`,展示日志内容(复用 log-viewer 的行号 + pre 布局)。
  - 多文件时展示文件选择器,切换用 `readFolderFileApi`。
  - 无日志时展示空状态。
  - 下载按钮。
- [x] router/routes/modules/pipelines.ts: 新增路由 `/pipelines/run-jobs/:id/cases/:caseRunId/log`
- [x] folder-browser.vue 和 log-viewer.vue 保留(其他模块右栏仍用)。

### Task 3: 前端 — pkgcmd 隐右栏 + case 行可点击 + 去 emoji

- [x] run-job-detail.vue:
  - 右栏加 `v-if="!isPkgcmd"`(pkgcmd 隐藏,其他模块保留)。
  - 网格 `:class="{ 'runjob-grid': !isPkgcmd }"`,左栏 `:class="{ 'runjob-left': !isPkgcmd }"`。
  - 删除 isPkgcmd 分支(死代码,右栏已隐藏)。
  - case 行加 `@click="openCaseLog(cr.id)"` + `cursor: pointer`(所有模块)。
  - 移除死代码:`pkgcmdLogArtifact`, `updateListArtifact`, `caseColumns`, `pagedCases`, `page`, `pageSize`。
  - 移除不再使用的 imports:`Table`, `TableColumnsType`。

### Task 4: 前端 — 去 emoji + AGENTS.md 规则

- [ ] AGENTS.md 项目规则段新增:
  > 前端页面不使用任何 emoji 或装饰性 Unicode 符号(如 ✓ ✗ ⚠ ⏭);状态和计数用文字标签或图标组件表达。
- [ ] run-job-detail.vue: 移除 ✓ ✗ ⏭ ⚠(stats 标签、Select 选项、suite 状态 Tag)。
  - stats: `✓ 通过` → `通过`,`✗ 失败` → `失败`,`⏭ 跳过` → `跳过`。
  - Select 选项: 同上。
  - suite Tag: `✗`/`✓`/`⏭` + count → 文字 `失败 N/M`/`通过 N/M`/`跳过 N/M`(颜色区分)。
- [ ] execution-detail.vue: 移除 ✓ ✗ ⏭(count 标签)。
  - `✓N` → `通过 N`,`✗N` → `失败 N`,`⏭N` → `跳过 N`。

### Task 5: Reconcile 文档

- [ ] ADR 0017: 标注 §2 右栏展示已移除(改为"case 点击跳转 mugen 日志")。
- [ ] ADR 0018: 标注 §5 右栏 suite 级汇总已移除。
- [ ] ADR 0019: 标注 §3 右栏展示已移除。
- [ ] Spec 0003 §4: 更新右栏描述为"用例列表全宽展示,点击 case 跳转 mugen 日志页"。
- [ ] CONTEXT.md: 更新 line 193 右栏描述。

## Verification

- `./scripts/check.sh backend` — ruff + pytest(含新端点测试)。
- `./scripts/check.sh frontend` — typecheck + lint + vitest + build。
- `./scripts/check.sh docs` — 文档规范检查。
- 手动验证(远程 dev):
  - RunJob 详情页:右栏已消失,左栏全宽。
  - case 行可点击 → 跳转到 mugen 日志页,展示日志内容。
  - 无日志的 case → 展示空状态。
  - execution-detail 统计标签无 emoji。
  - 无任何 ✓ ✗ ⚠ ⏭ 符号残留。

## Progress

- [x] Task 1: 后端 `get_case_mugen_log` + 路由 + 2 测试 (27 tests pass, ruff pass)
- [x] Task 2: case-log.vue + 路由 + API;folder-browser/log-viewer 保留
- [x] Task 3: run-job-detail pkgcmd 隐右栏 + 所有 case 行可点击 + 去 emoji
- [x] Task 4: AGENTS.md no-emoji 规则 + execution-detail 去 emoji
- [x] Task 5: ADR 0021 + ADR 0017/0018/0019 标注 + Spec 0003 + CONTEXT 更新

## Verification Results

- 后端 ruff: PASS
- 后端 pytest: 27 pipeline_execution tests PASS (7 pre-existing failures in test_repodata/test_test_management, unrelated)
- 前端 typecheck (vue-tsc --noEmit): PASS
- 前端 lint/vitest/build: 环境限制(rolldown 原生绑定不支持 Node 20),非改动引入
- 文档时间措辞检查: 无新增违规
- 全前端 emoji 扫描: 无残留
