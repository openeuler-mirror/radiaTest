<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# RunJob 取消功能

## 范围

支持 ADMIN 对运行中的 PipelineRunJob 发起取消请求，worker 在用例执行期间（通过
HangDetector 心跳线程）和用例/环境集之间检测到取消标志后，先 `pkill` 远程
mugen.sh 进程，再等本地 SSH 自然退出，清理 VM 环境，标剩余/中断用例
`not_executed`，最终将 RunJob 和 TestJob 标为 `cancelled`。

## 非目标

- 不支持取消已终止（succeeded/failed/error/cancelled）的 RunJob，返回 409。
- 不支持取消执行级别的所有 RunJob（逐个 RunJob 取消）。
- 不保证立即中断——正在跑的 mugen.sh 需要一次 `pkill` SSH 往返后生效。
- 不释放物理机租约（物理机保持占用，与现有失败清理逻辑一致）。
- 不新增幂等键机制（`UPDATE SET cancel_requested=True` 天然幂等）。

## 实施步骤

### 1. 数据模型

- 迁移：`pipeline_run_jobs` 加 `cancel_requested` 布尔列（nullable，默认 False）。
- `PipelineRunJob` 模型加 `cancel_requested` 字段。
- `PipelineRunJob.status` 枚举加 `cancelled`。
- `TestJob.status` 枚举加 `cancelled`。

### 2. API 端点

- `POST /api/v1/pipelines/run-jobs/{id}/cancel`，ADMIN only。
- 校验 RunJob 状态为非终止状态（`running`/`preparing`/`pending`），否则 409。
- 设 `cancel_requested = True`，`status = cancelling`，返回 202 + `{status: "cancelling"}`。

### 3. 执行流检查点

- `execute_env_set`：每个用例开始前检查 `cancel_requested`。
- `process_test_job`（或外层循环）：每个环境集开始前检查 `cancel_requested`。
- `run_case`：HangDetector 心跳线程并行检测 `cancel_requested`，命中后新开
  SSH 执行 `pkill -f mugen.sh`，远程进程退出后本地 SSH 自然返回。

### 4. 取消后清理

- 中断的用例标 `not_executed`。
- 剩余未跑用例标 `not_executed`。
- VM 环境调 `cleanup_env_vms` 销毁（复用 `cleanup_failed_job_envs` 逻辑）。
- 物理机保持占用。
- RunJob `status = cancelled`，TestJob `status = cancelled`。

### 5. 前端

- 执行总览页（`execution-detail.vue`）和 RunJob 详情页（`run-job-detail.vue`）
  加「中止」按钮，`cancelling` 状态显示禁用 + 文案「取消中」。
- `cancelled` 状态用灰色 Tag 区分。

### 6. Spec / ADR 同步

- ADR：取消功能设计决策（状态机、检查点、远程进程清理顺序）。
- Spec 0003：补充 RunJob 取消 API、状态转换、权限。

## 验证标准

- 单元测试：cancel 端点设标志 + 状态转换 + 409 边界。
- 单元测试：execute_env_set 检测 cancel_requested 后退出 + 标记 not_executed。
- 单元测试：run_case 内 HangDetector 检测 cancel 后 pkill 远程 mugen。
- `./scripts/check.sh` 通过。
