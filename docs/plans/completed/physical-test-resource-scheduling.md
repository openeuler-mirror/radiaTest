<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: 修复物理机测试资源调度与状态展示

## 状态

已完成。实现、定向验证与远程 dev 环境验证均通过；提交已合入 main 并推送 origin/main，
工作分支已清理。仓库完整检查被既有的 VM shell、SSH mock 与 64k 镜像用例失败阻断，
详见本次任务交付记录。

## 范围

- 流水线触发前按唯一 `(arch, usage_scenario)` 检查触发者已占用且测试空闲的物理机；
  任一组不可用时整体返回 `409`，不创建 Execution 或 RunJob。
- 多版本共享同组物理机排队执行；worker 按 Test Job 的 15 小时总截止时间等待资源释放。
- 物理机选中后立即把 Env Node 与资源关联；其他任务依据非终态 Test Job 的节点关联判定资源
  `testing`，不得再次选中并重装。
- Resource API 派生 `test_status=idle|testing` 以及当前 Test Job 标识；不新增数据库列。
- 资源列表和详情独立展示测试状态，并提供 Test Job 入口。
- 测试中的物理机禁止释放或强制释放租约、修改资源字段及手动 PXE 重装；允许查看、读取凭据和
  延长租约。

## 非目标

- 不实现 pkgcmd/pkgserver 复用 kernel 已安装环境的前序链。
- 不新增 Celery 任务、队列、数据库表、轮询配置或通知。
- 不改变管理状态、租约状态和连通状态的既有取值。
- 不改变测试任务 15 小时总截止时间。

## 实施步骤

1. 在测试管理领域增加物理机活动测试查询、原子认领和截止时间内等待能力。
2. 在流水线触发服务增加物理机需求集合与可用性前置校验，路由映射为 `409`。
3. Resource API 批量派生测试状态与任务关联，资源和租约写操作复用同一活动测试判断。
4. 前端展示测试状态、任务入口与后端触发失败原因，并禁用测试期间的破坏性操作。
5. 同步 ADR 和 Spec；完成定向测试后运行一次 `./scripts/check.sh`。

## 验证标准

- 只存在他人租约、租约空闲、用途/架构不匹配或机器正在测试时，触发返回 `409` 且无执行记录。
- 每个所需 `(arch, usage_scenario)` 至少一台测试空闲自有机器时，触发成功。
- 同组后续版本等待前一任务结束后复用机器，不在前一任务测试期间触发 PXE 重装。
- 物理机从节点被认领起到 Test Job 终态前返回 `test_status=testing`，随后返回 `idle`。
- 测试中资源的租约释放、资源修改和手动 PXE 重装均由后端拒绝；延长租约和读取保持可用。
- 前端列表和详情能区分管理、租约和测试状态，并显示明确的触发失败原因。
