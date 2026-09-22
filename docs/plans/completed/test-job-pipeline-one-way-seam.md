<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: Test Job 与 Pipeline 单向 seam 修复

## 状态

已完成。

关联决策：[ADR 0036](../../adr/0036-test-job-pipeline-one-way-seam.md)。

## 目标

消除 Test Job 执行期对 Pipeline 模块的反向依赖，使 Pipeline 通过
`PipelineRunJob.test_job_id` 单向关联并聚合 Test Job 的节点、日志和用例结果。

## 范围

- 将物理机用途作为 Test Job 创建快照，执行期不再读取 Pipeline 模板或 RunJob。
- 将子用例详情、日志产物、日志解析和收集器归入 Test Job 模块。
- Pipeline 读取 Test Job 环境节点、日志和子用例结果，兼容历史日志的
  `pipeline_run_id` 查询。
- 迁移历史物理任务的用途快照，并删除 `test_jobs.pipeline_run_job_id`。
- 为 Test Job 不导入 Pipeline 模块及 Pipeline 节点投影补充测试。

## 非目标

- 不新增 API、轮询、后台任务或外部依赖。
- 不改变 Pipeline 触发、Test Job 执行、结果状态、权限或页面展示语义。
- 不执行远程数据库迁移或部署。

## 实施与验证

- [x] 将 Pipeline 执行输入在创建 Test Job 时快照化。
- [x] 移除 Test Job 到 Pipeline 的源码导入和反向关联字段。
- [x] 让 Pipeline 通过 Test Job 数据进行节点、日志和结果聚合。
- [x] 新增 Alembic 迁移及 ADR 0036。
- [x] 聚焦测试：`56 passed`。
- [x] Ruff、Python 编译检查、Alembic 单一 head、文档检查与 `git diff --check` 通过。

## 验收标准

- `test_management` 源码不导入 `app.modules.pipelines`。
- Pipeline API 仍能按 RunJob 展示节点、日志和子用例结果。
- 已有任务迁移后仍能按 Test Job 关联查询，历史日志可读取。
