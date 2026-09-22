<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0021：pkgcmd 隐藏右栏 + case 跳转 mugen 日志 + 前端去 emoji

日期: 2026-07-28

## 状态

有效。pkgcmd 详情页隐藏右栏、左栏全宽展示为现行行为（pkgunion 详情页沿用同款语义，见 [ADR 0047](0047-pkgunion-module.md)）；页面细节以 [测试流水线功能规格](../spec/0003-test-pipeline.md) §5.5 为准。本文保留 pkgcmd case 跳转日志和去 emoji 的历史决策。

## 背景

RunJob 详情页(`run-job-detail.vue`)是所有模块共用的单一页面，右栏"执行结果"块按 `result_parser` 做 `if/else` 分派展示不同内容（pkgmanage 内联报告、kernel 日志链接、pkgcmd update_list+pkgcmd.log、默认 stdout/stderr）。不同模块有自己的特异性，只有部分展示块（统计卡片、用例列表、节点信息）能共用；把模块特异内容塞进一个共用块本身是设计问题。

pkgcmd 模块的执行已满足要求，用例列表（suite 级折叠 + case 状态）已完全替代右栏的执行结果展示。右栏对 pkgcmd 多余，应隐藏。

此外，前端页面使用了 emoji 符号（✓ ✗ ⏭ ⚠）表达状态和计数，不符合专业内网工具的视觉规范。

## 决策

### 1. pkgcmd 隐藏右栏

`run-job-detail.vue` 右栏加 `v-if="!isPkgcmd"`，pkgcmd 模块时整块隐藏，左栏（用例列表）全宽展示。其他模块（pkgmanage、kernel、docker、pkgserver）右栏不变。

不采用：为每个模块拆分独立详情页组件——改动面太大，且当前只有 pkgcmd 要求隐藏右栏。右栏的 `if/else` 分派设计问题留待后续模块拆分时统一处理。

### 2. case 行点击跳转 mugen 日志（所有模块）

所有模块的 case 行可点击，跳转到 `case-log.vue` 页面，展示该 case 的 mugen 日志文件内容（`logs/<suite>/<case>/*.log`）。

后端新增 `GET /pipelines/run-jobs/{run_job_id}/case-runs/{case_run_id}/mugen-log`：查 `pkg_folder` 类型且 `artifact_name` 以 `logs` 结尾的 artifact，列出文件，按 `{suite_name}/{case_name}/` 前缀过滤，返回首个匹配文件内容 + 全部匹配路径。

不采用：前端自行调 folder listing API 过滤——路径匹配（含 multi-env 命名 `env0-logs` 等）属后端职责，且一次调用比前端多次调用体验更好。不采用 case_run 的 `stdout_summary`/`stderr_summary`——用户明确要 mugen 文件夹内的日志文件。

### 3. folder-browser / log-viewer 保留

`folder-browser.vue` 和 `log-viewer.vue` 不删——其他模块（如 pkgmanage）右栏仍链接到它们。只有 pkgcmd 不再使用（右栏隐藏）。

### 4. 前端去 emoji

AGENTS.md 新增规则：前端页面不使用任何 emoji 或装饰性 Unicode 符号（如 ✓ ✗ ⚠ ⏭），状态和计数用文字标签或图标组件表达。现有页面中的符号已替换为纯文字（"通过"/"失败"/"跳过"/"异常"）。

## 影响

- `run-job-detail.vue`：右栏 `v-if="!isPkgcmd"`；case 行 `@click="openCaseLog"`；去掉 `isPkgcmd` 分支（死代码）；去掉 emoji。
- `case-log.vue`：新页面，路由 `/pipelines/run-jobs/:id/cases/:caseRunId/log`。
- `pipelines.ts`（API）：新增 `getCaseMugenLogApi` + `CaseMugenLog` 类型。
- `service.py`：新增 `get_case_mugen_log`。
- `router.py`：新增 mugen-log 端点。
- `execution-detail.vue`：去掉 emoji。
- `AGENTS.md`：新增 no-emoji 规则。
- ADR 0017/0018/0019：标注 pkgcmd 右栏已隐藏。
- Spec 0003 + CONTEXT 同步。
