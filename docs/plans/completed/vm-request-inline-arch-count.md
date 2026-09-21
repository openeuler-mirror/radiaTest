<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: VM 申请页架构数量框行内化

Status: complete
Branch: feat/pipeline-type-registration-and-config-delete
Related commits: 8462a84 (batch VM creation specs array), bcbc48e (checkbox arch select + conditional count inputs)

## Goal

VM 申请表单的"架构选择"项，将每个已选架构后面的数量输入框放到该架构复选框同一行紧随其后，不再单独成行。

## Scope (做)

仅改 `frontend/apps/web-antd/src/views/virtual-machines/index.vue` 第 984-1013 行模板：

- 3 个 `<div>`（架构选择 CheckboxGroup / "ARM 数量" InputNumber / "x86 数量" InputNumber）合并为 1 个 `<div>`。
- 单行结构：`架构选择` label（左对齐，保留 `requiredLabelClass('archSelections')` 绑定）+ `[Checkbox ARM] [InputNumber] [Checkbox x86] [InputNumber]`。
- 每个 InputNumber 仅在该架构被勾选时出现（保留现有 `v-if="requestForm.archSelections.includes(...)"` 条件）。
- InputNumber 宽度由 `w-full` 改为 `w-24`，以便两组塞进同一行。
- 去掉单独的 "ARM 数量" / "x86 数量" 文字 label（checkbox 的 ARM/x86 已表明身份，紧随其后的框即数量）。
- 整组左对齐、不强制拉满行宽（与邻居行同构：label 左 + 控件右、单行高）。
- min/max (1-20) 不变。

## Non-goals (不做)

- 不改后端 `specs` 契约（`POST /api/v1/vm-requests` 的 `specs` 数组结构不变）。
- 不改 `requestForm` 响应式字段（`archSelections` / `aarch64Count` / `x86_64Count`）。
- 不改 index.vue:448-466 的 `specs` 构造逻辑。
- 不改 `vm-request-form.ts` 及其测试 `vm-request-form.test.ts`（纯逻辑测试覆盖的不变行为）。
- 不改表单校验、`requiredLabelClass` 绑定、初始值/重置值（`x86_64Count` 已为 1，无怪癖可修）。
- 不补 spec 对多架构批量创建整体的记载（预存 gap，超出本次范围）。
- 不新增 DOM 渲染测试基建（web-antd 无既有组件 mount 测试，仅为布局微调引入 `@vue/test-utils` 属过度工程）。

## Confirmed decisions (grilling 结果)

1. 目标布局：单行 `架构选择  [☐ ARM][窄框 w-24]  [☐ x86][窄框 w-24]`，数量框仅勾选时出现。
2. 去掉 "ARM 数量" / "x86 数量" 文字 label。
3. 数量框窄宽 `w-24`，整组左对齐不拉满。
4. "x86 count 初始值怪癖"：不修，组件已为 1（index.vue:132,405）。

## Spec / ADR 冲突核查

- spec `docs/spec/0001-resource-management.md:164` "版本和架构使用下拉选择" 上下文（162-174 行）为飞书 Bot 卡片（单卡、默认"飞书申请 VM"、仅自动安装），非 Web 页。
- Web 页架构选择控件在 spec 334-349 行未规定类型。故代码用 CheckboxGroup 与 spec 不冲突，本次行内数量框亦不触及任何 spec 行。
- 无新 ADR（不构成架构/安全/领域决策）。

## TDD 判定

- 本次为纯展示层布局调整，无新行为：`archSelections` → `specs` 的构造逻辑不变，已被 `vm-request-form.test.ts` 覆盖。
- 无 RED 可写（无新行为可测）；引入组件 mount 测试仅为布局微调属过度工程。
- 验证策略：既有 vitest 回归（逻辑不变）+ typecheck + lint + build + 人工目视确认行内布局。

## Tasks

- [x] T1: 改 index.vue 第 984-1013 行模板（3 div → 1 div 行内；数量框 w-full → w-24；去掉两处数量 label）。已完成。
- [x] T2: 远程 dev 环境验证通过 — `./scripts/deploy.sh dev` 成功，见下方 Result。
- [x] T3: 前端 build 产物含 `virtual-machines-*.js`，构建通过；视觉行内布局待人工浏览器确认（dev 已可访问 http://localhost:8080）。

## Verification

```
./scripts/check.sh frontend
# = pnpm typecheck && pnpm lint && pnpm vitest run apps/web-antd/src && pnpm build
```

验收：上述全绿；vm-request-form.test.ts 既有用例不回归；表单视觉为单行行内。

## 本机验证受阻（均预存，非本次引入，用户决定待远程环境）

- typecheck：2 个未使用变量错误 `index.vue(205,7) manualArchOptions` / `index.vue(231,7) archOptions`，由 bcbc48e 删旧 Select 时遗留的孤儿声明（零引用，grep 已证）。stash 对照确认 HEAD 无本次改动时同样报这 2 个错误 → 与本次改动无关。用户决定**不删**，待远程环境一并处理。
- 已本机取证：本次模板改动**零新增 type 错误**（加改动后 typecheck 仍只有那 2 个预存错误，编辑区 984-1013 行无新错）。
- lint：`scripts/vsh/dist/index.mjs` 未构建（vsh 内部工具）。
- vitest：`rolldown-binding.linux-arm64-gnu.node` 原生二进制缺失（node_modules 平台不匹配）。
- 无 `corepack` 二进制 → `./scripts/check.sh frontend` 在第 31 行中断；node v20.18.2 低于引擎 `^22.18`（warn）。

## Progress

- Clarify: 完成（grilling 5 题已收敛；含预存孤儿处理决策）。
- Architect: 跳过（纯展示单文件，无模块/接口/seam 变化）。
- Elaborate: 完成（确认门已通过）。
- Solve: T1 完成；T2/T3 验证在远程 dev 通过。
- Audit: 通过 — 远程 dev 部署成功（build + 健康检查 + worker/bot 全绿）。
- Reconcile: 本文档已标记 complete 并移至 completed/（未 commit，留待人工审阅）。
- 状态：complete。
