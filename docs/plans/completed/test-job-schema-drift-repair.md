<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: Test Job 迁移结构漂移修复

## 状态

已完成。

## 目标

修复 `20260715_0015` 在迁移链并轨后用旧定义重建测试任务表造成的结构漂移，
确保当前 ORM 能创建流水线 Test Job，并让数据库异常后的 RunJob 可靠进入错误终态。

## 范围

- 新增后续 Alembic 迁移，幂等补齐当前模型需要的 `test_jobs` 和
  `test_env_sets` 字段。
- 将无 Test Job 的遗留 `running` RunJob 收敛为 `error`。
- Pipeline RunJob 任务遇到数据库异常时先回滚，再用干净事务记录错误状态和事件。
- 增加迁移结构与异常状态落库的聚焦回归测试。

## 非目标

- 不修改已发布的历史迁移。
- 不恢复 `test_jobs.pipeline_run_job_id`；关联仍以
  `pipeline_run_jobs.test_job_id` 为准。
- 不改变流水线产品行为、日志收集时机、PXE 流程或 VM 测试。
- 不执行远程数据库迁移或部署。

## 实施与验证

- [x] 新增 `0035` 幂等结构修复迁移。
- [x] 修复 RunJob 任务的失败事务处理。
- [x] 增加聚焦回归测试，`3 passed`。
- [x] Ruff、Python 编译和 Alembic 单一 head 检查通过。
- [x] 非 VM 后端测试 `335 passed, 1 skipped`。
- [x] 文档检查与 `git diff --check` 通过。

## 验收标准

- 当前模型所需的 `keep_env`、`result_parser`、`mugen_exec_command`、
  `update_packages` 和 `test_env_sets.env_type` 在迁移后存在。
- 已有同名字段时迁移可安全跳过，不重复添加。
- `running` 且 `test_job_id IS NULL` 的遗留 RunJob 被标记为 `error`。
- executor 抛出数据库异常时，RunJob 和 `runjob_error` 事件能够提交。
