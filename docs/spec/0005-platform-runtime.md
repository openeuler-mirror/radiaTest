<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# 平台运行时规格

## 状态

有效(Active)。

## 目标

本规格定义所有 radiaTest 业务模块共同遵循的 API 错误契约、请求追踪和异步任务中断行为。
资源、测试、工单和通知规格不重复定义这些公共规则。

## API 错误响应

> 契约、错误分类与请求追踪头的设计决策记录在
> [ADR 0034](../adr/0034-api-error-contract-and-request-tracing.md)。本节写
> 字段与行为，不重复决策理由。

- 所有 `/api/v1` JSON 错误必须使用以下结构：

  ```json
  {
    "error": {
      "code": "resource_not_found",
      "message": "资源不存在",
      "details": null
    }
  }
  ```

- `code` 为稳定的 `snake_case` 字符串。前端条件判断只使用 `code`，不能匹配
  `message` 文本。
- `message` 是可直接展示的中文用户提示。
- `details` 可以为空、对象或字段错误列表，只保存当前错误类型约定的数据。
- 未定义领域错误码时，按 HTTP 语义使用通用错误码：
  - `bad_request`
  - `unauthorized`
  - `forbidden`
  - `not_found`
  - `method_not_allowed`
  - `conflict`
  - `length_required`
  - `content_too_large`
  - `validation_error`
  - `service_unavailable`
  - `insufficient_storage`
  - `internal_error`
- 不返回旧 `detail` 字段。
- 错误响应保留正确 HTTP 状态码；前端不能只根据错误码推断状态码。
- `/api/v1` 下的路由不存在、方法不允许、认证失败、权限拒绝、业务冲突、参数校验失败和
  未预期异常都必须遵守同一响应结构。

## 参数校验错误

- 参数校验失败使用 HTTP 422 和 `validation_error`。
- `details` 是字段错误列表，每项包含：

  ```json
  {
    "field": "expected_ends_at",
    "message": "租期不能超过允许范围"
  }
  ```

- 嵌套字段使用点分路径；不返回 Pydantic 错误类型、输入原值、内部上下文或框架定位数组。
- 同一个请求可以返回多个字段错误，顺序保持后端校验结果顺序。

## 请求追踪

- 每个 `/api/v1` 请求由服务端生成唯一 `request_id`。
- 所有 `/api/v1` 响应都在 `X-Request-ID` 响应头返回该 ID。
- 访问日志、业务日志和异常日志使用同一个 `request_id`。
- 未预期异常使用 HTTP 500 和 `internal_error`，返回固定中文提示；`details` 只包含：

  ```json
  {
    "request_id": "<当前请求 ID>"
  }
  ```

- 未预期异常的响应不得包含异常文本、堆栈、SQL、文件路径、环境变量或凭据。
- 完整异常和 `request_id` 写入服务端日志，便于管理员定位。

## OpenAPI 和前端

- OpenAPI 使用公共错误模型描述统一错误信封和参数字段错误。
- 常见 400、401、403、404、405、409、411、413、422、500、503 和 507 响应使用公共模型，不继续声明
  FastAPI 默认 `detail` 格式。
- 前端请求层统一解析错误信封；页面只展示后端 `message`，需要分支处理时使用 `code`。
- 当前界面只提供中文，隐藏可见语言切换入口；不要求删除框架国际化代码。

## 异步任务中断

> 本节的行为由 [ADR 0035](../adr/0035-worker-interruption-recovery.md) Worker
> 中断恢复决策定义（含 2026-09-03"从未派发的孤儿"修订），并与
> [ADR 0031](../adr/0031-termination-convergence.md) 终止收敛机制、
> [ADR 0030](../adr/0030-runjob-cancel.md) RunJob 取消互补：0035 定义
> Worker 崩溃后的懒/启动期恢复边界，0031 定义运行中的 cancel_event 打断
> 通路，0030 定义用户主动取消的 API 与状态机。三者共同约束"什么场景
> 由谁把状态收敛到终态"。

### 通用规则

- PostgreSQL 是异步工作流状态的事实来源；Redis 只承担 Celery broker 和 result backend。
- 任务排队时保持排队状态；Celery task 真正开始执行后写入持久化开始标记。
- Worker 恢复默认不处理有开始标记但仍在执行中的任务之外的场景；只有 `task_id` 缺失且超
  过对应懒检查阈值的记录作为"从未派发"的孤儿才被回收，视为派发失败（不是排队等待）。
  有 `task_id` 但停在 `pending` 的记录继续视为 broker 中活着的排队消息，不进入自动处理，
  由用户手动取消。
- 每套环境只运行一个 Worker 容器，容器内部按部署配置并发执行多个任务。
- Worker 启动后检查已开始但未结束的旧任务；相关列表和详情在用户读取时执行同一套懒检查。
- 不增加周期扫描、任务心跳或自动刷新。
- Worker 启动恢复失败只写服务端错误日志，不阻止 Worker 接收新任务。
- Worker 启动恢复可以确定旧 Worker 已退出，错误码使用 `worker_interrupted`；页面懒检查
  只能确定任务超过执行期限，继续使用各流程已有的超时或陈旧错误码。
- 懒检查按任务类型已有最长执行时间判断：
  - VM 创建沿用 60 分钟。
  - Mugen 同步沿用 30 分钟同步锁期限。
  - 测试任务和 Pipeline RunJob 沿用 15 小时总超时。
  - VM 销毁沿用宿主销毁流程的最长执行时间。
  - "从未派发"孤儿（`task_id IS NULL`）复用同一任务类型阈值；worker 启动也不立即清，
    以避免与"业务对象落库→补齐 `task_id`→commit"的写入窗口竞争。
- 恢复不执行宿主机命令，不自动删除 domain、磁盘、VM 或测试环境。
- 恢复不自动重新投递 Celery 任务。

### 各流程结果

- VM 创建中断：
  - 已开始的 `creating` 和等待宿主并发槽位的 `queued` 申请都进入恢复范围；`pending` 中,
    有 `task_id` 的申请（broker 里活着的排队消息）不受影响；`task_id IS NULL` 的申请视为
    派发失败孤儿,超阈值时收敛。
  - 申请单改为 `failed`。
  - Worker 启动恢复的错误码记为 `worker_interrupted`；超过 60 分钟的懒检查继续使用
    `stale_creating`；派发失败孤儿使用 `orphaned_no_task`，两种触发都用它。
  - 不创建虚拟资源和租约，不自动清理宿主机。
- VM 销毁中断：
  - 清除当前销毁任务的执行锁定。
  - VM、资源记录和租约保持原状态。
  - 用户或管理员可以再次执行释放。
  - 已写入 `queued` 但在既有宿主脚本时限内没有 `destroy_started` 的任务，也按该规则清除锁；
    未超过时限的排队任务不处理，避免把仍在 broker 中的消息误判为中断。
- Mugen 同步中断：
  - 未结束的同步执行记录为失败事件。
  - 清除遗留同步互斥锁。
  - 已成功提交的历史用例索引保持不变。
- 测试任务中断：
  - 普通任务改为 `error`；已请求取消的任务改为 `cancelled`。
  - Worker 启动恢复的错误码记为 `worker_interrupted`；超过 15 小时的懒检查继续使用
    `task_timeout`。
  - 不自动恢复、重跑或清理测试环境；管理员根据任务事件确认外部状态。
- Pipeline RunJob 中断：
  - 普通 RunJob 改为 `error`；已请求取消且停在 `cancelling` 的 RunJob 及关联 Test Job
    改为 `cancelled`。关联的执行中 VM 申请按
    VM 创建规则收敛。
  - Worker 启动恢复使用 `worker_interrupted`；超过 15 小时的懒检查使用
    `task_timeout`；派发失败孤儿使用 `orphaned_no_dispatch`,两种触发都用它。
  - RunJob、Test Job 和 VM 申请共享外层 Celery task ID；缺少 `task_id` 且仍停在
    `pending` 的记录视为派发失败孤儿,按 15 小时阈值收敛；有 `task_id` 但缺 started 事件
    的历史记录继续不自动处理，由用户通过取消端点手动收敛。
  - 不修改 EnvSet、Node 或 CaseRun，不自动清理测试环境。

### 记录和重试

- 每次恢复写一条错误级任务事件，至少包含任务类型、业务对象和恢复原因；派发成功过的
  恢复附带 Celery task ID、最后阶段与已有候选宿主摘要；派发失败孤儿无 Celery task ID，
  仅记录业务字段变化与原因。
- 每次恢复写一条系统审计日志，记录原状态、目标状态和本次恢复原因，不伪装成用户操作。
- 日志不得保存凭据、完整宿主输出或完整测试日志。
- 不提供统一重试接口：
  - VM 创建失败后重新申请。
  - VM 销毁中断后再次释放。
  - Mugen 同步中断后再次同步。
  - 测试任务中断后重新创建任务。
  - Pipeline RunJob 中断后重新触发所属流水线。

## 验证

- API 测试覆盖框架错误、参数校验、认证权限、业务错误、未知路由、方法不允许和未预期异常。
- API 测试验证所有错误只返回错误信封，不返回旧 `detail`。
- 请求追踪测试验证正常响应和错误响应都返回 `X-Request-ID`，500 日志与响应使用同一个 ID。
- OpenAPI 测试验证公共错误模型存在，常见错误响应不引用 FastAPI 默认校验错误模型。
- Worker 恢复测试覆盖排队任务不受影响、已开始任务状态修正、`task_id` 缺失的派发失败孤儿
  回收（VM 申请与 Pipeline RunJob 各覆盖 lazy 与 startup 两种触发,含阈值前后与有 `task_id`
  不误杀回归）、重复恢复幂等、并发恢复行锁、启动恢复失败不阻断 Worker，以及各流程对应
  的任务事件和审计日志。
- 前端单元测试覆盖统一错误解析和语言切换入口隐藏。
