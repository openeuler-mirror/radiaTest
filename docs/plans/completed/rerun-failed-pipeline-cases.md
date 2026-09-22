<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: RunJob 失败用例按选重跑

## 状态

已完成。

关联决策：[ADR 0028](../../adr/0028-rerun-cases-in-source-environment.md)（取代 0027）。

## 目标

在 RunJob 详情中让已登录用户勾选失败的 Mugen 用例并一键重跑。原执行事实保持不变，最新
重跑结果成为看板当前状态，并可追溯完整重跑链和分组日志。

## 范围

- RunJob 保存来源、根来源和所选 suite/case 快照，支持连续重跑。
- 重跑仅接受终态 RunJob 中状态为 `failed` 的 Mugen Case Run；同名 suite/case 去重。
- 从原 Test Job 快照创建新的 Test Job，只执行选择的用例。
- RunJob 详情提供重跑弹窗、失败用例复选框和全选；来源详情顶部展示最新重跑记录。
- 看板与 Run 状态使用每条重跑链中的最新 RunJob；日志按执行记录、时间和重跑次数分隔展示。

## 非目标

- 不支持 `error`、`timeout`、`skipped`、`no_case` 或 `not_executed` 结果重跑。
- 不自动重跑、不新增轮询、调度器、依赖或跨 RunJob 批量操作。
- 不覆盖或复用原 Test Job、环境、日志或 Case Run。

## 实施与验证

- [x] 增加模型和 Alembic 迁移，并补充后端服务/API 测试。
- [x] 让 builder 基于原 Test Job 快照创建重跑任务。
- [x] 更新 read-time 状态聚合、重跑链和日志详情。
- [x] 实现前端弹窗、全选、提交和重跑记录展示，并完成 TypeScript 检查。
- [x] 运行受影响测试、项目检查、迁移 head 和 `git diff --check`。
