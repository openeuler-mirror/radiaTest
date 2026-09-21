<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: 虚拟机批量释放功能

## 状态

complete。TDD RED→GREEN（3 行为）；code-review 修 VMQueueUnavailableError 捕获+resource_ids 去重；neat-freak 文档对账（ADR 0005/CONTEXT/spec 不动，batch 是循环封装）；265 passed + typecheck 过。

## 目标

在虚拟机管理页面提供批量释放能力：用户可多选 VM，一键批量释放（销毁）。非 ADMIN
只能释放自己占用的 VM（租约所有者），ADMIN 可 force 释放所有。解决 92 宿主机累积
108 个 running VM（keep_env 保留未销毁）导致内存耗尽时无法快速释放的问题。

## 范围

- **A. 后端 `POST /vms/batch-release`**：接收 `VMReleaseBatchRequest{resource_ids: list[str], reason: str | None}` +
  `Idempotency-Key` header。循环对每个 resource_id 调 `request_vm_release`（内部
  `ensure_vm_release_allowed` 检查权限：非 ADMIN 释放自己租约，ADMIN force 释放所有）。
  单个失败不阻塞（归 `failed`）。返回 `{destroyed: list[str], failed: list[str]}`，
  对齐 `destroy_execution_envs` 模式。`current_user` 权限（非 AdminUser）。
- **B. 前端 `virtual-machines/index.vue`**：VM 列表 Table 加 `rowSelection`
  （多选 checkbox）+ 工具栏"批量释放"按钮（选中后启用，点击弹确认框，确认后调
  `batchReleaseVMApi` 带 `Idempotency-Key`）。释放后清空选中 + 刷新列表。

## 非目标

- 不改单个释放逻辑（`request_vm_release` / `ensure_vm_release_allowed` / `enqueue_vm_destroy`）。
- 不改 VM 销毁异步链路（enqueue_vm_destroy → Celery destroy_vm_task → process_vm_destroy）。
- 不加同步等待销毁完成（批量 enqueue 后立即返回，异步销毁）。
- 不改权限模型（复用 ensure_vm_release_allowed，非 ADMIN 释放自己租约，ADMIN force）。
- 不改 spec/ADR 0005（VM 释放不变式不变，批量是单释放的循环封装）。

## 确认决策（grilling 3 题）

1. **后端 API = 新建 `POST /vms/batch-release`**：一次 HTTP，循环 request_vm_release，
   返回 {destroyed, failed}，部分失败不阻塞。
2. **前端 = 多选 + 批量释放按钮**：Table rowSelection（checkbox）+ 工具栏"批量释放"
   按钮（选中后启用，确认弹窗）。
3. **权限 = current_user + ensure_vm_release_allowed**：非 ADMIN 释放自己租约，
   ADMIN force 释放所有；每 VM 检查，无权归 failed。要 Idempotency-Key。

## 任务

- [ ] T0 TDD 后端 `POST /vms/batch-release`：`VMReleaseBatchRequest` schema +
  `release_vm_batch_endpoint` + `batch_release_vms` service。TDD：
  (1) 非 ADMIN 批量释放自己 VM → destroyed；(2) 非 ADMIN 释放他人 VM → 归 failed；
  (3) ADMIN force 释放所有 → destroyed。
- [ ] T1 前端 `virtual-machines/index.vue`：Table rowSelection + "批量释放"按钮 +
  确认弹窗 + `batchReleaseVMApi`。
- [ ] T2 `./scripts/check.sh all`（ruff + pytest + 前端 typecheck/lint/build）。
- [ ] T3 Audit：独立只读审查 + check.sh。
- [ ] T4 部署 dev + 端到端（多选 VM 批量释放）。

## 进度

- Clarify + Architect + Elaborate 完成，待用户确认门后进 Solve。

## 验证命令与验收场景

- 检查入口：`./scripts/check.sh all`。
- TDD（后端）：`test_release_vm_batch` 3 行为（自己/他人/ADMIN force）RED→GREEN。
- 验收场景：
  1. `./scripts/check.sh all` 干净（backend + frontend）。
  2. 前端 VM 列表可多选 + 批量释放按钮 → 确认 → VM 进入释放流程。
  3. 非 ADMIN 释放他人 VM 归 failed；ADMIN 全释放。
