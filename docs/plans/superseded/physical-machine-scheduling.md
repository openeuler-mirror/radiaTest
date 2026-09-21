<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan（历史，已取代）：物理机资源调度 — DB 锁 + 等待重试

## 状态

未实施，已于 2026-09-04 被 [ADR 0029](../../adr/0029-physical-test-resource-usage-state.md) 的“行锁认领 + 非终态 TestJob 的 Env Node 关联”模型取代。本文的 `management_status=maintenance` 测试期锁、固定 `sleep(60)` 重试、提高至 60 并发均不可作为当前实施方案。

如需扩展调度吞吐或等待策略，必须基于 ADR 0029 重新 Grill 并在 `docs/plans/active/` 新建计划。

## 背景

当前 Celery worker concurrency=2(dev),所有 RunJob 进同一队列 FIFO 排队。kernel(物理机)和 docker(VM)资源完全不冲突但互相阻塞。触发全部 6 版本 × 2 架构 × 5 模块 = 60 个 RunJob 时会严重排队。

物理机资源:当前每种 `usage_scenario`(kernel-update/pkgcmd-update/pkgserver-update)只有 1 台物理机。两个任务不能同时用同一台物理机(PXE 重装冲突),但不同 `usage_scenario` 的物理机互不干扰。后续会加更多机器。

## 确认的决策

1. **concurrency 提高到 60**(dev)。部署脚本需放开 `=2` 校验。
2. **物理机锁**: `create_env_node_physical` 检查 `management_status == 'maintenance'`(被其他 RunJob PXE 占用)→ 等待重试,不直接 fail。
3. **等待方式**: sleep-and-retry(在 `create_env_node_physical` 内),`sleep(60)` 最多 30 次(30 分钟)。简单,不动 Celery/task/异常链。阻塞 1 个 worker 槽,concurrency=60 可接受。
4. 不采用 Celery task 级 retry:有 TestJob 已建/异常被 `_run_env_set_thread` 吞掉/多 env_set 线程处理的复杂问题。
5. 不同 `usage_scenario` 的物理机互不干扰,加机器后自动并行。

## 待实现 Task

### Task 1: 部署脚本放开 concurrency 校验
- `deploy/scripts/deploy-release.sh`: dev 的 `CELERY_WORKER_CONCURRENCY=2` 校验改为允许任意正整数
- `/etc/kronos/dev.env`: 设 `CELERY_WORKER_CONCURRENCY=60`

### Task 2: 物理机锁 + sleep-and-retry
- `errors.py`: 新增 `PhysicalMachineBusy` 异常
- `physical.py` `create_env_node_physical`: 找到资源后检查 `management_status`
  - 如果 `maintenance` → `sleep(60)` → `db.refresh(resource)` 重查,最多 30 次
  - 超过 30 次 → raise `TestJobExecutionError("physical_machine_timeout")`
  - 不阻塞其他 env_set 线程(VM env_set 不检查物理机)
- 无需改 Celery/task/异常链

### Task 3: 测试
- `create_env_node_physical` 在 `maintenance` 时等待,在 `active` 时继续
