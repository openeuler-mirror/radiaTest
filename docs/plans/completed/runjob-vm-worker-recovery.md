<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: RunJob 与 Pipeline VM 的 Worker 中断恢复

## 状态

实现、代码审查、远程 Linux 全量验证和 `main` 合入均已完成。

## 目标

Worker 因 SIGKILL、OOM 或容器重建而中断时，自动将已经开始但没有结束的 Pipeline
RunJob、关联 Test Job 和 VM 申请收敛为现有错误终态，避免记录永久停留在
`preparing`、`running`、`creating` 或宿主锁等待产生的 `queued`。

## 范围

- 为 `PipelineRunJob` 保存 Celery `task_id`，并把同一任务身份传给 Pipeline 创建的
  Test Job 和 VM 申请。
- Worker 领取 RunJob 时写入持久化 started 任务事件。
- 统一 recovery 增加 Pipeline RunJob 处理器；VM 创建恢复覆盖已经开始的
  `creating` 和 `queued` 申请。
- Worker 启动时立即收敛旧 Worker 的执行中记录；Pipeline 状态读取时按 15 小时任务
  总超时执行懒恢复兜底。
- RunJob 收敛为 `error`，Test Job 收敛为 `error`，VM 申请收敛为 `failed`；记录任务
  事件和系统审计日志。
- 同步更新 Worker 中断恢复 ADR，以及 Pipeline、测试任务和平台运行时 Spec。

## 非目标

- 不自动重放 Celery 任务。
- 不连接宿主机，不清理可能残留的 domain、磁盘、VM 或测试环境。
- 不修改 EnvSet、Node 或 CaseRun 的执行事实。
- 不新增定时器、Beat 任务、轮询、心跳、依赖或统一重试接口。
- 不自动收敛迁移前缺少 `task_id` 的历史卡死记录。
- 不把多种任务类型合并为一个跨类型事务；沿用每类 recovery 独立提交和失败隔离。

## 实施步骤

1. 新增 nullable `pipeline_run_jobs.task_id` 迁移和模型字段，不回填历史记录。
2. 先写失败测试，再让 enqueue 保存任务 ID，并让 RunJob worker started 事件、Test Job、
   VMRequest 共享该 ID。
3. 先写失败测试，再增加 Pipeline RunJob recovery，并扩展 VM recovery 的 `queued`
   覆盖；验证启动恢复、懒恢复、幂等和任务隔离。
4. 先写失败 API 测试，再把懒恢复接入 RunJob 详情、Run 下 Job 列表和 Execution 汇总。
5. 更新 ADR/Spec：恢复范围、15 小时总超时和当前 RunJob 状态边界。
6. 运行受影响测试和检查，最后只运行一次 `./scripts/check.sh`。

## 验证标准

- enqueue 成功后 RunJob 持久化 Celery ID；enqueue 失败仍按 `queue_unavailable`
  收敛，不影响其他 RunJob。
- RunJob 进入 `preparing` 时存在带相同 Celery ID 的 started 事件；派生 Test Job 和
  VMRequest 保存同一 ID。
- Worker 启动恢复只处理具有任务身份且处于执行中的 RunJob/Test Job/VMRequest；普通
  `pending` 或尚未开始的队列记录不受影响。
- VM 创建恢复同时覆盖 `creating` 与宿主锁等待产生的 `queued`，重复恢复不产生重复终态事件。
- Pipeline 懒恢复以 started 事件为起点，只收敛超过 15 小时的执行中 RunJob。
- 三个 Pipeline 状态读取入口返回恢复后的终态。
- 恢复不调用宿主脚本、不销毁资源、不改 EnvSet/Node/CaseRun。
- 受影响后端测试通过，`./scripts/check.sh` 通过。

## 验证记录

- 自愈相关定向测试通过：Worker 启动恢复、15 小时懒恢复、VM `queued`、任务身份传递、
  关联 Test Job 按 RunJob started 时间同步收敛、三个 Pipeline 状态读取入口及幂等行为。
- Ruff、Python 编译和 Alembic 单 head 检查通过，迁移 head 为 `20260903_0037`。
- 远程 Linux 环境 `./scripts/check.sh` 全项通过（2026-09-03 用户验证）。本地 macOS
  运行受基线测试依赖的 `sshpass` 和宿主脚本环境限制，采用定向测试与远程全量结果验收。
