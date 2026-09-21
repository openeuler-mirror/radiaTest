<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0035：Worker 中断恢复

## 状态

已接受(Accepted);2026-09-03 修订(见"修订"节)。

## 背景

VM 创建、VM 销毁、Mugen 同步、测试任务和 Pipeline RunJob 由 Celery Worker 执行，并会调用宿主机、
libvirt、Git 仓库或测试 VM。Celery 默认在执行前确认消息；Worker 在任务执行中异常退出时，
消息不会自动重新投递，PostgreSQL 中的业务状态可能长期停留在执行中。

直接启用延迟确认并自动重放并不安全：Worker 可能已经完成部分外部操作，只是尚未提交最终
数据库状态，重新执行可能重复创建 VM、销毁资源或运行测试。

## 决策

- 保持 Celery 默认的执行前消息确认，不启用 `acks_late` 或
  `task_reject_on_worker_lost`。
- Worker 中断后不自动重放任务，不自动连接宿主机清理可能残留的 domain、磁盘或测试环境。
- PostgreSQL 是业务执行状态的事实来源。任务真正开始时写入持久化开始标记；排队但尚未开始的
  任务没有开始标记，恢复逻辑不得处理。
  > **（修订：见 §修订（2026-09-03）"从未派发的孤儿"）**：`task_id IS NULL` 且
  > 超过 `VM_CREATE_TIMEOUT`/`TEST_JOB_TIMEOUT` 的 `pending` 记录视为派发失败
  > 证据，可收敛（VM → `failed + orphaned_no_task`；RunJob → `error +
  > orphaned_no_dispatch`）。有 `task_id` 的 pending 仍不处理。
- 每套环境只运行一个 Worker 容器；dev 和 prod 分别通过现有 `--concurrency=2` 和
  `--concurrency=4` 在容器内部并行执行任务，不支持同一环境横向运行多个 Worker 容器。
- Celery `worker_ready` 信号调用统一恢复服务。恢复查询使用 PostgreSQL 行锁，避免同一次
  启动中的重复处理。
- 相关列表和详情读取复用同一恢复服务进行懒检查，作为 Worker 启动恢复失败或子进程单独退出时
  的兜底；不新增 Beat 任务、后台轮询或任务心跳。
- Worker 启动恢复只处理已有开始标记且尚未结束的旧任务；懒检查按各任务类型已有最长执行时间
  判断，不使用统一的“最后更新时间”阈值。
- 恢复范围包括 VM 创建、VM 销毁、Mugen 同步、测试任务和 Pipeline RunJob。通知发送沿用已有 Celery 重试，
  每日维护沿用下一次 Beat 调度，不进入该恢复流程。
- Pipeline RunJob 在投递前持久化 Celery task ID，worker 领取时写 started 事件；其创建的
  Test Job 和 VM 申请继承同一 task ID。Pipeline 已开始但尚未进入 Test Job 执行时，关联
  Test Job 即使仍为 `pending`，也由 Pipeline started 事件证明已经开始。
- 恢复服务写入的 `error` 或 `cancelled` 是终态：仍存活但尚未提交结果的旧 Worker 必须在写入
  终态前刷新业务行，并保持该恢复结果，不能以过期 ORM 状态覆盖它。
- 收到取消请求且停在 `cancelling` 的 Pipeline RunJob，若 Worker 中断，由恢复服务将其和关联
  Test Job 收敛为 `cancelled`，而不是按普通中断标记为 `error`。此项只收敛数据库状态，不执行
  外部清理或重放。
- VM 创建恢复覆盖 `creating` 和等待宿主并发槽位的 `queued`；普通尚未领取的 VM 申请保持
  `pending`，没有 started 事件时不得恢复。
  > **（修订：见 §修订（2026-09-03））**：`pending` 且 `task_id IS NULL` 且
  > `created_at` 超 60min 的申请可回收为 `failed + orphaned_no_task`。仍**不**
  > 处理"`pending` + `task_id NOT NULL`"（broker 里的活消息）。
- 不新增 `interrupted` 状态；各工作流复用现有失败或异常状态。Worker 启动恢复使用
  `worker_interrupted` 区分中断原因，超时懒检查继续使用各流程已有的超时或陈旧错误码。
  具体状态变化以平台运行时规格为准。
- 每次状态修正同时写任务事件和审计日志。任务事件记录任务 ID、最后阶段、候选宿主等有限诊断
  信息；审计日志记录系统自动修改了业务状态。两者都不得记录凭据或完整原始输出。
- 启动恢复失败时记录完整服务端错误并继续启动 Worker；之后由相关页面的懒检查继续兜底。
- 不新增通用“重试任务”接口或按钮。VM 创建重新申请，VM 销毁再次释放，Mugen 再次同步，
  测试任务重新创建，Pipeline RunJob 重新触发所属流水线。

## 取舍

选择“标记异常并人工重新发起”，而不是 Celery 自动重放，是因为当前任务包含不可可靠回滚的
外部副作用。该方案优先避免重复操作，同时保留足够诊断信息。

选择 Worker 启动恢复和页面懒检查组合，而不是周期心跳或 Beat 扫描，是为了在正常重启时及时
修正状态，并以低成本覆盖 Worker 子进程异常，不产生持续数据库写入和后台轮询。

选择复用现有终态，并让启动恢复使用 `worker_interrupted` 错误码，而不是新增
`interrupted` 状态，是为了保持现有状态机、筛选和页面逻辑稳定。

选择单 Worker 容器加进程池并发，是因为启动恢复可以明确把已有执行中记录视为旧 Worker 遗留。
支持多个独立 Worker 容器需要额外的实例身份、租约和心跳，不符合当前部署规模和简单原则。

## 影响

- 具有持久化执行状态的异步流程需要明确区分排队、已开始和已结束。
- `pipeline_run_jobs` 保存 nullable `task_id`；历史缺少任务身份的执行中记录不自动收敛
  （**修订**：缺少 `task_id` 且从未 started 的 `pending` 派发失败记录改由"从未派发"分支收敛，详见"修订"节）。
- VM 销毁等缺少开始标记的流程需要补充最小持久化标记。
- Worker 启动和相关查询入口需要调用同一个恢复服务，状态修正必须具备并发保护。
- 异步中断的对外状态、日志和验收标准以平台运行时规格为准。

## 修订（2026-09-03）：从未派发的孤儿

### 背景补充

kimariyb 环境出现 44 条永久卡在 `creating`/`queued` 的 VM 申请，prod 环境出现 151 条
（含 29 条 `pending` + 122 条 `creating`），共同特征：`task_id IS NULL` 且其 started 事件
`celery_task_id IS NULL`。经只读排查确认：这类记录在 `create_vm_request` 落 `pending`
后、`queue_vm_request` 补 `task_id = enqueue_vm_create(request)` 并 commit 之前，进程
崩溃或被外部中断，Celery 从未收到派发请求，因此 started 事件与 `task_id` 都停留在
`NULL`。原决策"缺少 started 事件不处理"、"普通 `pending` 不受影响"、"缺少 task ID 的历史
记录不自动收敛"三条约束，对这类记录形成**永久盲区**：既不会被懒读回收，也不会被 worker
启动扫描回收，用户看到的状态会一直挂着。

Pipeline RunJob 存在同构风险：`plan_run_jobs` 先提交 `pending + task_id NULL`，随后
`enqueue_run_jobs` 才补 `task_id` 并 commit；若崩溃在两处之间，同样落入原三条约束的盲区。

### 决策（对"决策"第 3、6、10、12 条与"影响"第 2 条的补充）

在保留原有三条 AND 硬条件（状态白名单 + `task_id` 非空 + started 事件）分支不受影响的
前提下，为 `VM_CREATE` 与 `PIPELINE_RUN_JOB` 各新增一条**"从未派发"孤儿**回收分支，
**只**处理"`task_id IS NULL` 的派发失败记录"：

- **VM**：`status ∈ {pending, queued, creating}` 且 `task_id IS NULL` 且
  `created_at <= as_of - VM_CREATE_TIMEOUT`（60 分钟）→ `failed`，`error_code =
  'orphaned_no_task'`。
- **Pipeline RunJob**：`status = 'pending'` 且 `task_id IS NULL` 且
  `created_at <= as_of - TEST_JOB_TIMEOUT`（15 小时）→ `error`，`error_code =
  'orphaned_no_dispatch'`（`PipelineRunJob` 无 `error_code` 列，错误码落在恢复事件与审
  计里）。
- **触发时机**：懒读和 worker 启动共用同一条件（`created_at` 阈值），worker 启动也不立即
  清。原因是 `create_vm_request → queue_vm_request` 与 `plan_run_jobs →
  enqueue_run_jobs` 都存在"先落 `pending + task_id NULL`、commit、再补 `task_id`"的写入
  窗口；立即清会把用户正在提交的申请误杀。阈值已足以避开该窗口（用户提交耗时是毫秒级）。
- **不覆盖的相邻场景**："`task_id NOT NULL` + 停在 `pending`" 视为 broker 里活着的排队消息，
  与原决策一致，**继续不动**；用户如需处理，走现有 `/cancel` 端点。

### 取舍

保留原决策对"有 task_id + 有 started 事件"的收敛路径不变，只是把"有 started 事件"这条
硬性要求**替换**为"有 `task_id` 或有 `created_at` 超时"二者之一 —— 后者作为派发失败的可
靠证据。选择"`task_id IS NULL`" 作为孤儿信号，而不是"`created_at` 单条件"，是为了与"broker
里 pending 的活消息"清晰区分，不误杀。

阈值复用 `VM_CREATE_TIMEOUT`（60min）和 `TEST_JOB_TIMEOUT`（15h）两个既有常量而不是新
增 `PIPELINE_ORPHAN_TIMEOUT`，避免多一个未验证的旋钮；对 RunJob 来说，pending 孤儿 15h
才回收偏长是已识别的用户体验欠账，按用户反馈再单开常量。

### 影响（对"影响"节的补充）

- `_recover_vm_creates` 与 `recover_interrupted_run_jobs` 需要与原有查询并列一条 `task_id
  IS NULL` 分支，共用同一 handler 与同一提交；两条分支状态互斥。
- `record_task_recovery` 需要支持 `celery_task_id` 为空/空的调用（当前以 `celery_task_id=''`
  传参）；相关详情页文案与运维查询习惯需要知晓这条"无 celery 身份"的孤儿事件的存在。
- 历史手工 SQL 清理（例如 kimariyb 已回收的 44 条）不写 task_event/audit，因此同一
  `error_code` 下会有"有恢复事件"与"仅业务字段变化"混合，属于修订上线前的一次性运维
  痕迹，不再新产生。
- Spec `0005-platform-runtime.md` 相应条款（`Worker 恢复不得处理没有开始标记的排队任务`、
  `普通 pending 申请不受影响`、`缺少 task ID 或 Pipeline started 事件的历史记录不自动
  处理`）由本修订与新计划文档
  （`docs/plans/active/vm-orphan-request-recovery.md`、
  `docs/plans/active/runjob-orphan-recovery.md`）同步为"`task_id IS NULL` 且超过对应超时
  的 pending/creating/queued 记录属于派发失败孤儿，可回收"。
