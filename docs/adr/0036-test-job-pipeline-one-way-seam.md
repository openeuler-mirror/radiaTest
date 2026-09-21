<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0036：Test Job 与 Pipeline 的单向模块边界

日期: 2026-08-27

## 状态

已采纳。

## 背景

Pipeline 触发 Test Job 后，Test Job 执行期曾直接读取 Pipeline 模板和 RunJob，并写入
Pipeline 的节点、日志与子用例结果模型。这样使 Test Job 无法独立执行，也使 Pipeline
聚合状态依赖反向调用。

## 决策

- 依赖方向固定为 `Pipeline → Test Job`；Pipeline 通过 `PipelineRunJob.test_job_id`
  关联并读取 Test Job 的执行结果。
- Test Job 创建时保存物理机用途快照；物理环境执行不再查询 Pipeline 模板或 RunJob。
- Test Job 拥有用例子结果和日志产物。Pipeline 通过 Test Job ID 聚合节点、日志和结果，
  并继续兼容历史日志的 `pipeline_run_id` 关联。
- Pipeline 节点信息在读取时从 Test Job 环境节点投影，不由 Test Job 写入 Pipeline 表。

## 不采用

- **Test Job 回调或直接写 Pipeline 表**：会恢复反向依赖，且将 Pipeline 展示模型耦合进
  执行链。
- **轮询或新增后台同步任务**：读取时投影已可得到节点和结果，不需要额外时序与故障恢复。
- **保留 `TestJob.pipeline_run_job_id` 作为方便查询字段**：Pipeline 已持有
  `test_job_id`，该反向关联没有独立领域价值。

## 影响

- `test_jobs.pipeline_run_job_id` 迁移为 `physical_usage_scenario` 执行快照；历史数据在迁移
  时回填。
- 既有 Pipeline 页面和 API 的节点、日志、子用例展示语义保持不变。
- 新增 Test Job 代码不得导入 Pipeline 模块；该约束由测试覆盖。
